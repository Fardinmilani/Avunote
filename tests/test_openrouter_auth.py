"""Browser connection tests with a real loopback callback and fake provider."""

from base64 import urlsafe_b64encode
from hashlib import sha256
from http.client import HTTPConnection
import os
from pathlib import Path
from queue import SimpleQueue
import sys
from threading import Event, Thread
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QWidget
    import openrouter_auth
except ImportError:
    openrouter_auth = None


@unittest.skipIf(openrouter_auth is None, 'Qt dependencies are not installed')
class OpenRouterAuthTests(unittest.TestCase):
    def test_browser_callback_verifies_path_host_state_and_pkce(self):
        auth = openrouter_auth
        cancelled, results = Event(), SimpleQueue()
        listener = auth._LoopbackCallback('Return to Avunote.')
        url = urlsplit(listener.authorization_url())
        params = parse_qs(url.query)
        self.assertEqual((url.scheme, url.hostname, url.path), ('https', 'openrouter.ai', '/auth'))
        self.assertEqual(params['code_challenge_method'], ['S256'])
        challenge = urlsafe_b64encode(sha256(listener.verifier.encode('ascii')).digest()).rstrip(b'=').decode()
        self.assertEqual(params['code_challenge'], [challenge])
        self.assertNotIn(listener.verifier, listener.authorization_url())
        callback = urlsplit(params['callback_url'][0])
        self.assertEqual((callback.scheme, callback.hostname), ('http', '127.0.0.1'))
        self.assertEqual(callback.port, listener.server_port)

        def visit(path, headers=None):
            conn = HTTPConnection(callback.hostname, callback.port, timeout=2)
            try:
                conn.request('GET', path, headers=headers or {})
                response = conn.getresponse()
                return response.status, response.read(), response.getheader('Cache-Control')
            finally:
                conn.close()

        code, key = 'fake-one-time-code', 'sk-or-v1-unit-test-key'
        valid = urlencode({'state': params['state'][0], 'code': code})
        worker = Thread(target=auth._authorize, args=(listener, cancelled, results), daemon=True)
        with patch.object(auth, '_exchange_code', return_value=key) as exchange:
            worker.start()
            try:
                self.assertEqual(visit('/wrong?' + valid)[0], 404)
                self.assertEqual(visit(callback.path + '?state=wrong&code=' + code)[0], 400)
                self.assertEqual(visit(callback.path + '?' + valid + '&code=duplicate')[0], 400)
                self.assertEqual(visit(callback.path + '?' + valid, {'Host': 'example.test'})[0], 400)
                exchange.assert_not_called()
                status, body, cache_control = visit(callback.path + '?' + valid)
                self.assertEqual(status, 200)
                self.assertEqual(cache_control, 'no-store')
                self.assertNotIn(code.encode(), body)
                self.assertNotIn(key.encode(), body)
                self.assertEqual(results.get(timeout=2), ('connecting', None))
                self.assertEqual(results.get(timeout=2), ('connected', key))
                exchange.assert_called_once_with(code, listener.verifier, cancelled)
            finally:
                cancelled.set()
                worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(listener.socket.fileno(), -1)

    def test_cancelled_sign_in_does_not_request_a_key(self):
        auth = openrouter_auth
        cancelled, results = Event(), SimpleQueue()
        listener = auth._LoopbackCallback('Return to Avunote.')
        cancelled.set()
        with patch.object(auth, '_exchange_code') as exchange:
            auth._authorize(listener, cancelled, results)
        self.assertTrue(results.empty())
        exchange.assert_not_called()
        self.assertEqual(listener.socket.fileno(), -1)

    def test_exchange_uses_only_the_official_endpoint_without_redirects(self):
        auth = openrouter_auth
        with patch.object(auth.requests, 'Session') as session_type:
            session = session_type.return_value.__enter__.return_value
            response = session.post.return_value.__enter__.return_value
            response.status_code = 200
            response.iter_content.return_value = [b'{"key":"sk-or-v1-unit-test-key"}']
            self.assertEqual(auth._exchange_code('auth-code', 'secret-verifier', Event()),
                             'sk-or-v1-unit-test-key')
            endpoint, = session.post.call_args.args
            self.assertEqual(endpoint, 'https://openrouter.ai/api/v1/auth/keys')
            sent = session.post.call_args.kwargs
            self.assertFalse(sent['allow_redirects'])
            self.assertFalse(session.trust_env)
            self.assertEqual(sent['json'], {'code': 'auth-code', 'code_verifier': 'secret-verifier',
                                            'code_challenge_method': 'S256'})
            response.status_code = 307
            response.iter_content.reset_mock()
            with self.assertRaises(auth.AuthError):
                auth._exchange_code('auth-code', 'secret-verifier', Event())
            response.iter_content.assert_not_called()
            response.status_code = 200
            response.iter_content.return_value = [b'x' * (auth._MAX_REPLY + 1)]
            with self.assertRaises(auth.AuthError):
                auth._exchange_code('auth-code', 'secret-verifier', Event())

    def test_browser_profile_is_protected_and_routes_free_requests_only(self):
        auth = openrouter_auth
        from ai_clients import _endpoint, _payload, validate_profile

        with patch.object(auth, 'save_profile', return_value='openrouter-free') as save:
            self.assertEqual(auth._save_connection('sk-or-v1-unit-test-key'), 'openrouter-free')
        profile, = save.call_args.args
        self.assertTrue(profile['store_key'])
        config = validate_profile(profile)
        self.assertEqual(_endpoint(config), 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(_payload(config, [])['provider']['max_price'], {
            'prompt': 0, 'completion': 0, 'request': 0,
        })
        with self.assertRaises(auth.AIError):
            validate_profile({**profile, 'model': 'openrouter/auto'})
        with self.assertRaises(auth.AIError):
            validate_profile({**profile, 'base_url': 'https://example.test/v1'})

    def test_dialog_completes_after_browser_callback_without_exposing_key(self):
        auth = openrouter_auth
        app = QApplication.instance() or QApplication([])
        parent = QWidget()
        browser_result = SimpleQueue()
        browser_workers = []

        def open_browser(url):
            params = parse_qs(urlsplit(url.toString()).query)
            callback = urlsplit(params['callback_url'][0])

            def redirect():
                conn = HTTPConnection(callback.hostname, callback.port, timeout=2)
                try:
                    path = callback.path + '?' + urlencode({'state': params['state'][0], 'code': 'test-code'})
                    conn.request('GET', path)
                    response = conn.getresponse()
                    browser_result.put((response.status, response.read()))
                finally:
                    conn.close()

            worker = Thread(target=redirect, daemon=True)
            browser_workers.append(worker)
            worker.start()
            return True

        def watchdog():
            dialog = app.activeModalWidget()
            if dialog:
                dialog.reject()

        key = 'sk-or-v1-unit-test-key'
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(watchdog)
        guard.start(4000)
        try:
            with patch.object(auth.QDesktopServices, 'openUrl', side_effect=open_browser), \
                 patch.object(auth, '_exchange_code', return_value=key), \
                 patch.object(auth, '_save_connection', return_value='openrouter-free') as save:
                self.assertEqual(auth.connect_openrouter(parent), 'openrouter-free')
                save.assert_called_once_with(key)
                status, page = browser_result.get(timeout=2)
                self.assertEqual(status, 200)
                self.assertNotIn(key.encode(), page)
        finally:
            guard.stop()
            for worker in browser_workers:
                worker.join(3)
            parent.close()


if __name__ == '__main__':
    unittest.main()
