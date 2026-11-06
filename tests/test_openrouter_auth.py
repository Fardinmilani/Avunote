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
            self.assertTrue(session.trust_env)
            self.assertEqual(sent['json'], {'code': 'auth-code', 'code_verifier': 'secret-verifier',
                                            'code_challenge_method': 'S256'})
            response.status_code = 307
            response.iter_content.reset_mock()
            with self.assertRaises(auth.AuthError) as raised:
                auth._exchange_code('auth-code', 'secret-verifier', Event())
            self.assertEqual((raised.exception.kind, raised.exception.status), ('rejected', 307))
            response.iter_content.assert_not_called()
            response.status_code = 200
            response.iter_content.return_value = [b'x' * (auth._MAX_REPLY + 1)]
            with self.assertRaises(auth.AuthError):
                auth._exchange_code('auth-code', 'secret-verifier', Event())

    def test_unreachable_system_proxy_falls_back_to_a_direct_connection(self):
        auth = openrouter_auth
        modes = []

        def request_key(code, verifier, cancelled, use_system_proxy):
            modes.append(use_system_proxy)
            if use_system_proxy:
                raise auth.AuthError('network', retryable=True)
            return 'sk-or-v1-unit-test-key'

        with patch.object(auth, '_system_proxy_configured', return_value=True), \
             patch.object(auth, '_request_key', side_effect=request_key):
            self.assertEqual(auth._exchange_code('c', 'v', Event()), 'sk-or-v1-unit-test-key')
        self.assertEqual(modes, [True, False])

        modes.clear()
        with patch.object(auth, '_system_proxy_configured', return_value=False), \
             patch.object(auth, '_request_key', side_effect=request_key), \
             self.assertRaises(auth.AuthError) as raised:
            auth._exchange_code('c', 'v', Event())
        self.assertEqual((modes, raised.exception.kind), ([True], 'network'))

    def test_exchange_classifies_failures_and_never_retries_a_delivered_code(self):
        auth = openrouter_auth
        cases = [
            (auth.requests.ConnectionError(), 'network', [True, False]),
            (auth.requests.ConnectTimeout(), 'network', [True, False]),
            (auth.requests.ReadTimeout(), 'slow', [True]),
            (auth.requests.exceptions.ChunkedEncodingError(), 'network', [True]),
        ]
        for failure, kind, attempts in cases:
            with self.subTest(failure=type(failure).__name__), \
                 patch.object(auth, '_system_proxy_configured', return_value=True), \
                 patch.object(auth.requests, 'Session') as session_type:
                trust = []
                session = session_type.return_value.__enter__.return_value

                def post(*args, **kwargs):
                    trust.append(session.trust_env)
                    raise failure

                session.post.side_effect = post
                with self.assertRaises(auth.AuthError) as raised:
                    auth._exchange_code('c', 'v', Event())
                self.assertEqual(raised.exception.kind, kind)
                self.assertEqual(trust, attempts)

    def test_unexpected_worker_error_is_reported_instead_of_hanging(self):
        auth = openrouter_auth
        cancelled, results = Event(), SimpleQueue()
        listener = auth._LoopbackCallback('Return to Avunote.')
        with patch.object(listener, 'wait_for_code', return_value='code'), \
             patch.object(auth, '_exchange_code', side_effect=KeyError('boom')):
            auth._authorize(listener, cancelled, results)
        self.assertEqual(results.get_nowait(), ('connecting', None))
        self.assertEqual(results.get_nowait(), ('failed', None))
        self.assertEqual(listener.socket.fileno(), -1)

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

    def run_dialog(self, until, limit_ms=6000):
        """Run the dialog; close it once until(dialog) is true and return its visible state."""
        auth = openrouter_auth
        app = QApplication.instance() or QApplication([])
        parent = QWidget()
        seen = {}

        def check():
            dialog = app.activeModalWidget()
            if isinstance(dialog, auth._ConnectDialog) and not seen and until(dialog):
                seen.update(status=dialog.status.text(), retry=dialog.retry.isVisible(),
                            progress=dialog.progress.isVisible(), copy_link=dialog.copy_link.isVisible(),
                            more=dialog.more, copy=dialog.copy)
                dialog.reject()

        def expire():
            dialog = app.activeModalWidget()
            if dialog:
                seen.setdefault('expired', True)
                dialog.reject()

        poll, guard = QTimer(), QTimer()
        poll.timeout.connect(check)
        guard.setSingleShot(True)
        guard.timeout.connect(expire)
        poll.start(30)
        guard.start(limit_ms)
        try:
            seen['result'] = auth.connect_openrouter(parent)
        finally:
            poll.stop()
            guard.stop()
            parent.close()
        return seen

    def redirecting_browser(self, code='test-code'):
        def open_browser(url):
            params = parse_qs(urlsplit(url.toString()).query)
            callback = urlsplit(params['callback_url'][0])

            def redirect():
                conn = HTTPConnection(callback.hostname, callback.port, timeout=2)
                try:
                    conn.request('GET', callback.path + '?' + urlencode({'state': params['state'][0], 'code': code}))
                    conn.getresponse().read()
                finally:
                    conn.close()

            Thread(target=redirect, daemon=True).start()
            return True
        return open_browser

    def test_dialog_shows_network_error_and_retry_instead_of_spinning(self):
        auth = openrouter_auth
        with patch.object(auth.QDesktopServices, 'openUrl', side_effect=self.redirecting_browser()), \
             patch.object(auth, '_exchange_code', side_effect=auth.AuthError('network', retryable=True)), \
             patch.object(auth, '_save_connection') as save:
            seen = self.run_dialog(lambda dialog: dialog.retry.isVisible())
        self.assertNotIn('expired', seen)
        self.assertEqual(seen['status'], seen['more'][0])
        self.assertFalse(seen['progress'])
        self.assertIsNone(seen['result'])
        save.assert_not_called()

    def test_dialog_reports_rejected_code_with_http_status(self):
        auth = openrouter_auth
        with patch.object(auth.QDesktopServices, 'openUrl', side_effect=self.redirecting_browser()), \
             patch.object(auth, '_exchange_code', side_effect=auth.AuthError('rejected', 403)):
            seen = self.run_dialog(lambda dialog: dialog.retry.isVisible())
        self.assertEqual(seen['status'], seen['more'][1].format(403))
        self.assertIn('403', seen['status'])

    def test_dialog_times_out_a_stalled_key_exchange(self):
        auth = openrouter_auth
        released = Event()

        def stalled(code, verifier, cancelled):
            cancelled.wait(10)
            released.set()
            return None

        with patch.object(auth, '_EXCHANGE_TIMEOUT', 0.3), \
             patch.object(auth.QDesktopServices, 'openUrl', side_effect=self.redirecting_browser()), \
             patch.object(auth, '_exchange_code', side_effect=stalled):
            seen = self.run_dialog(lambda dialog: dialog.retry.isVisible())
        self.assertNotIn('expired', seen)
        self.assertEqual(seen['status'], seen['more'][2])
        self.assertTrue(released.wait(2), 'the stalled worker was not cancelled')

    def test_dialog_notices_a_worker_that_died_silently(self):
        auth = openrouter_auth
        with patch.object(auth, '_authorize', side_effect=lambda listener, cancelled, results: listener.server_close()), \
             patch.object(auth.QDesktopServices, 'openUrl', return_value=True):
            seen = self.run_dialog(lambda dialog: dialog.retry.isVisible())
        self.assertNotIn('expired', seen)
        self.assertEqual(seen['status'], seen['copy'][6])

    def test_browser_failure_keeps_listening_and_offers_link_and_api_key(self):
        auth = openrouter_auth
        app = QApplication.instance() or QApplication([])
        key = 'sk-or-v1-pasted-unit-test-key'
        state = {}

        def paste_key(dialog):
            if not state:
                state.update(status=dialog.status.text(), copy_link=dialog.copy_link.isVisible(),
                             more=dialog.more)
                dialog.copy_link.click()
                state['clipboard'] = app.clipboard().text()
                dialog.manual_key.click()
            return False

        with patch.object(auth.QDesktopServices, 'openUrl', return_value=False), \
             patch.object(auth.QInputDialog, 'getText', return_value=(f'  {key}  ', True)), \
             patch.object(auth, '_save_connection', return_value='openrouter-free') as save:
            seen = self.run_dialog(paste_key)
        self.assertEqual(seen['result'], 'openrouter-free')
        save.assert_called_once_with(key)
        self.assertEqual(state['status'], state['more'][3])
        self.assertTrue(state['copy_link'])
        self.assertTrue(state['clipboard'].startswith('https://openrouter.ai/auth?'))

        with patch.object(auth.QDesktopServices, 'openUrl', return_value=True), \
             patch.object(auth.QInputDialog, 'getText', return_value=('sk-proj-not-openrouter-key', True)), \
             patch.object(auth, '_save_connection') as save:
            seen = self.run_dialog(lambda dialog: dialog.manual_key.click() or dialog.retry.isVisible())
        save.assert_not_called()
        self.assertEqual(seen['status'], seen['more'][8])

    def test_end_to_end_with_real_callback_and_fake_key_server(self):
        """Real loopback callback, real HTTP exchange against a local stand-in for OpenRouter."""
        auth = openrouter_auth
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import json

        issued = 'sk-or-v1-end-to-end-test-key'
        received = {}
        challenges = []

        class KeyServer(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.update(path=self.path, body=body)
                expected = urlsafe_b64encode(sha256(body['code_verifier'].encode()).digest()).rstrip(b'=').decode()
                ok = body.get('code') == 'e2e-code' and challenges and challenges[-1] == expected
                reply = json.dumps({'key': issued} if ok else {'error': 'bad'}).encode()
                self.send_response(200 if ok else 400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        provider = HTTPServer(('127.0.0.1', 0), KeyServer)
        Thread(target=provider.serve_forever, daemon=True).start()
        browser = self.redirecting_browser('e2e-code')

        def open_browser(url):
            challenges.append(parse_qs(urlsplit(url.toString()).query)['code_challenge'][0])
            return browser(url)

        try:
            with patch.dict(os.environ, {'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost'}), \
                 patch.object(auth, '_KEY_URL', f'http://127.0.0.1:{provider.server_port}/api/v1/auth/keys'), \
                 patch.object(auth.QDesktopServices, 'openUrl', side_effect=open_browser), \
                 patch.object(auth, '_save_connection', return_value='openrouter-free') as save:
                seen = self.run_dialog(lambda dialog: False)
        finally:
            provider.shutdown()
            provider.server_close()
        self.assertNotIn('expired', seen)
        self.assertEqual(seen['result'], 'openrouter-free')
        save.assert_called_once_with(issued)
        self.assertEqual(received['path'], '/api/v1/auth/keys')
        self.assertEqual(received['body']['code_challenge_method'], 'S256')


if __name__ == '__main__':
    unittest.main()
