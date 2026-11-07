"""Update trust boundary and model-free delta baseline checks."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))

import requests
import app_updates as updates


class _ApiResponse:
    def __init__(self, status, payload=None, location=None):
        self.status_code = status
        self.headers = {'Location': location} if location else {}
        if payload is None:
            self._body = b''
        elif isinstance(payload, bytes):
            self._body = payload
        else:
            self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(str(self.status_code))
            error.response = self
            raise error

    def iter_content(self, size):
        yield self._body


class UpdateTests(unittest.TestCase):
    def _asset(self, name, size=1000, digest='b' * 64, repository=None):
        repository = repository or updates.REPOSITORY
        return {
            'name': name, 'state': 'uploaded', 'size': size, 'digest': 'sha256:' + digest,
            'browser_download_url': f'https://github.com/{repository}/releases/download/v2.4.1/{name}',
        }

    def _release(self, *assets):
        return {'tag_name': 'v2.4.1', 'draft': False, 'prerelease': False, 'assets': list(assets)}

    def test_selects_smaller_update_for_exact_baseline_and_full_setup_otherwise(self):
        baseline = 'a' * 64
        setup = self._asset(updates.setup_name('2.4.1'))
        delta = self._asset(updates.delta_name('2.4.1', '2.4.0', baseline), 100)
        content = self._release(setup, delta)
        release = updates.parse_release(content, '2.4.0', baseline)
        self.assertEqual(release.delta.size, 100)
        self.assertIsNone(updates.parse_release(content, '2.4.0', 'f' * 64).delta)
        self.assertIsNone(updates.parse_release(content, '2.4.1', baseline))
        self.assertIsNone(updates.parse_release(content, '2.4.9', baseline))
        content['prerelease'] = True
        self.assertIsNone(updates.parse_release(content, '2.4.0', baseline))

    def test_requires_github_digest_and_canonical_repository_url(self):
        asset = self._asset(updates.setup_name('2.4.1'))
        for values in ({'digest': None}, {'browser_download_url': 'https://other.invalid/fake.exe'},
                       {'size': -1}, {'state': 'new'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                updates.parse_release(self._release(dict(asset, **values)), '2.4.0')

    def test_incomplete_or_changed_installation_cannot_take_delta(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            data = b'original'
            exe = root / 'Avunote.exe'
            exe.write_bytes(data)
            contents = {'schema': 1, 'version': '2.4.0', 'files': [
                {'path': 'Avunote.exe', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()},
                {'path': '_internal/transformers/models/example.py', 'bytes': len(data),
                 'sha256': hashlib.sha256(data).hexdigest()},
            ]}
            library = root / '_internal/transformers/models/example.py'
            library.parent.mkdir(parents=True)
            library.write_bytes(data)
            manifest = root / updates.MANIFEST_NAME
            manifest.write_text(json.dumps(contents), encoding='utf-8')
            self.assertIsNotNone(updates.baseline_digest(root, '2.4.0', verify_files=True))
            exe.write_bytes(b'changed!')
            self.assertIsNone(updates.baseline_digest(root, '2.4.0', verify_files=True))
            contents['files'].append({'path': 'app/../anything', 'bytes': 1, 'sha256': 'a' * 64})
            manifest.write_text(json.dumps(contents), encoding='utf-8')
            self.assertIsNone(updates.baseline_digest(root, '2.4.0'))

    def test_staging_checks_hash_size_and_cancel_without_publishing_partial_files(self):
        data = b'synthetic installer fixture'
        name = updates.setup_name('2.4.1')
        cancel = threading.Event()
        progress = []

        class Response:
            status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return None

            def raise_for_status(self):
                return None

            def iter_content(self, size):
                yield data

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bad = updates.parse_release(self._release(self._asset(name, len(data))), '2.4.0').setup
            with patch.object(updates, '_download_response', return_value=Response()):
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    updates.stage_update(bad, root, cancel)
                self.assertEqual(list(root.iterdir()), [])
                good = updates.parse_release(self._release(
                    self._asset(name, len(data), hashlib.sha256(data).hexdigest())), '2.4.0').setup
                cancel.set()
                with self.assertRaises(updates.UpdateCancelled):
                    updates.stage_update(good, root, cancel)
                self.assertEqual(list(root.iterdir()), [])
                cancel.clear()
                self.assertEqual(updates.stage_update(good, root, cancel, lambda n, size: progress.append(n)),
                                 root / name)
                self.assertEqual(progress, [len(data)])
                self.assertTrue(updates.verify_staged(root / name, good))

    def test_missing_releases_and_same_or_older_tags_are_up_to_date(self):
        responses = [_ApiResponse(404), _ApiResponse(404)]

        def missing(url, **kwargs):
            self.assertIn(url, {
                'https://api.github.com/repos/Fardinmilani/Avunote/releases/latest',
                'https://api.github.com/repos/Fardinmilani/Voxriva/releases/latest',
            })
            return responses.pop(0)

        with patch.object(updates.requests, 'get', side_effect=missing):
            self.assertIsNone(updates.check_release('2.4.0'))
        current = self._release(self._asset(updates.setup_name('2.4.1')))
        current['tag_name'] = 'v2.4.0'
        with patch.object(updates.requests, 'get', return_value=_ApiResponse(200, current)):
            self.assertIsNone(updates.check_release('2.4.0'))

    def test_follows_rename_redirects_and_legacy_voxriva_download_urls(self):
        setup = self._asset(updates.setup_name('2.4.1'), repository='Fardinmilani/Voxriva')
        payload = self._release(setup)
        responses = [
            _ApiResponse(301, location='https://api.github.com/repositories/1444103502/releases/latest'),
            _ApiResponse(200, payload),
        ]
        with patch.object(updates.requests, 'get', side_effect=lambda url, **kwargs: responses.pop(0)):
            release = updates.check_release('2.4.0')
        self.assertEqual(release.version, '2.4.1')
        self.assertEqual(release.setup.url, setup['browser_download_url'])

    def test_falls_back_to_former_repository_name_when_new_name_has_no_release(self):
        setup = self._asset(updates.setup_name('2.4.1'), repository='Fardinmilani/Voxriva')
        responses = [_ApiResponse(404), _ApiResponse(200, self._release(setup))]
        with patch.object(updates.requests, 'get', side_effect=lambda url, **kwargs: responses.pop(0)):
            self.assertEqual(updates.check_release('2.4.0').setup.url, setup['browser_download_url'])

    def test_skips_prerelease_and_rejects_assets_without_github_digest(self):
        setup = self._asset(updates.setup_name('2.4.1'))
        pre = self._release(setup)
        pre['prerelease'] = True
        with patch.object(updates.requests, 'get', return_value=_ApiResponse(200, pre)):
            self.assertIsNone(updates.check_release('2.4.0'))
        with patch.object(updates.requests, 'get',
                          return_value=_ApiResponse(200, self._release(dict(setup, digest=None)))):
            with self.assertRaises(ValueError):
                updates.check_release('2.4.0')


if __name__ == '__main__':
    unittest.main()
