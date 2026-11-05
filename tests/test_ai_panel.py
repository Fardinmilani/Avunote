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
    from PySide6.QtCore import QObject,Signal
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


if __name__=='__main__':unittest.main()
