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

import app_updates as updates


class UpdateTests(unittest.TestCase):
    def _asset(self, name, size=1000, digest='b' * 64):
        return {
            'name': name, 'state': 'uploaded', 'size': size, 'digest': 'sha256:' + digest,
            'browser_download_url': f'https://github.com/{updates.REPOSITORY}/releases/download/v2.4.1/{name}',
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


if __name__ == '__main__':
    unittest.main()
