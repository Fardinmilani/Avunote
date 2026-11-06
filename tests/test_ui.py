"""Readiness and download feedback regressions; never opens a microphone."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    import studio_ui
except ImportError:
    studio_ui = None


@unittest.skipIf(studio_ui is None, 'Qt dependencies are not installed')
class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env = patch.dict(os.environ, AVUNOTE_DATA_DIR=self.folder.name, VOXRIVA_DATA_DIR=self.folder.name)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.devices = patch.object(studio_ui.Studio, 'refresh_devices',
                                    lambda window: window.devices.addItem('No microphone in tests', None))
        self.devices.start()
        self.addCleanup(self.devices.stop)
        self.ready = patch.object(studio_ui, 'find_local_model', return_value=None)
        self.ready.start()
        self.addCleanup(self.ready.stop)
        self.window = studio_ui.Studio()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_missing_model_blocks_conversion_and_recording(self):
        self.window.language.setCurrentIndex(self.window.language.findData('fa'))
        self.assertFalse(self.window.choose_button.isEnabled())
        self.assertFalse(self.window.record_button.isEnabled())
        self.assertIsNone(self.window.model.currentData())
        self.assertEqual(self.window.model.placeholderText(), 'No model installed')
        for index in range(self.window.model.count()):
            row = self.window.model.model().item(index)
            self.assertFalse(row.isEnabled())
            self.assertFalse(row.isSelectable())
            self.assertIn('Not downloaded', row.text())
        self.window.model.setCurrentIndex(0)
        self.assertIsNone(self.window.model.currentData())
        with patch.object(studio_ui.QFileDialog, 'getOpenFileName') as dialog:
            self.window.choose_file()
            dialog.assert_not_called()
        self.assertEqual(self.window.pages.currentIndex(), 2)
        self.window.language.setCurrentIndex(self.window.language.findData('azb'))
        compatible = studio_ui.models_for_language('azb')
        self.assertEqual({self.window.model.itemData(i) for i in range(self.window.model.count())},
                         {item['key'] for item in compatible})

    def test_download_feedback_and_shared_model_ready_without_network(self):
        key = 'multilingual-tiny'
        self.window.language.setCurrentIndex(self.window.language.findData('fa'))
        self.window.library_language.setCurrentIndex(self.window.library_language.findData('fa'))
        self.window.rebuild_library()
        state = dict(status='downloading', bytes_done=50, bytes_total=100,
                     speed_bps=10, eta_seconds=5, error='')
        with patch.object(self.window.downloads, 'snapshot', return_value=state):
            self.window.refresh_library()
            widgets = self.window.download_widgets[key]
            index = self.window.model.findData(key)
            row = self.window.model.model().item(index)
            self.assertEqual(widgets['bar'].value(), 500)
            self.assertFalse(widgets['pause'].isHidden())
            self.assertIn('50%', row.text())
            self.assertFalse(row.isEnabled())
            state['status'] = 'paused'
            self.window.refresh_library()
            self.assertEqual(widgets['start'].text(), 'Resume download')
            state['status'] = 'completed'
            self.window.refresh_library()
            self.assertFalse(row.isEnabled())  # Receipt alone cannot mark missing files ready.
            self.assertIn('Not downloaded', row.text())
        # One shared model serves both categories; no download method is called.
        with patch.object(studio_ui, 'find_local_model', side_effect=lambda k: Path(self.folder.name) if k == key else None), \
             patch.object(self.window.downloads, 'start') as start:
            self.window.refresh_library()
            self.assertEqual(self.window.model.currentData(), key)
            self.assertTrue(row.isEnabled())
            self.assertTrue(row.icon().isNull())
            for language in ['fa', 'tr', 'en']:
                self.window.language.setCurrentIndex(self.window.language.findData(language))
                self.assertEqual(self.window.model.currentData(), key)
                self.assertTrue(self.window.choose_button.isEnabled())
            start.assert_not_called()

    def test_download_icon_and_keyboard_keep_picker_open_without_selecting_model(self):
        key = 'multilingual-tiny'
        self.window.language.setCurrentIndex(self.window.language.findData('fa'))
        self.window.show()
        self.app.processEvents()
        picker = self.window.model
        studio_page = self.window.pages.currentIndex()
        state = dict(status='idle', bytes_done=0, bytes_total=100)

        def snapshot(model_key):
            return dict(state) if model_key == key else {'status': 'idle'}

        def begin(model_key):
            self.assertEqual(model_key, key)
            state.update(status='downloading', bytes_done=41)

        def pause(model_key):
            self.assertEqual(model_key, key)
            state.update(status='paused')

        with patch.object(self.window.downloads, 'snapshot', side_effect=snapshot), \
             patch.object(self.window.downloads, 'active_key', side_effect=lambda: key if state['status'] == 'downloading' else None), \
             patch.object(self.window.downloads, 'start', side_effect=begin) as start, \
             patch.object(self.window.downloads, 'pause', side_effect=pause) as pause_download, \
             patch.object(self.window.downloads, 'resume', side_effect=begin) as resume:
            QTest.mouseClick(picker, Qt.MouseButton.LeftButton)
            self.app.processEvents()
            popup = picker._model_popup
            self.assertTrue(popup.isVisible())
            row = popup.rows[key]
            self.assertIn('Download model', row.action.accessibleName())
            self.assertFalse(row.action.icon().isNull())
            QTest.mouseClick(row.title, Qt.MouseButton.LeftButton)
            start.assert_not_called()
            QTest.mouseClick(row.action, Qt.MouseButton.LeftButton)
            start.assert_called_once_with(key)
            self.assertTrue(popup.isVisible())
            self.assertEqual(self.window.pages.currentIndex(), studio_page)
            self.assertIsNone(picker.currentData())
            self.assertIn('41%', row.status.text())
            self.assertEqual(row.progress.value(), 41)
            self.assertIn('Pause', row.action.accessibleName())
            self.assertTrue(all(not item.action.isEnabled() for model_key, item in popup.rows.items() if model_key != key))
            QTest.keyClick(row.action, Qt.Key.Key_Return)
            pause_download.assert_called_once_with(key)
            self.assertIn('Resume download', row.action.accessibleName())
            QTest.keyClick(row.action, Qt.Key.Key_Space)
            resume.assert_called_once_with(key)
            QTest.keyClick(row.action, Qt.Key.Key_Escape)
            self.assertFalse(popup.isVisible())

    def test_interface_switch_preserves_speech_and_raw_model_text(self):
        self.assertEqual(self.window.ui_language, 'en')
        self.window.language.setCurrentIndex(self.window.language.findData('fa'))
        selected_model = self.window.model.currentData()
        # A phrase identical to a UI label must never be translated in the transcript.
        raw = 'شروع ضبط\nYour voice. Your words.\nسلام، دنیا!'
        self.window.raw_text = raw
        self.window.text.setPlainText(raw)
        for locale in ['fa', 'tr', 'ar', 'az', 'en']:
            self.window.interface_language.setCurrentIndex(self.window.interface_language.findData(locale))
            self.assertEqual(self.window.language.currentData(), 'fa')
            self.assertEqual(self.window.model.currentData(), selected_model)
            self.assertEqual(self.window.raw_text, raw)
            self.assertEqual(self.window.text.toPlainText(), raw)
        self.window.save_settings()
        settings = __import__('json').loads((Path(self.folder.name)/'settings.json').read_text(encoding='utf-8'))
        self.assertEqual(settings['ui_language'], 'en')
        self.assertEqual(settings['language'], 'fa')


if __name__ == '__main__':
    unittest.main()
