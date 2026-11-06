"""Opt-in chat UI regressions: no API requests, microphone, or real secrets."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtCore import QObject,Signal,Qt
    from PySide6.QtGui import QInputMethodEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication,QFormLayout,QLabel
    import ai_panel as panel
    import ai_profiles
    import ui_i18n
except ImportError:
    panel=None


if panel:
    class FakeWorker(QObject):
        reply=Signal(str);failed=Signal(str);cancelled=Signal();finished=Signal()
        instances=[]
        def __init__(self,profile,messages):
            super().__init__();self.profile=dict(profile);self.messages=messages;self.cancel_event=threading.Event();self.running=False
            self.__class__.instances.append(self)
        def start(self):self.running=True
        def isRunning(self):return self.running
        def wait(self,timeout):return not self.running
        def deleteLater(self):pass
        def complete(self,text):
            self.running=False;self.reply.emit(text);self.finished.emit()
        def fail(self):
            self.running=False;self.failed.emit('Mock request failed');self.finished.emit()


@unittest.skipIf(panel is None,'Qt dependencies unavailable')
class AIPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.application=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.folder=Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        env=patch.dict(os.environ,VOXRIVA_DATA_DIR=str(self.folder));env.start();self.addCleanup(env.stop)
        self.language=ui_i18n.current_language();ui_i18n.set_language('en');self.addCleanup(ui_i18n.set_language,self.language)
        ai_profiles._SESSION_KEYS.clear();self.addCleanup(ai_profiles._SESSION_KEYS.clear)
        self.profile_id=ai_profiles.save_profile({'name':'Test cloud','provider':'gemini','model':'example-model','key':'unit-secret-key-not-real'})
        worker=patch.object(panel,'ChatWorker',FakeWorker);worker.start();self.addCleanup(worker.stop);FakeWorker.instances.clear()
        self.raw='Original transcript <script>alert(1)</script>'
        self.page=panel.AIPage(lambda:self.raw)
        self.addCleanup(self.page.close)

    def test_no_auto_send_and_explicit_cloud_consent(self):
        self.page.set_transcript(self.raw)
        self.page.retranslate_ui();self.page.refresh_profiles()
        self.assertEqual(FakeWorker.instances,[])
        self.page.composer.setPlainText('Summarize')
        self.page.send_chat()
        self.assertEqual(FakeWorker.instances,[])
        self.assertEqual(self.page.composer.toPlainText(),'Summarize')
        self.page.consent.setChecked(True);self.page.send_chat()
        self.assertEqual(len(FakeWorker.instances),1)
        self.assertTrue(any(self.raw in m['content'] for m in FakeWorker.instances[-1].messages))
        FakeWorker.instances[-1].complete('Summary')
        self.assertEqual(self.page.messages,[{'role':'user','content':'Summarize'},{'role':'assistant','content':'Summary'}])
        self.assertEqual(self.raw,'Original transcript <script>alert(1)</script>')

    def test_grammar_mode_reviews_voice_text_without_bypassing_consent(self):
        self.page.chat_mode.setCurrentIndex(self.page.chat_mode.findData('grammar'))
        self.page.append_voice_transcript('I has a book.')
        self.page.send_chat()
        self.assertEqual(FakeWorker.instances, [])
        self.page.consent.setChecked(True)
        self.page.send_chat()
        request = FakeWorker.instances[-1]
        self.assertIn('Needs correction', request.messages[0]['content'])
        self.assertIn('speech recognition', request.messages[0]['content'])
        self.assertEqual(request.messages[-1], {'role':'user', 'content':'I has a book.'})
        self.assertFalse(self.page.chat_mode.isEnabled())
        request.complete('Needs correction. I have a book.')
        self.assertTrue(self.page.chat_mode.isEnabled())

    def test_composer_keyboard_respects_line_breaks_and_ime(self):
        self.page.consent.setChecked(True)
        self.page.composer.setPlainText('First line')
        self.page.composer.moveCursor(self.page.composer.textCursor().MoveOperation.End)
        QTest.keyClick(self.page.composer, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.page.composer.toPlainText(), 'First line\n')
        self.application.sendEvent(self.page.composer, QInputMethodEvent('あ', []))
        QTest.keyClick(self.page.composer, Qt.Key.Key_Return)
        self.assertEqual(FakeWorker.instances, [])
        self.application.sendEvent(self.page.composer, QInputMethodEvent('', []))
        QTest.keyClick(self.page.composer, Qt.Key.Key_Return)
        self.assertEqual(FakeWorker.instances[-1].messages[-1]['content'], 'First line')
        FakeWorker.instances[-1].complete('Reply')

    def test_chat_preserves_both_message_directions_in_persian_ui(self):
        ui_i18n.set_language('fa')
        english = 'Yesterday I go to the library.'
        persian = 'دیروز به کتابخانه رفتم.'
        self.page.messages = [{'role':'assistant', 'content':english + '\n' + persian}]
        self.page.retranslate_ui()
        block = self.page.conversation.document().firstBlock()
        directions = {}
        while block.isValid():
            directions[block.text()] = block.textDirection()
            block = block.next()
        self.assertEqual(directions[english], Qt.LayoutDirection.LeftToRight)
        self.assertEqual(directions[persian], Qt.LayoutDirection.RightToLeft)

    def test_practice_starter_and_mode_survive_reopen_with_legacy_default(self):
        self.page.chat_mode.setCurrentIndex(self.page.chat_mode.findData('practice'))
        self.page.insert_practice_starter()
        draft = self.page.composer.toPlainText()
        self.assertIn('one short exercise', draft)
        self.assertEqual(FakeWorker.instances, [])
        self.assertTrue(self.page.shutdown())
        restored = panel.AIPage(lambda: self.raw)
        try:
            self.assertEqual(restored.chat_mode.currentData(), 'practice')
            self.assertEqual(restored.composer.toPlainText(), draft)
            self.assertFalse(restored.consent.isChecked())
        finally:
            restored.close()
        path = self.folder / 'ai-chats' / (self.page.chat_id + '.json')
        saved = json.loads(path.read_text(encoding='utf-8'))
        del saved['mode']
        path.write_text(json.dumps(saved), encoding='utf-8')
        legacy = panel.AIPage(lambda: self.raw)
        try:
            self.assertEqual(legacy.chat_mode.currentData(), 'chat')
            self.assertEqual(legacy.composer.toPlainText(), draft)
        finally:
            legacy.close()

    def test_failed_question_restored_without_polluting_followup_history(self):
        self.page.consent.setChecked(True);self.page.composer.setPlainText('Failed question');self.page.send_chat()
        FakeWorker.instances[-1].fail()
        self.assertEqual(self.page.messages,[])
        self.assertEqual(self.page.composer.toPlainText(),'Failed question')
        self.page.composer.setPlainText('Retry question');self.page.send_chat()
        payload=FakeWorker.instances[-1].messages
        self.assertFalse(any(m['content']=='Failed question' for m in payload))
        FakeWorker.instances[-1].complete('Successful answer')

    def test_cancellation_restores_draft_and_keeps_reference_stable(self):
        self.page.set_transcript(self.raw);self.page.consent.setChecked(True)
        self.page.composer.setPlainText('Question');self.page.send_chat()
        worker=FakeWorker.instances[-1]
        self.assertFalse(self.page.set_transcript('replacement'))
        self.assertEqual(self.page.reference,self.raw)
        self.page.stop_chat();worker.complete('Late answer')
        self.assertEqual(self.page.messages,[])
        self.assertEqual(self.page.composer.toPlainText(),'Question')

    def test_followup_retains_context_but_reference_change_starts_new_chat(self):
        self.page.set_transcript(self.raw);self.page.consent.setChecked(True)
        self.page.composer.setPlainText('First');self.page.send_chat();FakeWorker.instances[-1].complete('First reply')
        self.page.composer.setPlainText('Followup');self.page.send_chat()
        payload=FakeWorker.instances[-1].messages
        self.assertEqual([m['content'] for m in payload[-3:]],['First','First reply','Followup'])
        FakeWorker.instances[-1].complete('Second reply');old_id=self.page.chat_id
        self.assertTrue(self.page.set_transcript('New transcript'))
        self.assertNotEqual(self.page.chat_id,old_id);self.assertEqual(self.page.messages,[])
        self.assertFalse(self.page.consent.isChecked())

    def test_saved_chat_deleted_profile_cannot_reuse_another_provider_consent(self):
        self.page.set_transcript(self.raw);self.page.consent.setChecked(True)
        self.page.composer.setPlainText('Question');self.page.send_chat();FakeWorker.instances[-1].complete('Answer')
        saved=self.page.chat_id+'.json'
        contents=(self.folder/'ai-chats'/saved).read_text(encoding='utf-8')
        self.assertNotIn('unit-secret-key',contents)
        ai_profiles.delete_profile(self.profile_id)
        other=ai_profiles.save_profile({'name':'Other cloud','provider':'openai-compatible','model':'other','key':'other-dummy-key'})
        self.page.refresh_profiles(other);self.page.consent.setChecked(True)
        self.page.load_chat(self.page.saved_chats.findData(saved))
        self.assertIsNone(self.page.profiles.currentData());self.assertFalse(self.page.consent.isChecked())
        self.assertEqual(self.page.reference,self.raw)
        self.assertEqual(self.page.messages[-1]['content'],'Answer')

    def test_html_is_escaped_and_locale_changes_do_not_send_or_reset_consent(self):
        attack='<img src="https://evil.example/pixel"><script>alert(1)</script>'
        self.page.messages=[{'role':'assistant','content':attack}];self.page.render()
        self.assertNotIn('<img ',self.page.conversation.toHtml())
        self.assertIn(attack,self.page.conversation.toPlainText())
        self.page.consent.setChecked(True)
        for code in ['fa','tr','ar','az','en']:
            ui_i18n.set_language(code);self.page.retranslate_ui()
            self.assertTrue(self.page.consent.isChecked())
            self.assertEqual(FakeWorker.instances,[])
            dialog=panel.ProfileDialog(parent=self.page)
            form=dialog.findChild(QFormLayout)
            self.assertEqual(form.labelForField(dialog.name).text(),panel.t('Name'))
            self.assertEqual(dialog.clear_key.text(),panel.t('Forget existing key'))
            dialog.close()

    def test_repeated_voice_inputs_continue_the_same_chat_without_automatic_sending(self):
        self.page.set_transcript(self.raw)
        self.page.consent.setChecked(True)
        self.page.composer.setPlainText('Typed introduction')
        chat_id=self.page.chat_id
        self.page.set_voice_state('recording')
        self.page.set_voice_state('transcribing')
        self.page.append_voice_transcript('First voice question','voice-one.wav')
        self.assertEqual(FakeWorker.instances,[])
        self.assertEqual(self.page.composer.toPlainText(),'Typed introduction\n\nFirst voice question')
        self.assertEqual(self.page.chat_id,chat_id)
        self.assertEqual(self.page.reference,self.raw)
        self.assertTrue(self.page.consent.isChecked())
        self.page.send_chat();FakeWorker.instances[-1].complete('First answer')
        self.page.set_voice_state('transcribing')
        self.page.append_voice_transcript('Follow-up voice','voice-two.wav')
        self.assertEqual(len(FakeWorker.instances),1)
        self.assertEqual(self.page.chat_id,chat_id)
        self.page.send_chat()
        self.assertEqual([m['content'] for m in FakeWorker.instances[-1].messages[-3:]],
                         ['Typed introduction\n\nFirst voice question','First answer','Follow-up voice'])
        self.assertEqual(self.raw,'Original transcript <script>alert(1)</script>')
        FakeWorker.instances[-1].complete('Follow-up answer')

    def test_voice_controls_emit_only_explicit_actions_and_obey_busy_states(self):
        actions=[]
        self.page.record_requested.connect(lambda:actions.append('record'))
        self.page.audio_requested.connect(lambda:actions.append('audio'))
        self.page.cancel_voice_requested.connect(lambda:actions.append('cancel'))
        self.page.settings_requested.connect(lambda:actions.append('settings'))
        self.page.set_speech_settings('Persian · local Whisper · microphone',ready=True,microphone_available=True)
        self.page.record_voice.click()
        self.assertEqual(actions,['record'])
        self.page.set_voice_state('preparing')
        self.assertFalse(self.page.record_voice.isEnabled())
        self.assertFalse(self.page.send.isEnabled())
        self.page.set_voice_state('recording')
        self.assertTrue(self.page.record_voice.isEnabled())
        self.page.record_voice.click()
        self.page.set_voice_state('transcribing')
        self.assertFalse(self.page.attach_audio.isEnabled())
        self.assertTrue(self.page.composer.isEnabled())
        self.page.voice_cancel.click()
        self.page.set_voice_state('idle')
        self.page.attach_audio.click();self.page.speech_settings.click()
        self.assertEqual(actions,['record','record','cancel','audio','settings'])
        self.assertEqual(FakeWorker.instances,[])

    def test_voice_readiness_distinguishes_missing_microphone_and_model(self):
        self.page.set_speech_settings('No microphone',ready=True,microphone_available=False)
        self.assertFalse(self.page.record_voice.isEnabled())
        self.assertTrue(self.page.attach_audio.isEnabled())
        self.assertTrue(self.page.speech_settings.isEnabled())
        self.page.set_speech_settings('Download a speech model',ready=False,microphone_available=True)
        self.assertFalse(self.page.record_voice.isEnabled())
        self.assertFalse(self.page.attach_audio.isEnabled())
        self.assertTrue(self.page.speech_settings.isEnabled())

    def test_typing_during_transcription_is_retained_and_errors_preserve_draft(self):
        self.page.composer.setPlainText('Existing draft')
        self.page.set_voice_state('transcribing')
        self.page.composer.insertPlainText(' while decoding')
        draft=self.page.composer.toPlainText()
        self.page.voice_failed('Mock microphone failure')
        self.assertEqual(self.page.composer.toPlainText(),draft)
        self.assertEqual(self.page.voice_state,'idle')
        self.page.set_voice_state('transcribing')
        self.page.append_voice_transcript('')
        self.assertEqual(self.page.composer.toPlainText(),draft)
        self.page.set_voice_state('transcribing')
        self.page.append_voice_transcript('Decoded speech')
        self.assertEqual(self.page.composer.toPlainText(),draft+'\n\nDecoded speech')

    def test_voice_processing_blocks_sending_and_conversation_switching(self):
        self.page.composer.setPlainText('Unsent question')
        self.page.consent.setChecked(True)
        chat_id=self.page.chat_id
        self.page.set_voice_state('transcribing')
        self.page.send_chat();self.page.new_chat()
        self.assertFalse(self.page.set_transcript('Changed reference'))
        self.assertEqual(FakeWorker.instances,[])
        self.assertEqual(self.page.chat_id,chat_id)
        self.assertEqual(self.page.composer.toPlainText(),'Unsent question')
        self.page.set_voice_state('idle')

    def test_new_chat_saves_unsent_draft_and_loading_preserves_both_conversations(self):
        self.page.set_transcript(self.raw)
        self.page.composer.setPlainText('Unsent draft in first chat')
        first=self.page.chat_id
        self.page.new_chat()
        self.assertNotEqual(self.page.chat_id,first)
        self.assertEqual(self.page.reference,'')
        self.assertEqual(self.page.composer.toPlainText(),'')
        self.page.composer.setPlainText('Unsent second chat')
        second=self.page.chat_id
        self.page.load_chat(self.page.saved_chats.findData(first+'.json'))
        self.assertEqual(self.page.chat_id,first)
        self.assertEqual(self.page.composer.toPlainText(),'Unsent draft in first chat')
        self.assertEqual(self.page.reference,self.raw)
        self.page.load_chat(self.page.saved_chats.findData(second+'.json'))
        self.assertEqual(self.page.composer.toPlainText(),'Unsent second chat')

    def test_shutdown_persists_latest_draft_and_restart_restores_it_without_consent(self):
        self.page.set_transcript(self.raw)
        self.page.consent.setChecked(True)
        self.page.composer.setPlainText('Latest draft without waiting for autosave')
        saved_id=self.page.chat_id
        self.assertTrue(self.page.shutdown())
        other=panel.AIPage(lambda:self.raw)
        try:
            self.assertEqual(other.chat_id,saved_id)
            self.assertEqual(other.composer.toPlainText(),'Latest draft without waiting for autosave')
            self.assertEqual(other.reference,self.raw)
            self.assertFalse(other.consent.isChecked())
            self.assertEqual(FakeWorker.instances,[])
        finally:other.close()

    def test_autosaved_pending_question_restores_as_draft_after_interruption(self):
        self.page.consent.setChecked(True)
        self.page.composer.setPlainText('Question in flight')
        self.page.send_chat()
        other=panel.AIPage(lambda:self.raw)
        try:
            self.assertEqual(other.composer.toPlainText(),'Question in flight')
            self.assertEqual(other.messages,[])
            self.assertEqual(other.pending_question,'')
            self.assertFalse(other.consent.isChecked())
        finally:other.close()
        FakeWorker.instances[-1].fail()

    def test_save_failure_keeps_visible_draft_and_prevents_switch(self):
        self.page.composer.setPlainText('Do not lose this draft')
        old_id=self.page.chat_id
        with patch.object(panel,'atomic_write_text',side_effect=PermissionError('Mock busy file')):
            self.page.new_chat()
            self.assertFalse(self.page.shutdown())
        self.assertEqual(self.page.chat_id,old_id)
        self.assertEqual(self.page.composer.toPlainText(),'Do not lose this draft')

    def test_voice_save_failure_keeps_text_and_shows_storage_error(self):
        self.page.composer.setPlainText('Existing draft')
        with patch.object(panel,'atomic_write_text',side_effect=PermissionError('Mock busy file')):
            self.page.append_voice_transcript('Voice text')
        self.assertEqual(self.page.composer.toPlainText(),'Existing draft\n\nVoice text')
        self.assertIn('could not be saved',self.page.status.text())

    def test_deleting_chat_does_not_resave_it_from_pending_autosave(self):
        self.page.composer.setPlainText('Delete this saved draft')
        self.page.save_chat()
        target=self.folder/'ai-chats'/(self.page.chat_id+'.json')
        self.assertTrue(target.is_file())
        with patch.object(panel.QMessageBox,'question',return_value=panel.QMessageBox.StandardButton.Yes):
            self.page.delete_chat()
        self.assertFalse(target.exists())
        self.assertEqual(self.page.composer.toPlainText(),'')
        self.assertFalse(self.page.autosave.isActive())
        self.page.shutdown()
        self.assertFalse(target.exists())

    def test_export_contains_messages_and_draft_without_profile_credentials(self):
        self.page.messages=[{'role':'user','content':'Question'},{'role':'assistant','content':'Answer'}]
        self.page.composer.setPlainText('Unsent draft')
        destination=self.folder/'export.md'
        with patch.object(panel.QFileDialog,'getSaveFileName',return_value=(str(destination),'Markdown (*.md)')):
            self.page.export_chat()
        text=destination.read_text(encoding='utf-8')
        self.assertIn('Question',text)
        self.assertIn('Answer',text)
        self.assertIn('Unsent draft',text)
        self.assertNotIn('unit-secret-key-not-real',text)


if __name__=='__main__':unittest.main()
