"""Profile persistence and DPAPI tests. No API credentials or external calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import ai_profiles as profiles
from ai_clients import AIError


def value(**extra):
    return {'name':'Google','provider':'gemini','model':'example-model','key':'secret-profile-key-54321',**extra}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.folder = Path(temporary.name)
        self.addCleanup(temporary.cleanup)
        patcher = patch.object(profiles, 'data_root', return_value=self.folder)
        patcher.start(); self.addCleanup(patcher.stop)
        profiles._SESSION_KEYS.clear(); self.addCleanup(profiles._SESSION_KEYS.clear)

    def test_session_default_sanitized_list_and_no_plaintext_file(self):
        profile_id = profiles.save_profile(value())
        self.assertNotIn('secret-profile-key', (self.folder/'ai-profiles.json').read_text(encoding='utf-8'))
        shown = profiles.list_profiles()[0]
        self.assertTrue(shown['has_key']); self.assertFalse(shown['store_key'])
        self.assertEqual(shown['key_storage'], 'session')
        self.assertNotIn('key', shown); self.assertNotIn('key_ciphertext', shown)
        self.assertEqual(profiles.get_profile(profile_id)['key'], 'secret-profile-key-54321')
        self.assertNotIn('key', profiles.get_profile(profile_id, include_secret=False))
        profiles._SESSION_KEYS.clear()
        self.assertEqual(profiles.get_profile(profile_id)['key'], '')

    def test_set_profile_model_keeps_key_and_caches_valid_models(self):
        profile_id = profiles.save_profile(value())
        self.assertEqual(profiles.set_profile_model(profile_id, 'gemini-2.5-pro', ['gemini-2.5-pro', 'bad model', 'gemini-2.5-pro']),
                         'gemini-2.5-pro')
        shown = profiles.get_profile(profile_id)
        self.assertEqual(shown['model'], 'gemini-2.5-pro')
        self.assertEqual(shown['models'], ['gemini-2.5-pro'])
        self.assertEqual(shown['key'], 'secret-profile-key-54321')
        with self.assertRaises(AIError): profiles.set_profile_model(profile_id, 'bad model')
        self.assertEqual(profiles.get_profile(profile_id)['model'], 'gemini-2.5-pro')
        profiles.save_profile(value(id=profile_id, model='gemini-2.5-flash'))
        self.assertEqual(profiles.get_profile(profile_id)['models'], ['gemini-2.5-pro'])
        profiles.save_profile(value(id=profile_id, base_url='https://example.com/v1beta'))
        self.assertEqual(profiles.get_profile(profile_id)['models'], [])
        with self.assertRaises(AIError): profiles.set_profile_model('missing', 'x')

    def test_non_windows_session_only_notice(self):
        with patch.object(profiles,'persistent_keys_available',return_value=False):
            profile_id = profiles.save_profile(value(store_key=True))
            shown = profiles.get_profile(profile_id, include_secret=False)
            self.assertEqual(shown['key_storage'], 'session'); self.assertFalse(shown['store_key'])
            self.assertIn('session only', shown['storage_notice'])
            self.assertNotIn('secret-profile-key', (self.folder/'ai-profiles.json').read_text(encoding='utf-8'))

    @unittest.skipIf(sys.platform != 'win32','Windows DPAPI only')
    def test_real_dpapi_roundtrip_without_plaintext(self):
        profile_id = profiles.save_profile(value(store_key=True))
        payload = json.loads((self.folder/'ai-profiles.json').read_text(encoding='utf-8'))
        self.assertTrue(payload['profiles'][0]['key_ciphertext'].startswith('dpapi-v1:'))
        self.assertNotIn('secret-profile-key', json.dumps(payload))
        profiles._SESSION_KEYS.clear()
        self.assertEqual(profiles.get_profile(profile_id)['key'], 'secret-profile-key-54321')
        self.assertEqual(profiles.list_profiles()[0]['key_storage'], 'windows-dpapi')

    def test_edit_blank_preserves_key_clear_and_delete(self):
        profile_id = profiles.save_profile(value())
        profiles.save_profile(value(id=profile_id,name='Renamed',key=''))
        self.assertEqual(len(profiles.list_profiles()), 1)
        self.assertEqual(profiles.get_profile(profile_id)['key'], 'secret-profile-key-54321')
        profiles.save_profile(value(id=profile_id,key='',clear_key=True))
        self.assertFalse(profiles.list_profiles()[0]['has_key'])
        profiles.delete_profile(profile_id); self.assertEqual(profiles.list_profiles(), [])
        with self.assertRaises(AIError): profiles.get_profile(profile_id)

    def test_secret_metadata_and_unsafe_profile_rejected(self):
        with self.assertRaisesRegex(AIError,'password field'): profiles.save_profile(value(name='secret-profile-key-54321'))
        with self.assertRaises(AIError): profiles.save_profile(value(id='../../outside'))
        with self.assertRaises(AIError): profiles.save_profile(value(base_url='http://remote.example/v1'))
        self.assertFalse((self.folder/'ai-profiles.json').exists())

    def test_edit_cannot_leak_preserved_key_in_profile_name(self):
        profile_id = profiles.save_profile(value())
        with self.assertRaisesRegex(AIError, 'password field'):
            profiles.save_profile(value(id=profile_id, key='', name='secret-profile-key-54321'))
        self.assertNotIn('secret-profile-key', (self.folder/'ai-profiles.json').read_text(encoding='utf-8'))
        self.assertEqual(profiles.get_profile(profile_id)['name'], 'Google')

    def test_changing_provider_or_endpoint_does_not_reuse_old_secret(self):
        profile_id = profiles.save_profile(value())
        profiles.save_profile(value(id=profile_id, key='', base_url='https://other.example/v1beta'))
        self.assertEqual(profiles.get_profile(profile_id)['key'], '')

    def test_corrupt_settings_not_silently_overwritten(self):
        path = self.folder/'ai-profiles.json'; path.write_text('broken',encoding='utf-8')
        with self.assertRaises(AIError): profiles.save_profile(value())
        self.assertEqual(path.read_text(encoding='utf-8'),'broken')


if __name__ == '__main__': unittest.main()
