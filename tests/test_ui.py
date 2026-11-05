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
        self.env = patch.dict(os.environ, VOXRIVA_DATA_DIR=self.folder.name)
        self.env.start()
        self.devices = patch.object(studio_ui.Studio, 'refresh_devices',
                                    lambda window: window.devices.addItem('No microphone in tests', None))
        self.devices.start()
        self.ready = patch.object(studio_ui, 'find_local_model', return_value=None)
        self.ready.start()
        self.window = studio_ui.Studio()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        self.ready.stop();self.devices.stop();self.env.stop();self.folder.cleanup()

    def test_missing_model_blocks_conversion_and_recording(self):
        self.window.language.setCurrentIndex(self.window.language.findData('fa'))
        self.window.selection_changed()
        self.assertFalse(self.window.choose_button.isEnabled())
        self.assertFalse(self.window.record_button.isEnabled())
        self.assertEqual(self.window.model.count(), 3)
        self.window.language.setCurrentIndex(self.window.language.findData('azb'))
        self.assertEqual(self.window.model.count(), 4)
        self.assertFalse(any('multilingual' in self.window.model.itemData(i)
                             for i in range(self.window.model.count())))

    def test_download_feedback_and_shared_model_ready_without_network(self):
        key = 'multilingual-tiny'
        self.window.library_language.setCurrentIndex(self.window.library_language.findData('fa'))
        self.window.rebuild_library()
        state = dict(status='downloading', bytes_done=50, bytes_total=100,
                     speed_bps=10, eta_seconds=5, error='')
        with patch.object(self.window.downloads, 'snapshot', return_value=state):
            self.window.refresh_library()
            widgets = self.window.download_widgets[key]
            self.assertEqual(widgets['bar'].value(), 500)
            self.assertFalse(widgets['pause'].isHidden())
            state['status'] = 'paused'
            self.window.refresh_library()
            self.assertEqual(widgets['start'].text(), 'Resume download')
        # One shared model serves both categories; no download method is called.
        with patch.object(studio_ui, 'find_local_model', side_effect=lambda k: Path(self.folder.name) if k == key else None), \
             patch.object(self.window.downloads, 'start') as start:
            for language in ['fa', 'tr', 'en']:
                self.window.language.setCurrentIndex(self.window.language.findData(language))
                self.window.model.setCurrentIndex(self.window.model.findData(key))
                self.window.selection_changed()
                self.assertTrue(self.window.choose_button.isEnabled())
            start.assert_not_called()

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
