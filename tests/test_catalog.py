"""Catalog/readiness contracts: all fixtures are tiny, local, and synthetic."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import model_catalog as catalog


class CatalogContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.environment=patch.dict(os.environ,{'VOXRIVA_DATA_DIR':str(self.root/'cache'),'AZB_DATA_DIR':''})
        self.environment.start()
        self.legacy=patch.object(catalog,'_legacy_roots',return_value=[])
        self.legacy.start()
        self.payloads={'config.json':b'{"model_type":"whisper"}','model.bin':b'fake weights',
                       'tokenizer.json':b'{}','vocabulary.txt':b'one\n'}
        self.model={'key':'catalog-fixture','backend':'faster-whisper','repo':'fixture/model','revision':'a'*40,
                    'weight_bytes':len(self.payloads['model.bin']),'subfolder':'','files':list(self.payloads),
                    'bytes':sum(map(len,self.payloads.values())),'artifacts':[
                        {'name':name,'size':len(value),'sha256':hashlib.sha256(value).hexdigest()}
                        for name,value in self.payloads.items()]}
        catalog.CATALOG.append(self.model)

    def tearDown(self):
        catalog.CATALOG.remove(self.model)
        self.legacy.stop();self.environment.stop();self.tmp.cleanup()

    def write_files(self,folder):
        folder.mkdir(parents=True,exist_ok=True)
        for name,value in self.payloads.items():(folder/name).write_bytes(value)

    def marker(self,folder,**overrides):
        value={'repo':self.model['repo'],'revision':self.model['revision'],'files':self.model['artifacts']}
        value.update(overrides)
        (folder/'completed.json').write_text(json.dumps(value),encoding='utf-8')

    def test_directory_and_partial_files_are_never_ready(self):
        folder=catalog.model_dir(self.model['key']);folder.mkdir(parents=True)
        self.assertIsNone(catalog.find_local_model(self.model['key']))
        self.write_files(folder)
        self.assertIsNone(catalog.find_local_model(self.model['key']))
        self.marker(folder)
        self.assertEqual(catalog.find_local_model(self.model['key']),folder)
        (folder/'vocabulary.txt').unlink()
        self.assertIsNone(catalog.find_local_model(self.model['key']))

    def test_marker_revision_size_and_path_traversal_rejected(self):
        folder=catalog.model_dir(self.model['key']);self.write_files(folder)
        self.marker(folder,revision='b'*40)
        self.assertIsNone(catalog.find_local_model(self.model['key']))
        self.marker(folder,files=[{'name':'../outside','size':1,'sha256':'0'*64}])
        self.assertIsNone(catalog.find_local_model(self.model['key']))
        self.marker(folder)
        (folder/'model.bin').write_bytes(b'x')
        self.assertIsNone(catalog.find_local_model(self.model['key']))

    def test_malformed_marker_never_crashes_readiness(self):
        folder=catalog.model_dir(self.model['key']);self.write_files(folder)
        for invalid in ['not json','[]','null','"string"','123','{"files":null}']:
            with self.subTest(marker=invalid):
                (folder/'completed.json').write_text(invalid,encoding='utf-8')
                self.assertIsNone(catalog.find_local_model(self.model['key']))

    def test_registered_local_reference_never_copies_model(self):
        external=self.root/'chosen-model';self.write_files(external)
        self.assertGreater(catalog.register_local_root(external),0)
        self.assertEqual(catalog.find_local_model(self.model['key']),external)
        self.assertFalse(catalog.model_dir(self.model['key']).exists())
        self.assertEqual((external/'model.bin').read_bytes(),self.payloads['model.bin'])
        self.assertEqual(json.loads((catalog.data_root()/'model-roots.json').read_text(encoding='utf-8')),
                         [str(external.resolve())])

    def test_broken_config_never_ready_even_with_matching_file_size(self):
        folder=catalog.model_dir(self.model['key']);self.write_files(folder);self.marker(folder)
        size=len(self.payloads['config.json'])
        for invalid in ['[]','null','"string"','123','not json']:
            with self.subTest(config=invalid):
                (folder/'config.json').write_text(invalid.ljust(size),encoding='utf-8')
                self.assertIsNone(catalog.find_local_model(self.model['key']))

    def test_whisper_is_shared_and_each_new_model_appears_only_for_supported_languages(self):
        expected={m['key'] for m in catalog.CATALOG if m['backend']=='faster-whisper'}
        for language in catalog.LANGUAGES:
            with self.subTest(language=language['code']):
                models=catalog.models_for_language(language['code'])
                if language['code']=='azb':
                    self.assertEqual({x['backend'] for x in models}, {'transformers', 'sherpa-omnilingual'})
                    self.assertTrue(expected.isdisjoint({x['key'] for x in models}))
                else:self.assertTrue(expected.issubset({x['key'] for x in models}))
        self.assertTrue({'qwen3-asr-06b', 'sensevoice-small', 'parakeet-tdt-v3'}.issubset(
            {m['key'] for m in catalog.models_for_language('en')}))
        for language in ('fa', 'tr'):
            keys = {m['key'] for m in catalog.models_for_language(language)}
            self.assertIn('qwen3-asr-06b', keys)
            self.assertNotIn('parakeet-tdt-v3', keys)
            self.assertNotIn('sensevoice-small', keys)
        self.assertNotIn('qwen3-asr-06b', {m['key'] for m in catalog.models_for_language('uk')})
        for code in ['unknown','azj',None]:
            with self.assertRaises(ValueError):catalog.models_for_language(code)

    def test_new_models_expand_choices_without_extrapolating_speech_languages(self):
        omni = catalog.get_model('omnilingual-ctc-300m')
        self.assertTrue(omni['cpu_only'] and omni['automatic_language'])
        self.assertEqual(len(omni['languages']), 97)
        for code in ('azb', 'fa', 'tr', 'es', 'ja', 'zh'):
            self.assertIn(omni, catalog.models_for_language(code))
        for code in ('nn', 'sa'):
            self.assertNotIn(omni, catalog.models_for_language(code))
        medium = catalog.get_model('multilingual-medium')
        self.assertEqual(medium['bytes'], sum(file['size'] for file in medium['artifacts']))
        self.assertNotIn(medium, catalog.models_for_language('azb'))
        for row in catalog.LANGUAGES:
            self.assertGreaterEqual(len(catalog.models_for_language(row['code'])), 4)

    def test_storage_alias_precedence_and_no_source_tree_cache(self):
        self.assertEqual(catalog.data_root(),self.root/'cache')
        with patch.dict(os.environ,{'AVUNOTE_DATA_DIR':str(self.root/'new-cache')}):
            self.assertEqual(catalog.data_root(),self.root/'new-cache')
        with patch.dict(os.environ,{'VOXRIVA_DATA_DIR':'','AZB_DATA_DIR':str(self.root/'legacy-cache')}):
            self.assertEqual(catalog.data_root(),self.root/'legacy-cache')
        with patch.dict(os.environ,{'VOXRIVA_DATA_DIR':'','AZB_DATA_DIR':'','LOCALAPPDATA':str(self.root/'appdata')}):
            self.assertEqual(catalog.data_root(),self.root/'appdata/AZBVoiceStudio')


class NoNetwork(unittest.TestCase):
    def test_import_and_fresh_catalog_do_not_connect(self):
        with tempfile.TemporaryDirectory() as directory,\
             patch.dict(os.environ,{'VOXRIVA_DATA_DIR':directory}),\
             patch('socket.create_connection',side_effect=AssertionError('Network forbidden')),\
             patch('requests.sessions.Session.request',side_effect=AssertionError('Network forbidden')):
            importlib.reload(catalog)
            with patch.object(catalog,'_legacy_roots',return_value=[]):
                for model in catalog.CATALOG:
                    self.assertIsNone(catalog.find_local_model(model['key']))


if __name__=='__main__':unittest.main()
