"""Local-only download lifecycle tests. No model weights or external network."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import model_catalog as catalog
import model_downloads as downloads


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    payloads = {}
    mode = 'range'
    ranges = []
    interrupted = False
    ranged_416 = False
    tripped = False
    if_ranges = []
    encodings = []
    redirected = False

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).encodings.append(self.headers.get('Accept-Encoding'))
        if self.mode == 'redirect' and not self.path.startswith('/cdn/'):
            type(self).redirected = True
            self.send_response(302)
            self.send_header('Location', '/cdn' + self.path)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        name = self.path.strip('/').split('/')[-1]
        data = self.payloads[name]
        offset = int(self.headers.get('Range', 'bytes=0-').split('=')[1].split('-')[0])
        type(self).ranges.append(offset)
        type(self).if_ranges.append(self.headers.get('If-Range'))
        if self.mode == 'changed' and self.headers.get('If-Range') and offset:
            type(self).tripped = True
            offset = 0
        once = name == 'model.bin' and not type(self).tripped
        if self.mode == 'badrange' and offset and once:
            type(self).tripped = True
            self.send_response(206)
            self.send_header('Content-Length', str(len(data)-offset))
            self.send_header('Content-Range', f'bytes {offset+1}-{len(data)}/{len(data)+1}')
            self.end_headers()
            return
        if self.mode == 'oversize' and not offset and once:
            type(self).tripped = True
            data = data + b'extra'*4000
        if self.mode == 'once416' and offset and not type(self).ranged_416:
            type(self).ranged_416 = True
            self.send_response(416)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if self.mode == 'ignore':
            offset = 0
        if offset >= len(data):
            self.send_response(416)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(206 if offset else 200)
        self.send_header('Content-Length', str(len(data)-offset))
        self.send_header('ETag', 'W/"fixture"' if self.mode == 'weak' else '"fixture"')
        if offset:
            self.send_header('Content-Range', f'bytes {offset}-{len(data)-1}/{len(data)}')
        self.end_headers()
        try:
            for start in range(offset, len(data), 16*1024):
                self.wfile.write(data[start:start+16*1024])
                self.wfile.flush()
                if self.mode == 'interrupt' and name == 'model.bin' and not type(self).interrupted and start > 100000:
                    type(self).interrupted = True
                    self.close_connection = True
                    return
                if name == 'model.bin':
                    time.sleep(.003)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'AZB_DATA_DIR': self.tmp.name, 'VOXRIVA_DATA_DIR': ''})
        self.env.start()
        Handler.mode, Handler.ranges, Handler.interrupted, Handler.ranged_416 = 'range', [], False, False
        Handler.tripped, Handler.if_ranges, Handler.encodings, Handler.redirected = False, [], [], False
        Handler.payloads = {'config.json': b'{"model_type":"whisper"}', 'model.bin': b'fixture!'*256000,
                            'tokenizer.json': b'{}', 'vocabulary.txt': b'word\n'}
        self.model = {'key': 'fixture', 'title': 'fixture', 'backend': 'faster-whisper',
                      'repo': 'test/fixture', 'revision': 'a'*40, 'subfolder': '',
                      'url': 'https://huggingface.co/test/fixture', 'license': 'synthetic-test-license',
                      'license_url': 'https://example.invalid/test-license', 'attribution': 'Synthetic test fixture',
                      'model_license_basis': 'Unit test data only, independent of the application license',
                      'weight_bytes': len(Handler.payloads['model.bin']), 'bytes': sum(map(len,Handler.payloads.values())),
                      'files': list(Handler.payloads)}
        catalog.CATALOG.append(self.model)
        self.artifacts = [{'name': n, 'size': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
                           'url': f'http://127.0.0.1:{self.server.server_port}/{n}'}
                          for n,b in Handler.payloads.items()]
        self.resolve = patch.object(downloads, '_resolve_artifacts', return_value=self.artifacts)
        self.resolve.start()
        self.host = patch.object(downloads, '_validate_url', return_value=None)
        self.host.start()
        self.manager = downloads.DownloadManager()

    def tearDown(self):
        self.manager.close()
        self.host.stop(); self.resolve.stop()
        catalog.CATALOG.remove(self.model)
        self.env.stop(); self.tmp.cleanup()

    def wait(self, states, timeout=12):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            state = self.manager.snapshot('fixture')
            if state['status'] in states:
                return state
            time.sleep(.01)
        self.fail(self.manager.snapshot('fixture'))

    def start_partial(self):
        self.manager.start('fixture')
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            partial=catalog.model_dir('fixture')/'model.bin.part'
            if partial.exists() and partial.stat().st_size>128000:
                return
            time.sleep(.01)
        self.fail('No partial transfer observed')

    def test_pause_restart_resume_and_ready_marker(self):
        self.start_partial()
        self.manager.pause('fixture')
        self.wait({'paused'})
        self.assertIsNone(catalog.find_local_model('fixture'))
        self.assertTrue(self.manager.close())
        self.manager=downloads.DownloadManager()
        self.assertEqual(self.manager.snapshot('fixture')['status'], 'paused')
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(any(x>0 for x in Handler.ranges))
        self.assertIsNotNone(catalog.find_local_model('fixture'))
        marker=json.loads((catalog.model_dir('fixture')/'completed.json').read_text(encoding='utf-8'))
        source=json.loads((catalog.model_dir('fixture')/'model-source.json').read_text(encoding='utf-8'))
        for field in ['repo','revision','license','license_url','attribution','model_license_basis']:
            self.assertEqual(marker[field],self.model[field])
            self.assertEqual(source[field],self.model[field])
        self.assertEqual(source['source_url'],self.model['url'])
        (catalog.model_dir('fixture')/'tokenizer.json').unlink()
        self.assertIsNone(catalog.find_local_model('fixture'))

    def test_server_ignores_range(self):
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        Handler.mode='ignore'
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertEqual((catalog.model_dir('fixture')/'model.bin').read_bytes(),Handler.payloads['model.bin'])

    def test_interruption_retries_range(self):
        Handler.mode='interrupt'
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.interrupted)
        self.assertTrue(any(x>0 for x in Handler.ranges))

    def test_stale_range_416_restarts(self):
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        Handler.mode='once416'
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.ranged_416)

    def test_cancel_only_partials(self):
        self.start_partial(); self.manager.cancel('fixture')
        state=self.wait({'cancelled','error'})
        self.assertEqual(state['status'],'cancelled',state)
        self.assertFalse((catalog.model_dir('fixture')/'model.bin.part').exists())
        self.assertTrue((catalog.model_dir('fixture')/'config.json').exists())
        self.assertFalse((catalog.model_dir('fixture')/'completed.json').exists())

    def test_corrupt_hash_never_ready(self):
        self.artifacts[1]['sha256']='0'*64
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'error')
        self.assertEqual(state['error'],downloads.HASH_FAILED)
        self.assertIsNone(catalog.find_local_model('fixture'))
        self.assertFalse((catalog.model_dir('fixture')/'completed.json').exists())
        self.assertFalse((catalog.model_dir('fixture')/'model.bin.part').exists())

    def test_corrupt_partial_is_redownloaded_from_zero(self):
        folder=catalog.model_dir('fixture'); folder.mkdir(parents=True)
        (folder/'model.bin.part').write_bytes(b'X'*200000)
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertIn(200000,Handler.ranges)
        self.assertEqual((folder/'model.bin').read_bytes(),Handler.payloads['model.bin'])

    def test_invalid_content_range_restarts_instead_of_failing(self):
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        Handler.mode='badrange'
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.tripped)
        self.assertEqual((catalog.model_dir('fixture')/'model.bin').read_bytes(),Handler.payloads['model.bin'])

    def test_oversized_response_restarts(self):
        Handler.mode='oversize'
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.tripped)
        self.assertEqual((catalog.model_dir('fixture')/'model.bin').read_bytes(),Handler.payloads['model.bin'])

    def test_redirect_preserves_range_resume(self):
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        Handler.mode='redirect'
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.redirected)
        self.assertTrue(any(x>0 for x in Handler.ranges))
        self.assertTrue(any(value and 'identity' in value for value in Handler.encodings))

    def test_etag_change_rewrites_instead_of_appending(self):
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        Handler.mode='changed'
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(Handler.tripped)
        self.assertEqual((catalog.model_dir('fixture')/'model.bin').read_bytes(),Handler.payloads['model.bin'])

    def test_stale_transfer_lock_is_dropped(self):
        folder=catalog.model_dir('fixture'); folder.mkdir(parents=True)
        (folder/'model.bin.part').write_bytes(Handler.payloads['model.bin'][:180000])
        (folder/'transfer.json').write_text(json.dumps({
            'file': 'other.bin', 'revision': 'b'*40, 'etag': '"stale"'}), encoding='utf-8')
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(any(x>0 for x in Handler.ranges))
        self.assertFalse(any(value=='"stale"' for value in Handler.if_ranges))

    def test_weak_etag_is_never_sent_as_if_range(self):
        Handler.mode='weak'
        self.start_partial(); self.manager.pause('fixture'); self.wait({'paused'})
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertTrue(any(x>0 for x in Handler.ranges))
        self.assertFalse(any(value and value.startswith('W/') for value in Handler.if_ranges))

    def test_missing_ssl_reports_clear_error(self):
        with patch.dict(sys.modules,{'ssl':None}):
            self.manager.start('fixture')
            state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'error')
        self.assertEqual(state['error'],downloads.SSL_UNAVAILABLE)
        self.assertRegex(state['error_detail'], r'(ImportError|ModuleNotFoundError)')
        self.assertEqual(Handler.ranges,[])

    def test_retry_after_connection_error_downloads(self):
        self.resolve.stop()
        with patch.object(downloads,'_resolve_artifacts',side_effect=downloads.requests.ConnectionError('offline')):
            self.manager.start('fixture')
            state=self.wait({'completed','error'})
        self.assertEqual(state['error'],downloads.UNREACHABLE)
        self.assertIn('offline',state['error_detail'])
        self.resolve.start()
        self.manager.start('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)
        self.assertEqual((state['error'],state['error_detail']),('',''))

    def test_immediate_resume_after_pause_is_not_ignored(self):
        self.start_partial()
        self.manager.pause('fixture')
        self.manager.resume('fixture')
        state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'completed',state)

    def test_non_lfs_git_blob_hash(self):
        data=b'hello\n'
        artifact={'size':len(data),'git_sha1':hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()}
        path=Path(self.tmp.name)/'small.txt'; path.write_bytes(data)
        self.assertTrue(downloads._matches(path,artifact))
        artifact['git_sha1']='0'*40
        self.assertFalse(downloads._matches(path,artifact))

    def test_shutdown_pauses(self):
        self.start_partial()
        self.assertTrue(self.manager.close())
        self.assertEqual(self.manager.snapshot('fixture')['status'],'paused')

    def test_frozen_app_discovers_adjacent_legacy_cache_without_copy(self):
        fixture=Path(self.tmp.name)/'AZBVoiceStudio/Portable/_internal/assets/models/fixture'
        fixture.mkdir(parents=True)
        for name,data in Handler.payloads.items():
            (fixture/name).write_bytes(data)
        new_exe=Path(self.tmp.name)/'new/Portable/App.exe'
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(new_exe)):
            self.assertEqual(catalog.find_local_model('fixture'),fixture)
        self.assertFalse((catalog.model_dir('fixture')/'model.bin').exists())

    def test_state_write_failure_keeps_error_visible(self):
        with patch.object(downloads,'_atomic_json',side_effect=OSError('disk full')):
            self.manager._update('fixture',force=True,status='error',error='fixture failure')
        state=self.manager.snapshot('fixture')
        self.assertEqual(state['status'],'error')
        self.assertEqual(state['error'],'fixture failure')
        self.assertIn('disk full',state['persistence_error'])

    def test_completed_marker_failure_never_marks_ready(self):
        original=downloads._atomic_json
        def fail_marker(path,value):
            if path.name=='completed.json':
                raise OSError('disk full')
            return original(path,value)
        with patch.object(downloads,'_atomic_json',side_effect=fail_marker):
            self.manager.start('fixture')
            state=self.wait({'completed','error'})
        self.assertEqual(state['status'],'error')
        self.assertIsNone(catalog.find_local_model('fixture'))


class Errors(unittest.TestCase):
    class Session:
        def __init__(self, *results):
            self.trust_env, self.results, self.trust_history = True, list(results), []

        def get(self, url, **kwargs):
            self.trust_history.append(self.trust_env)
            result = self.results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    def test_dead_system_proxy_falls_back_to_direct(self):
        session = self.Session(downloads.requests.exceptions.ProxyError('proxy down'), 'response')
        self.assertEqual(downloads._get(session, 'https://huggingface.co/x'), 'response')
        self.assertEqual(session.trust_history, [True, False])
        self.assertTrue(session.trust_env)

    def test_proxy_error_is_kept_when_direct_also_fails(self):
        proxy = downloads.requests.exceptions.ProxyError('proxy down')
        session = self.Session(proxy, downloads.requests.ConnectionError('blocked'))
        with self.assertRaises(downloads.requests.exceptions.ProxyError):
            downloads._get(session, 'https://huggingface.co/x')
        self.assertTrue(session.trust_env)
        self.assertEqual(downloads.describe_error(proxy), downloads.PROXY_FAILED)

    def test_error_messages_are_specific_and_translated(self):
        import ui_i18n
        cases = [
            (ImportError("Can't connect to HTTPS URL because the SSL module is not available."), downloads.SSL_UNAVAILABLE),
            (downloads.requests.ConnectTimeout('slow'), downloads.UNREACHABLE),
            (downloads.requests.ReadTimeout('slow'), downloads.UNREACHABLE),
            (downloads.requests.HTTPError('403'), downloads.SERVER_REFUSED),
            (PermissionError('denied'), downloads.SAVE_FAILED),
            (downloads.DownloadError(downloads.DISK_FULL), downloads.DISK_FULL),
            (downloads.requests.exceptions.SSLError("Can't connect to HTTPS URL because the SSL module is not available"), downloads.SSL_UNAVAILABLE),
            (ValueError('anything else'), downloads.GENERIC_FAILURE),
        ]
        for error, message in cases:
            with self.subTest(error=error):
                self.assertEqual(downloads.describe_error(error), message)
                self.assertIn(message, ui_i18n.EN)
        self.assertIn(downloads.RESUME_BUSY, ui_i18n.EN)


class Security(unittest.TestCase):
    def test_no_implicit_application_license_for_models(self):
        with self.assertRaises(ValueError):downloads._provenance({'repo':'fixture/model','revision':'a'*40})
        for model in catalog.CATALOG:
            source=downloads._provenance(model)
            self.assertEqual(source['license'],model['license'])

    def test_untrusted_hosts_and_paths(self):
        for name in ['../model.bin','a/model.bin','..','C:\\file','/tmp/file']:
            with self.assertRaises(ValueError):catalog._safe_file(name)
        for url in ['http://huggingface.co/model','https://evil.test/model',
                    'https://huggingface.co.evil.test/model','https://user:pass@huggingface.co/model']:
            with self.assertRaises(ValueError):downloads._validate_url(url)
        downloads._validate_url('https://cas-bridge.xethub.hf.co/file')

    def test_bad_manifest_rejected_before_download(self):
        model=dict(catalog.get_model('multilingual-tiny'))
        model['artifacts']=[{'name':'../model.bin','size':1,'sha256':'0'*64}]
        with self.assertRaises(ValueError):downloads._resolve_artifacts(model,None)

    def test_pinned_onnx_artifact_manifests_and_nested_tokenizer(self):
        for model in catalog.CATALOG:
            if model['backend'] not in catalog.SHERPA_BACKENDS:
                continue
            with self.subTest(model=model['key']):
                artifacts = downloads._resolve_artifacts(model, None)
                self.assertEqual(sum(file['size'] for file in artifacts), model['bytes'])
                self.assertEqual({file['name'] for file in artifacts}, set(model['files']))
                self.assertTrue(all(model['revision'] in file['url'] for file in artifacts))
        qwen = catalog.get_model('qwen3-asr-06b')
        tokenizer = next(file for file in downloads._resolve_artifacts(qwen, None) if file['name'] == 'vocab.json')
        self.assertTrue(tokenizer['url'].endswith('/tokenizer/vocab.json?download=true'))
        invalid = {**qwen, 'artifacts': [dict(file, remote_prefix='../escape') for file in qwen['artifacts']]}
        with self.assertRaises(ValueError):downloads._resolve_artifacts(invalid, None)


if __name__=='__main__':
    unittest.main()
