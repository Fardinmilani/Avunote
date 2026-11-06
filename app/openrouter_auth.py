"""Browser sign-in for the free OpenRouter connection."""

from base64 import urlsafe_b64encode
from hashlib import sha256
from hmac import compare_digest
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from queue import Empty, SimpleQueue
from secrets import token_urlsafe
from socket import SHUT_RDWR
from threading import Event, Thread, Timer
from time import monotonic
from urllib.parse import parse_qs, urlencode, urlsplit

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QProgressBar, QVBoxLayout
import requests

from ai_clients import AIError, OPENROUTER_BASE_URL, OPENROUTER_FREE_MODEL
from ai_profiles import save_profile
from ui_i18n import RTL_LANGUAGES, current_language

_AUTH_URL = 'https://openrouter.ai/auth'
_KEY_URL = OPENROUTER_BASE_URL + '/auth/keys'
_PROFILE_ID = 'openrouter-free'
_MAX_REPLY = 32_768

# Title, description, waiting, connecting, retry, cancel, error, timeout, browser confirmation.
_COPY = {
    'en': (
        'Connect to OpenRouter', 'Sign in through your browser to use free models. Provider limits apply.',
        'Waiting for browser sign-in…', 'Connecting your account…', 'Try again', 'Cancel',
        'Could not complete sign-in. Check your connection and try again.',
        'Sign-in timed out. Start again when ready.', 'Authorization received. Return to Avunote.',
    ),
    'fa': (
        'اتصال به OpenRouter', 'برای استفاده از مدل‌های رایگان، در مرورگر وارد شوید. سرویس محدودیت درخواست دارد.',
        'در انتظار ورود در مرورگر…', 'در حال اتصال حساب…', 'تلاش دوباره', 'لغو',
        'ورود کامل نشد. اتصال اینترنت را بررسی کنید و دوباره تلاش کنید.',
        'زمان ورود تمام شد. هر وقت آماده بودید دوباره شروع کنید.', 'مجوز دریافت شد. به آوونوت برگردید.',
    ),
    'tr': (
        'OpenRouter’a bağlan', 'Ücretsiz modeller için tarayıcıda oturum açın. Sağlayıcı sınırları geçerlidir.',
        'Tarayıcıda oturum açmanız bekleniyor…', 'Hesabınız bağlanıyor…', 'Tekrar dene', 'İptal',
        'Oturum açılamadı. Bağlantınızı kontrol edip tekrar deneyin.',
        'Oturum açma süresi doldu. Hazır olduğunuzda yeniden başlayın.', 'Yetkilendirme alındı. Avunote’a dönün.',
    ),
    'ar': (
        'الاتصال بـ OpenRouter', 'سجّل الدخول من المتصفح لاستخدام النماذج المجانية. تسري حدود استخدام الخدمة.',
        'في انتظار تسجيل الدخول من المتصفح…', 'جارٍ ربط حسابك…', 'إعادة المحاولة', 'إلغاء',
        'تعذّر إكمال تسجيل الدخول. تحقّق من اتصالك وحاول مجددًا.',
        'انتهت مهلة تسجيل الدخول. ابدأ مجددًا عندما تكون جاهزًا.', 'تم استلام التفويض. عُد إلى Avunote.',
    ),
    'az': (
        'OpenRouter-a qoşul', 'Pulsuz modellər üçün brauzerdə daxil olun. Xidmətin istifadə limitləri tətbiq olunur.',
        'Brauzerdə giriş gözlənilir…', 'Hesabınız qoşulur…', 'Yenidən cəhd et', 'Ləğv et',
        'Giriş tamamlanmadı. Bağlantınızı yoxlayıb yenidən cəhd edin.',
        'Giriş vaxtı bitdi. Hazır olanda yenidən başlayın.', 'İcazə alındı. Avunote-a qayıdın.',
    ),
    'es': (
        'Conectar con OpenRouter', 'Inicia sesión en tu navegador para usar modelos gratuitos. Se aplican los límites del servicio.',
        'Esperando el inicio de sesión en el navegador…', 'Conectando tu cuenta…', 'Reintentar', 'Cancelar',
        'No se pudo iniciar sesión. Comprueba tu conexión e inténtalo de nuevo.',
        'Se agotó el tiempo para iniciar sesión. Vuelve a intentarlo cuando quieras.', 'Autorización recibida. Vuelve a Avunote.',
    ),
    'fr': (
        'Connexion à OpenRouter', 'Connectez-vous dans votre navigateur pour utiliser les modèles gratuits. Les limites du service s’appliquent.',
        'En attente de connexion dans le navigateur…', 'Connexion de votre compte…', 'Réessayer', 'Annuler',
        'La connexion a échoué. Vérifiez votre connexion Internet et réessayez.',
        'Le délai de connexion a expiré. Réessayez quand vous êtes prêt.', 'Autorisation reçue. Revenez dans Avunote.',
    ),
    'de': (
        'Mit OpenRouter verbinden', 'Melden Sie sich im Browser an, um kostenlose Modelle zu verwenden. Es gelten die Nutzungslimits des Anbieters.',
        'Warten auf die Anmeldung im Browser…', 'Konto wird verbunden…', 'Erneut versuchen', 'Abbrechen',
        'Die Anmeldung ist fehlgeschlagen. Prüfen Sie Ihre Verbindung und versuchen Sie es erneut.',
        'Die Anmeldezeit ist abgelaufen. Starten Sie die Anmeldung erneut.', 'Autorisierung erhalten. Kehren Sie zu Avunote zurück.',
    ),
    'pt': (
        'Conectar ao OpenRouter', 'Entre pelo navegador para usar os modelos gratuitos. O serviço tem limites de uso.',
        'Aguardando o login no navegador…', 'Conectando sua conta…', 'Tentar novamente', 'Cancelar',
        'Não foi possível entrar. Confira sua conexão e tente novamente.',
        'O tempo para fazer login acabou. Tente novamente quando quiser.', 'Autorização recebida. Volte ao Avunote.',
    ),
    'ru': (
        'Подключение к OpenRouter', 'Войдите через браузер, чтобы пользоваться бесплатными моделями. Действуют ограничения сервиса.',
        'Ожидание входа в браузере…', 'Подключение аккаунта…', 'Повторить', 'Отмена',
        'Не удалось войти. Проверьте подключение к интернету и попробуйте снова.',
        'Время ожидания входа истекло. Запустите вход ещё раз.', 'Авторизация получена. Вернитесь в Avunote.',
    ),
    'zh': (
        '连接 OpenRouter', '在浏览器中登录即可使用免费模型。使用量受服务限制。',
        '正在等待浏览器登录…', '正在连接账户…', '重试', '取消',
        '登录未完成。请检查网络连接后重试。',
        '登录超时，请重试。', '已收到授权，请返回 Avunote。',
    ),
    'ja': (
        'OpenRouter に接続', '無料モデルを使うには、ブラウザーでログインしてください。サービスの利用制限が適用されます。',
        'ブラウザーでのログインを待っています…', 'アカウントに接続しています…', '再試行', 'キャンセル',
        'ログインできませんでした。ネットワーク接続を確認して、もう一度お試しください。',
        'ログインがタイムアウトしました。準備ができたら再試行してください。', '認証を受け付けました。Avunote に戻ってください。',
    ),
}


class AuthError(Exception):
    """An authorization failure safe to show without provider details."""


def _bounded_token(value):
    return isinstance(value, str) and 0 < len(value) <= 4096 and all(33 <= ord(char) <= 126 for char in value)


class _CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # The callback request line contains a single-use credential.
        pass

    def _send(self, status, text):
        body = ('<!doctype html><meta charset="utf-8"><title>Avunote</title>'
                f'<h1>Avunote</h1><p>{escape(text)}</p>').encode('utf-8')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass

    def do_GET(self):
        server = self.server
        if self.headers.get_all('Host') != [f'127.0.0.1:{server.server_port}'] or len(self.path) > 8192:
            self._send(400, 'Invalid authorization callback.')
            return
        try:
            target = urlsplit(self.path)
            params = parse_qs(target.query, keep_blank_values=True, max_num_fields=8)
        except ValueError:
            self._send(400, 'Invalid authorization callback.')
            return
        if target.scheme or target.netloc or target.path != server.callback_path:
            self._send(404, 'Authorization callback not found.')
            return
        states = params.get('state', [])
        codes = params.get('code', [])
        if (server.code is not None or len(states) != 1 or not states[0].isascii()
                or not compare_digest(states[0], server.state)
                or len(codes) != 1 or not _bounded_token(codes[0])):
            self._send(400, 'Invalid authorization callback.')
            return
        server.code = codes[0]
        self._send(200, server.browser_message)


class _LoopbackCallback(HTTPServer):
    allow_reuse_address = False
    allow_reuse_port = False
    timeout = 0.2

    def __init__(self, browser_message):
        self.state = token_urlsafe(32)
        self.callback_path = '/avunote/' + token_urlsafe(24)
        self.verifier = token_urlsafe(48)
        self.browser_message = browser_message
        self.code = None
        super().__init__(('127.0.0.1', 0), _CallbackHandler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(1)
        return connection, address

    def process_request(self, request, client_address):
        # Bound total request time even if a local process dribbles HTTP headers.
        def stop_request():
            try:
                request.shutdown(SHUT_RDWR)
            except OSError:
                pass

        timer = Timer(2, stop_request)
        timer.daemon = True
        timer.start()
        try:
            super().process_request(request, client_address)
        finally:
            timer.cancel()

    def handle_error(self, request, client_address):
        # Do not print browser requests or authorization exceptions.
        pass

    def authorization_url(self):
        digest = sha256(self.verifier.encode('ascii')).digest()
        challenge = urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
        return _AUTH_URL + '?' + urlencode({
            'callback_url': f'http://127.0.0.1:{self.server_port}{self.callback_path}',
            'code_challenge': challenge, 'code_challenge_method': 'S256',
            'state': self.state, 'key_label': 'Avunote',
        })

    def wait_for_code(self, cancelled, timeout=180):
        deadline = monotonic() + timeout
        while not cancelled.is_set() and monotonic() < deadline:
            self.handle_request()
            if self.code is not None and not cancelled.is_set():
                code, self.code = self.code, None
                return code
        if cancelled.is_set():
            return None
        raise TimeoutError


def _exchange_code(code, verifier, cancelled):
    if cancelled.is_set():
        return None
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.post(
                _KEY_URL, json={'code': code, 'code_verifier': verifier, 'code_challenge_method': 'S256'},
                headers={'Accept': 'application/json'}, timeout=(8, 12),
                allow_redirects=False, stream=True,
            ) as response:
                if response.status_code != 200:
                    raise AuthError
                raw = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if cancelled.is_set():
                        return None
                    raw.extend(chunk)
                    if len(raw) > _MAX_REPLY:
                        raise AuthError
        data = json.loads(raw)
        key = data.get('key') if isinstance(data, dict) else None
    except (requests.RequestException, ValueError, RecursionError):
        raise AuthError from None
    if not _bounded_token(key) or len(key) < 16:
        raise AuthError
    return key


def _authorize(listener, cancelled, results):
    try:
        with listener:
            code = listener.wait_for_code(cancelled)
        if code is not None and not cancelled.is_set():
            results.put(('connecting', None))
            key = _exchange_code(code, listener.verifier, cancelled)
            if key is not None and not cancelled.is_set():
                results.put(('connected', key))
    except TimeoutError:
        results.put(('timeout', None))
    except (AuthError, OSError):
        results.put(('failed', None))


def _save_connection(key):
    return save_profile({
        'id': _PROFILE_ID, 'name': 'OpenRouter Free', 'provider': 'openrouter',
        'base_url': OPENROUTER_BASE_URL, 'model': OPENROUTER_FREE_MODEL, 'key': key,
        'store_key': True,
    })


class _ConnectDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        locale = current_language()
        self.copy = _COPY.get(locale, _COPY['en'])
        if locale in RTL_LANGUAGES:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle(self.copy[0])
        self.setMinimumWidth(360)
        self.profile_id = None
        self.cancelled = Event()
        self.results = SimpleQueue()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(12)
        description = QLabel(self.copy[1])
        description.setWordWrap(True)
        layout.addWidget(description)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        actions.button(QDialogButtonBox.StandardButton.Cancel).setText(self.copy[5])
        actions.rejected.connect(self.reject)
        self.retry = actions.addButton(self.copy[4], QDialogButtonBox.ButtonRole.ActionRole)
        self.retry.clicked.connect(self.start)
        self.retry.hide()
        layout.addWidget(actions)
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.consume_result)
        QTimer.singleShot(0, self, self.start)

    def start(self):
        if not self.isVisible():
            return
        self.retry.hide()
        self.progress.show()
        self.status.setText(self.copy[2])
        self.cancelled = Event()
        self.results = SimpleQueue()
        try:
            listener = _LoopbackCallback(self.copy[8])
        except OSError:
            self.show_failure(self.copy[6])
            return
        if not QDesktopServices.openUrl(QUrl(listener.authorization_url())):
            listener.server_close()
            self.show_failure(self.copy[6])
            return
        try:
            Thread(target=_authorize, args=(listener, self.cancelled, self.results),
                   name='openrouter-sign-in', daemon=True).start()
        except RuntimeError:
            listener.server_close()
            self.show_failure(self.copy[6])
            return
        self.poll.start(80)

    def consume_result(self):
        try:
            result, key = self.results.get_nowait()
        except Empty:
            return
        if result == 'connecting':
            self.status.setText(self.copy[3])
        elif result == 'connected':
            try:
                self.profile_id = _save_connection(key)
            except (AIError, OSError):
                self.show_failure(self.copy[6])
            else:
                self.accept()
        else:
            self.show_failure(self.copy[7 if result == 'timeout' else 6])

    def show_failure(self, message):
        self.poll.stop()
        self.status.setText(message)
        self.progress.hide()
        self.retry.show()

    def done(self, result):
        self.cancelled.set()
        self.poll.stop()
        super().done(result)


def connect_openrouter(parent):
    """Open browser sign-in and return the stored profile ID after approval."""
    dialog = _ConnectDialog(parent)
    try:
        return dialog.profile_id if dialog.exec() == QDialog.DialogCode.Accepted else None
    finally:
        dialog.deleteLater()
