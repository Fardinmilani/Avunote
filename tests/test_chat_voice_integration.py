"""Offline integration of real chat UI with the shared speech/recording pipeline."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication
    import studio_ui
    import ai_panel
    import ai_profiles
except ImportError:
    studio_ui = None


if studio_ui:
    class FakeRecorder(QObject):
        ready = Signal()
        level = Signal(float)
        recorded = Signal(str, float)
        failed = Signal(str)

        def __init__(self, device, path):
            super().__init__()
            self.device, self.path = device, Path(path)
            self.stop_event = threading.Event()
            self.wait = MagicMock(return_value=True)

        def start(self):self.ready.emit()

        def complete(self):
            self.path.write_bytes(b'RIFF mock local recorded audio')
            self.recorded.emit(str(self.path), 2.5)


    class FakeChatWorker(QObject):
        reply = Signal(str)
        failed = Signal(str)
        cancelled = Signal()
        finished = Signal()
        instances = []

        def __init__(self, profile, messages):
            super().__init__()
            self.messages = messages
            self.cancel_event = threading.Event()
            self.running = False
            self.instances.append(self)

        def start(self):self.running = True
        def isRunning(self):return self.running
        def wait(self, timeout):return not self.running
        def complete(self, reply):
            self.running = False
            self.reply.emit(reply)
            self.finished.emit()


@unittest.skipIf(studio_ui is None, 'Qt dependencies unavailable')
class ChatVoiceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.audio = self.folder / 'question.wav'
        self.audio.write_bytes(b'RIFF mock imported audio')
        (self.folder / 'settings.json').write_text(json.dumps({'ui_language':'en', 'language':'fa'}), encoding='utf-8')
        self.patches = [
            patch.dict(os.environ, AVUNOTE_DATA_DIR=str(self.folder), VOXRIVA_DATA_DIR=str(self.folder), AVUNOTE_SUPPRESS_PROMPTS='1', VOXRIVA_SUPPRESS_PROMPTS='1'),
            patch.object(studio_ui.Studio, 'refresh_devices', lambda w:w.devices.addItem('Test microphone', 7)),
            patch.object(studio_ui, 'find_local_model', return_value=self.folder),
            patch.object(studio_ui, 'Recorder', FakeRecorder),
            patch.object(ai_panel, 'ChatWorker', FakeChatWorker),
        ]
        for item in self.patches:item.start()
        FakeChatWorker.instances.clear()
        self.window = studio_ui.Studio()
        self.window.timer.stop()
        self.page = self.window.ai_page
        profile = ai_profiles.save_profile({'name':'Local fixture', 'provider':'ollama', 'model':'test-model'})
        self.page.refresh_profiles(profile)
        self.window.model_readiness[self.window.model.currentData()] = True
        self.window.controls()
        self.window.raw_text = 'Original studio transcript'
        self.window.text.setPlainText(self.window.raw_text)
        self.window.output = self.folder / 'original.txt'
        self.window.last_audio = self.folder / 'original.wav'
        self.window.run_language = 'en'
        self.page.set_transcript('Reference that must remain stable', 'original.txt')
        self.page.messages = [{'role':'user','content':'Earlier question'}, {'role':'assistant','content':'Earlier answer'}]
        self.page.composer.setPlainText('Existing typed draft')
        self.page.render()
        self.window.show_page(3)
        self.original = (self.window.raw_text, self.window.output, self.window.last_audio, self.page.chat_id, self.page.reference)

    def tearDown(self):
        self.window.busy = self.window.recording = False
        self.window.process = None
        self.page.set_voice_state('idle')
        self.window.close()
        self.app.processEvents()
        for item in reversed(self.patches):item.stop()
        self.temporary.cleanup()

    def fake_process(self):
        process = MagicMock()
        process.pid = None  # Never inspect or terminate real operating-system processes.
        process.poll.return_value = None
        process.returncode = None
        return process

    def finish_transcription(self, process, text='Decoded voice question', status='success', code=0):
        output = self.window.active_output()
        output.write_text(text, encoding='utf-8')
        output.with_suffix('.metrics.json').write_text(json.dumps({'status':status, 'language':'fa', 'errors':[]}), encoding='utf-8')
        process.returncode = code
        process.poll.return_value = code
        self.window.complete()

    def assert_original_preserved(self):
        self.assertEqual((self.window.raw_text, self.window.output, self.window.last_audio, self.page.chat_id, self.page.reference), self.original)
        self.assertEqual(self.window.text.toPlainText(), 'Original studio transcript')
        self.assertEqual(self.window.pages.currentIndex(), 3)

    def test_import_uses_same_worker_and_all_selected_speech_settings(self):
        self.window.compute_device.setCurrentIndex(self.window.compute_device.findData('cuda'))
        self.window.chunk_seconds.setCurrentIndex(self.window.chunk_seconds.findData(15))
        process = self.fake_process()
        with patch.object(studio_ui.QFileDialog, 'getOpenFileName', return_value=(str(self.audio), 'Audio')), \
             patch.object(studio_ui.subprocess, 'Popen', return_value=process) as start:
            self.page.attach_audio.click()
        command = start.call_args.args[0]
        expected = {'--worker':str(self.audio.resolve()), '--model':self.page.speech_model_key(),
                    '--language':self.page.speech_language_code(), '--beams':str(self.window.mode.currentData()),
                    '--device':'cuda', '--chunk-seconds':'15', '--output':str(self.window.ai_output)}
        for flag, value in expected.items():self.assertEqual(command[command.index(flag) + 1], value)
        self.assertEqual(self.page.voice_state, 'transcribing')
        self.assert_original_preserved()
        self.finish_transcription(process)
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft\n\nDecoded voice question')
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertEqual(FakeChatWorker.instances, [])
        self.assert_original_preserved()

    def test_recording_and_second_voice_use_shared_recorder_and_keep_chat_context(self):
        self.page.record_voice.click()
        recorder = self.window.recorder
        self.assertIsInstance(recorder, FakeRecorder)
        self.assertEqual(recorder.device, 7)
        self.assertEqual(self.page.voice_state, 'recording')
        self.page.record_voice.click()
        self.assertTrue(recorder.stop_event.is_set())
        self.assertEqual(self.page.voice_state, 'stopping')
        process = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=process):recorder.complete()
        self.finish_transcription(process, 'First voice')
        self.page.send_chat()
        request = FakeChatWorker.instances[-1]
        self.assertEqual([m['content'] for m in request.messages[-3:]], ['Earlier question','Earlier answer','Existing typed draft\n\nFirst voice'])
        request.complete('Answer to first voice')
        second = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=second):self.window.start_transcription(self.audio, target='ai')
        self.finish_transcription(second, 'Second voice')
        self.page.send_chat()
        self.assertEqual([m['content'] for m in FakeChatWorker.instances[-1].messages[-3:]], ['Existing typed draft\n\nFirst voice','Answer to first voice','Second voice'])
        FakeChatWorker.instances[-1].complete('Second answer')
        self.assert_original_preserved()

    def test_recording_error_and_worker_spawn_error_restore_controls_and_draft(self):
        self.page.record_voice.click()
        self.window.recorder.failed.emit('Mock microphone error')
        self.assertFalse(self.window.recording)
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft')
        with patch.object(studio_ui.subprocess, 'Popen', side_effect=OSError('Mock spawn failure')):
            self.window.start_transcription(self.audio, target='ai')
        self.assertFalse(self.window.busy)
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertTrue(self.page.send.isEnabled())
        self.assert_original_preserved()

    def test_progress_and_cancel_stay_in_chat_and_discard_partial_text(self):
        process = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=process):self.window.start_transcription(self.audio, target='ai')
        self.window.ai_output.with_suffix('.progress.json').write_text(json.dumps({'phase':'transcribing','fraction':.45,'completed':2,'total':10}), encoding='utf-8')
        self.window.tick()
        self.assertIn('45%', self.page.status.text())
        self.page.voice_cancel.click()
        process.terminate.assert_called_once()
        self.assertTrue(self.window.cancelled)
        self.assertFalse(self.page.voice_cancel.isEnabled())
        self.finish_transcription(process, 'Partial speech must not enter the chat', code=-15)
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft')
        self.assert_original_preserved()

    def test_model_disappearing_after_recording_does_not_leave_chat_locked(self):
        self.page.record_voice.click()
        self.page.record_voice.click()
        with patch.object(studio_ui, 'find_local_model', return_value=None), \
             patch.object(self.window, 'open_selected_library'):
            self.window.recorder.complete()
        self.assertFalse(self.window.recording)
        self.assertFalse(self.window.busy)
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertTrue(self.page.send.isEnabled())
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft')

    def test_failed_asr_does_not_replace_conversation_or_original_result(self):
        process = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=process):self.window.start_transcription(self.audio, target='ai')
        self.finish_transcription(process, 'Partial result', status='failed', code=1)
        self.assertEqual(self.page.voice_state, 'idle')
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft')
        self.assertEqual(self.page.messages[-1]['content'], 'Earlier answer')
        self.assert_original_preserved()

    def test_ctrl_o_on_chat_uses_chat_import_and_retains_current_page(self):
        process = self.fake_process()
        with patch.object(studio_ui.QFileDialog, 'getOpenFileName', return_value=(str(self.audio), 'Audio')), \
             patch.object(studio_ui.subprocess, 'Popen', return_value=process):self.window.choose_file()
        self.assertEqual(self.window.transcription_target, 'ai')
        self.assert_original_preserved()
        self.finish_transcription(process)

    def test_shutdown_cancels_asr_and_saves_the_latest_typed_draft(self):
        process = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=process):self.window.start_transcription(self.audio, target='ai')
        self.page.composer.setPlainText('Typed during local ASR')
        self.window.close()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=3)
        saved = json.loads((self.folder / 'ai-chats' / (self.page.chat_id + '.json')).read_text(encoding='utf-8'))
        self.assertEqual(saved['draft'], 'Typed during local ASR')

    def test_rejected_close_after_recording_stops_recording_without_starting_asr(self):
        self.page.record_voice.click()
        recorder = self.window.recorder
        with patch.object(self.window.downloads, 'close', return_value=False):
            self.window.close()
        self.assertTrue(recorder.stop_event.is_set())
        self.assertFalse(self.window.closing)
        self.assertFalse(self.window.recording)
        self.assertEqual(self.page.voice_state, 'idle')
        with patch.object(studio_ui.subprocess, 'Popen') as start:recorder.complete()
        start.assert_not_called()
        self.assertEqual(self.page.composer.toPlainText(), 'Existing typed draft')

    def test_chat_speech_pickers_are_independent_of_studio(self):
        studio_language = self.window.language.currentData()
        studio_model = self.window.model.currentData()
        self.page.speech_language.setCurrentIndex(self.page.speech_language.findData('en'))
        self.assertEqual(self.window.language.currentData(), studio_language)
        chat_model = self.page.speech_model_key()
        self.assertTrue(chat_model)
        process = self.fake_process()
        with patch.object(studio_ui.QFileDialog, 'getOpenFileName', return_value=(str(self.audio), 'Audio')), \
             patch.object(studio_ui.subprocess, 'Popen', return_value=process) as start:
            self.page.attach_audio.click()
        command = start.call_args.args[0]
        self.assertEqual(command[command.index('--language') + 1], 'en')
        self.assertEqual(command[command.index('--model') + 1], chat_model)
        self.assertEqual(self.window.model.currentData(), studio_model)
        self.window.language.setCurrentIndex(self.window.language.findData('tr'))
        self.assertEqual(self.page.speech_language_code(), 'en')
        self.finish_transcription(process)

    def test_drop_on_chat_routes_to_chat_transcriber(self):
        event = MagicMock()
        url = MagicMock()
        url.toLocalFile.return_value = str(self.audio)
        event.mimeData.return_value.urls.return_value = [url]
        process = self.fake_process()
        with patch.object(studio_ui.subprocess, 'Popen', return_value=process):self.window.dropEvent(event)
        self.assertEqual(self.window.transcription_target, 'ai')
        event.acceptProposedAction.assert_called_once()
        self.assert_original_preserved()
        self.finish_transcription(process)


if __name__ == '__main__':unittest.main()
