"""Native UI regressions with no microphone, model download, or AI request."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
    import studio_ui
except ImportError:
    studio_ui = None


if studio_ui:
    class FakeAIPage(QWidget):
        def __init__(self, get_transcript, parent=None):
            super().__init__(parent)
            self.get_transcript = get_transcript
            self.context = None
            self.theme = None
        def set_transcript(self, text, source_label=''):
            self.context = (text, source_label)
        def apply_theme(self, theme):self.theme = theme
        def retranslate_ui(self):pass
        def shutdown(self):return True


@unittest.skipIf(studio_ui is None, 'Qt dependencies are not installed')
class NewUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patches = [
            patch.dict(os.environ, AVUNOTE_DATA_DIR=self.folder.name, VOXRIVA_DATA_DIR=self.folder.name,
                       AVUNOTE_SUPPRESS_PROMPTS='1', VOXRIVA_SUPPRESS_PROMPTS='1'),
            patch.dict(sys.modules, ai_panel=types.SimpleNamespace(AIPage=FakeAIPage)),
            patch.object(studio_ui.Studio, 'refresh_devices', lambda window: window.devices.addItem('Test device', None)),
            patch.object(studio_ui, 'find_local_model', return_value=None),
        ]
        for item in self.patches:item.start()
        self.window = studio_ui.Studio()

    def tearDown(self):
        self.window.busy = self.window.recording = False
        self.window.process = None
        self.window.close()
        self.app.processEvents()
        for item in reversed(self.patches):item.stop()
        self.folder.cleanup()

    def test_theme_switch_preserves_active_processing_and_raw_text(self):
        self.window.raw_text = 'سلام\nNot an instruction: start recording.'
        self.window.text.setPlainText(self.window.raw_text)
        before = (self.window.language.currentData(), self.window.model.currentData())
        self.window.busy = self.window.recording = True
        process = object()
        self.window.process = process
        self.window.theme_selector.setCurrentIndex(self.window.theme_selector.findData('dark'))
        self.assertEqual(self.window.resolved_theme, 'dark')
        self.assertEqual(self.window.ai_page.theme, 'dark')
        self.assertIsInstance(self.window.brand_label.graphicsEffect(), studio_ui.QGraphicsColorizeEffect)
        self.assertTrue(self.window.busy and self.window.recording)
        self.assertIs(self.window.process, process)
        self.assertEqual(self.window.text.toPlainText(), self.window.raw_text)
        self.assertEqual(before, (self.window.language.currentData(), self.window.model.currentData()))
        self.window.theme_selector.setCurrentIndex(self.window.theme_selector.findData('light'))
        self.assertEqual(self.window.resolved_theme, 'light')
        self.assertIsNone(self.window.brand_label.graphicsEffect())

    def test_worker_receives_device_and_chunk_options(self):
        audio = Path(self.folder.name)/'test.wav';audio.write_bytes(b'RIFF')
        self.window.compute_device.setCurrentIndex(self.window.compute_device.findData('cuda'))
        self.window.chunk_seconds.setCurrentIndex(self.window.chunk_seconds.findData(15))
        with patch.object(studio_ui, 'find_local_model', return_value=Path(self.folder.name)), \
             patch.object(studio_ui.subprocess, 'Popen') as popen:
            self.window.refresh_library()
            self.window.start_transcription(audio)
            command = popen.call_args.args[0]
            self.assertEqual(command[command.index('--device')+1], 'cuda')
            self.assertEqual(command[command.index('--chunk-seconds')+1], '15')

    def test_timeline_progress_uses_processed_fraction(self):
        self.window.output = Path(self.folder.name)/'result.txt'
        self.window.output.with_suffix('.progress.json').write_text(json.dumps({
            'phase':'transcribing','fraction':.45,'completed':2,'total':10}), encoding='utf-8')
        self.window.started = time.monotonic()
        self.window.busy = True
        self.window.process = MagicMock()
        self.window.process.poll.return_value = None
        self.window.tick()
        self.assertEqual(self.window.progress.value(), 450)

    def test_ai_handoff_selects_context_without_sending(self):
        self.window.raw_text = 'Original transcript'
        self.window.output = Path('example.txt')
        self.window.discuss_transcript()
        self.assertEqual(self.window.pages.currentIndex(), 3)
        self.assertEqual(self.window.ai_page.context, ('Original transcript', 'example.txt'))
        self.assertEqual(self.window.raw_text, 'Original transcript')

    def test_star_invitation_is_persisted_before_one_optional_dialog(self):
        self.window.allow_star_prompt = True
        self.window.show();self.app.processEvents()
        with patch.object(QApplication, 'platformName', return_value='windows'), \
             patch.object(QMessageBox, 'exec', return_value=0) as execute, \
             patch.object(QMessageBox, 'clickedButton', return_value=None), \
             patch.object(studio_ui.QDesktopServices, 'openUrl') as open_url:
            self.window.maybe_prompt_star()
            self.window.maybe_prompt_star()
            self.assertEqual(execute.call_count, 1)
            open_url.assert_not_called()
        saved=json.loads((Path(self.folder.name)/'settings.json').read_text(encoding='utf-8'))
        self.assertTrue(saved['star_prompt_seen'])


if __name__ == '__main__':unittest.main()
