"""Packaging entry-point checks. Network is not required."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import entrypoint


class SelfTest(unittest.TestCase):
    def test_self_test_loads_ssl_and_certifi(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            self.assertEqual(entrypoint._self_test(output, None), 0)
            report = output.read_text(encoding='utf-8')
        self.assertIn('"ok": true', report)
        self.assertIn('openssl', report)
        self.assertIn('ca_certificates', report)

    def test_self_test_reports_missing_ssl(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            with patch.dict(sys.modules, {'ssl': None}):
                self.assertEqual(entrypoint._self_test(output, None), 1)
            report = output.read_text(encoding='utf-8')
        self.assertIn('"ok": false', report)
        self.assertRegex(report, r'(ImportError|ModuleNotFoundError)')

    def test_guard_https_rewrites_urllib3_when_ssl_missing(self):
        from urllib3 import connectionpool
        original = connectionpool.HTTPSConnectionPool._new_conn
        try:
            with patch.dict(sys.modules, {'ssl': None}):
                entrypoint._guard_https()
            with self.assertRaises(ImportError) as raised:
                connectionpool.HTTPSConnectionPool(host='huggingface.co', port=443)._new_conn()
            self.assertIn('OpenSSL', str(raised.exception))
            self.assertNotIn('SSL module is not available', str(raised.exception))
        finally:
            connectionpool.HTTPSConnectionPool._new_conn = original
