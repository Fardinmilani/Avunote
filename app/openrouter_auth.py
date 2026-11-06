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
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QInputDialog, QLabel, QLineEdit, QProgressBar,
                               QVBoxLayout)
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


# Unreachable, rejected (HTTP {}), slow reply, browser did not open, copy link, link copied,
# use API key, API key prompt, invalid API key.
_MORE = {
    'en': (
        'Could not reach OpenRouter. Check your internet connection, VPN or proxy, then try again.',
        'OpenRouter did not accept the sign-in (HTTP {}). Try again and approve the request in your browser.',
        'OpenRouter did not respond in time. Check your internet connection, VPN or proxy, then try again.',
        'Could not open your browser. Copy the sign-in link and open it in your browser.',
        'Copy sign-in link', 'Sign-in link copied. Paste it into your browser’s address bar.',
        'Use an API key…', 'Paste your OpenRouter API key (it starts with sk-or-):',
        'That is not an OpenRouter API key. It should start with sk-or-.',
    ),
    'fa': (
        'دسترسی به OpenRouter ممکن نشد. اتصال اینترنت، VPN یا پراکسی را بررسی کنید و دوباره تلاش کنید.',
        'OpenRouter ورود را نپذیرفت (HTTP {}). دوباره تلاش کنید و درخواست را در مرورگر تأیید کنید.',
        'OpenRouter به‌موقع پاسخ نداد. اتصال اینترنت، VPN یا پراکسی را بررسی کنید و دوباره تلاش کنید.',
        'مرورگر باز نشد. پیوند ورود را کپی کنید و در مرورگر باز کنید.',
        'کپی پیوند ورود', 'پیوند ورود کپی شد. آن را در نوار نشانی مرورگر بچسبانید.',
        'استفاده از کلید API…', 'کلید API سرویس OpenRouter را بچسبانید (با sk-or- شروع می‌شود):',
        'این کلید API سرویس OpenRouter نیست. باید با sk-or- شروع شود.',
    ),
    'tr': (
        'OpenRouter’a ulaşılamadı. İnternet bağlantınızı, VPN’inizi veya proxy ayarınızı kontrol edip tekrar deneyin.',
        'OpenRouter oturum açmayı kabul etmedi (HTTP {}). Tekrar deneyin ve isteği tarayıcıda onaylayın.',
        'OpenRouter zamanında yanıt vermedi. İnternet bağlantınızı, VPN’inizi veya proxy ayarınızı kontrol edip tekrar deneyin.',
        'Tarayıcı açılamadı. Oturum açma bağlantısını kopyalayıp tarayıcınızda açın.',
        'Bağlantıyı kopyala', 'Bağlantı kopyalandı. Tarayıcınızın adres çubuğuna yapıştırın.',
        'API anahtarı kullan…', 'OpenRouter API anahtarınızı yapıştırın (sk-or- ile başlar):',
        'Bu bir OpenRouter API anahtarı değil. sk-or- ile başlamalıdır.',
    ),
    'ar': (
        'تعذّر الوصول إلى OpenRouter. تحقّق من اتصال الإنترنت أو VPN أو الوكيل، ثم حاول مجددًا.',
        'لم يقبل OpenRouter تسجيل الدخول (HTTP {}). حاول مجددًا ووافق على الطلب في المتصفح.',
        'لم يستجب OpenRouter في الوقت المحدد. تحقّق من اتصال الإنترنت أو VPN أو الوكيل، ثم حاول مجددًا.',
        'تعذّر فتح المتصفح. انسخ رابط تسجيل الدخول وافتحه في المتصفح.',
        'نسخ رابط تسجيل الدخول', 'تم نسخ الرابط. الصقه في شريط العنوان في المتصفح.',
        'استخدام مفتاح API…', 'الصق مفتاح OpenRouter API (يبدأ بـ sk-or-):',
        'هذا ليس مفتاح OpenRouter API. يجب أن يبدأ بـ sk-or-.',
    ),
    'az': (
        'OpenRouter-a qoşulmaq mümkün olmadı. İnternet bağlantısını, VPN və ya proksini yoxlayıb yenidən cəhd edin.',
        'OpenRouter girişi qəbul etmədi (HTTP {}). Yenidən cəhd edin və sorğunu brauzerdə təsdiqləyin.',
        'OpenRouter vaxtında cavab vermədi. İnternet bağlantısını, VPN və ya proksini yoxlayıb yenidən cəhd edin.',
        'Brauzer açılmadı. Giriş keçidini kopyalayıb brauzerdə açın.',
        'Giriş keçidini kopyala', 'Keçid kopyalandı. Onu brauzerin ünvan sətrinə yapışdırın.',
        'API açarı istifadə et…', 'OpenRouter API açarınızı yapışdırın (sk-or- ilə başlayır):',
        'Bu OpenRouter API açarı deyil. sk-or- ilə başlamalıdır.',
    ),
    'es': (
        'No se pudo conectar con OpenRouter. Comprueba tu conexión a Internet, VPN o proxy e inténtalo de nuevo.',
        'OpenRouter no aceptó el inicio de sesión (HTTP {}). Inténtalo de nuevo y aprueba la solicitud en el navegador.',
        'OpenRouter no respondió a tiempo. Comprueba tu conexión a Internet, VPN o proxy e inténtalo de nuevo.',
        'No se pudo abrir el navegador. Copia el enlace de inicio de sesión y ábrelo en tu navegador.',
        'Copiar enlace', 'Enlace copiado. Pégalo en la barra de direcciones del navegador.',
        'Usar una clave de API…', 'Pega tu clave de API de OpenRouter (empieza por sk-or-):',
        'No es una clave de API de OpenRouter. Debe empezar por sk-or-.',
    ),
    'fr': (
        'Impossible de joindre OpenRouter. Vérifiez votre connexion Internet, votre VPN ou votre proxy, puis réessayez.',
        'OpenRouter a refusé la connexion (HTTP {}). Réessayez et approuvez la demande dans votre navigateur.',
        'OpenRouter n’a pas répondu à temps. Vérifiez votre connexion Internet, votre VPN ou votre proxy, puis réessayez.',
        'Impossible d’ouvrir le navigateur. Copiez le lien de connexion et ouvrez-le dans votre navigateur.',
        'Copier le lien', 'Lien copié. Collez-le dans la barre d’adresse de votre navigateur.',
        'Utiliser une clé API…', 'Collez votre clé API OpenRouter (elle commence par sk-or-) :',
        'Ce n’est pas une clé API OpenRouter. Elle doit commencer par sk-or-.',
    ),
    'de': (
        'OpenRouter ist nicht erreichbar. Prüfen Sie Ihre Internetverbindung, Ihr VPN oder Ihren Proxy und versuchen Sie es erneut.',
        'OpenRouter hat die Anmeldung nicht akzeptiert (HTTP {}). Versuchen Sie es erneut und bestätigen Sie die Anfrage im Browser.',
        'OpenRouter hat nicht rechtzeitig geantwortet. Prüfen Sie Ihre Internetverbindung, Ihr VPN oder Ihren Proxy und versuchen Sie es erneut.',
        'Der Browser konnte nicht geöffnet werden. Kopieren Sie den Anmeldelink und öffnen Sie ihn im Browser.',
        'Link kopieren', 'Link kopiert. Fügen Sie ihn in die Adressleiste Ihres Browsers ein.',
        'API-Schlüssel verwenden…', 'Fügen Sie Ihren OpenRouter-API-Schlüssel ein (beginnt mit sk-or-):',
        'Das ist kein OpenRouter-API-Schlüssel. Er muss mit sk-or- beginnen.',
    ),
    'pt': (
        'Não foi possível acessar o OpenRouter. Confira sua conexão com a internet, VPN ou proxy e tente novamente.',
        'O OpenRouter não aceitou o login (HTTP {}). Tente novamente e aprove a solicitação no navegador.',
        'O OpenRouter não respondeu a tempo. Confira sua conexão com a internet, VPN ou proxy e tente novamente.',
        'Não foi possível abrir o navegador. Copie o link de login e abra-o no navegador.',
        'Copiar link', 'Link copiado. Cole-o na barra de endereços do navegador.',
        'Usar uma chave de API…', 'Cole sua chave de API do OpenRouter (começa com sk-or-):',
        'Esta não é uma chave de API do OpenRouter. Ela deve começar com sk-or-.',
    ),
    'ru': (
        'Не удалось подключиться к OpenRouter. Проверьте подключение к интернету, VPN или прокси и попробуйте снова.',
        'OpenRouter не принял вход (HTTP {}). Попробуйте снова и подтвердите запрос в браузере.',
        'OpenRouter не ответил вовремя. Проверьте подключение к интернету, VPN или прокси и попробуйте снова.',
        'Не удалось открыть браузер. Скопируйте ссылку для входа и откройте её в браузере.',
        'Копировать ссылку', 'Ссылка скопирована. Вставьте её в адресную строку браузера.',
        'Использовать API-ключ…', 'Вставьте API-ключ OpenRouter (начинается с sk-or-):',
        'Это не API-ключ OpenRouter. Он должен начинаться с sk-or-.',
    ),
    'zh': (
        '无法连接 OpenRouter。请检查网络连接、VPN 或代理后重试。',
        'OpenRouter 未接受此次登录（HTTP {}）。请重试，并在浏览器中批准请求。',
        'OpenRouter 未及时响应。请检查网络连接、VPN 或代理后重试。',
        '无法打开浏览器。请复制登录链接并在浏览器中打开。',
        '复制登录链接', '链接已复制。请粘贴到浏览器地址栏。',
        '使用 API 密钥…', '粘贴你的 OpenRouter API 密钥（以 sk-or- 开头）：',
        '这不是 OpenRouter API 密钥，应以 sk-or- 开头。',
    ),
    'ja': (
        'OpenRouter に接続できません。インターネット接続、VPN、またはプロキシを確認して、もう一度お試しください。',
        'OpenRouter がログインを受け付けませんでした（HTTP {}）。もう一度お試しのうえ、ブラウザーで要求を承認してください。',
        'OpenRouter から時間内に応答がありませんでした。インターネット接続、VPN、またはプロキシを確認して、もう一度お試しください。',
        'ブラウザーを開けませんでした。ログインリンクをコピーしてブラウザーで開いてください。',
        'ログインリンクをコピー', 'リンクをコピーしました。ブラウザーのアドレスバーに貼り付けてください。',
        'API キーを使う…', 'OpenRouter の API キーを貼り付けてください（sk-or- で始まります）：',
        'OpenRouter の API キーではありません。sk-or- で始まる必要があります。',
    ),
}

_SIGN_IN_TIMEOUT = 180
_EXCHANGE_TIMEOUT = 45


class AuthError(Exception):
    """An authorization failure safe to show without provider details.

    kind is 'network', 'slow', 'rejected' or 'invalid'; retryable marks failures
    where the single-use code was most likely never delivered.
    """

    def __init__(self, kind='invalid', status=None, retryable=False):
        super().__init__(kind)
        self.kind = kind
        self.status = status
        self.retryable = retryable


def _bounded_token(value):
    return isinstance(value, str) and 0 < len(value) <= 4096 and all(33 <= ord(char) <= 126 for char in value)


class _CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # The callback request line contains a single-use credential.
        pass

    def _send(self, status, text):
        body = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                '<title>Avunote</title><style>body{font:16px/1.5 "Segoe UI",system-ui,sans-serif;'
                'background:#f6f6f4;color:#1c1c1c;display:grid;place-items:center;min-height:90vh;margin:0}'
                'main{background:#fff;border:1px solid #e2e2de;border-radius:12px;padding:28px 36px;'
                'max-width:420px;text-align:center}h1{font-size:20px;margin:0 0 8px}p{margin:0}</style>'
                f'<main><h1>Avunote</h1><p dir="auto">{escape(text)}</p></main>').encode('utf-8')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")
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

    def wait_for_code(self, cancelled, timeout=_SIGN_IN_TIMEOUT):
        deadline = monotonic() + timeout
        while not cancelled.is_set() and monotonic() < deadline:
            self.handle_request()
            if self.code is not None and not cancelled.is_set():
                code, self.code = self.code, None
                return code
        if cancelled.is_set():
            return None
        raise TimeoutError


def _system_proxy_configured():
    try:
        return bool(requests.utils.get_environ_proxies(_KEY_URL))
    except Exception:
        return False


def _request_key(code, verifier, cancelled, use_system_proxy):
    try:
        with requests.Session() as session:
            # Same proxy policy as remote chat requests: the browser that approved
            # the sign-in usually reaches OpenRouter through the system proxy/VPN.
            session.trust_env = use_system_proxy
            with session.post(
                _KEY_URL, json={'code': code, 'code_verifier': verifier, 'code_challenge_method': 'S256'},
                headers={'Accept': 'application/json'}, timeout=(8, 15),
                allow_redirects=False, stream=True,
            ) as response:
                if response.status_code != 200:
                    raise AuthError('rejected', response.status_code)
                raw = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if cancelled.is_set():
                        return None
                    raw.extend(chunk)
                    if len(raw) > _MAX_REPLY:
                        raise AuthError
        data = json.loads(raw)
        key = data.get('key') if isinstance(data, dict) else None
    except requests.ConnectionError:
        raise AuthError('network', retryable=True) from None
    except requests.Timeout:
        raise AuthError('slow') from None
    except requests.RequestException:
        raise AuthError('network') from None
    except (ValueError, RecursionError):
        raise AuthError from None
    if not _bounded_token(key) or len(key) < 16:
        raise AuthError
    return key


def _exchange_code(code, verifier, cancelled):
    if cancelled.is_set():
        return None
    # A dead or misconfigured system proxy should not block sign-in when OpenRouter
    # is reachable directly, so connection failures through the proxy retry once.
    modes = (True, False) if _system_proxy_configured() else (True,)
    for index, use_system_proxy in enumerate(modes):
        try:
            return _request_key(code, verifier, cancelled, use_system_proxy)
        except AuthError as error:
            if not error.retryable or index == len(modes) - 1 or cancelled.is_set():
                raise
    return None


def _authorize(listener, cancelled, results):
    # Every exit path reports to the dialog so it can never wait on a silent thread.
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
    except AuthError as error:
        results.put(('failed', error))
    except Exception:
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
        self.more = _MORE.get(locale, _MORE['en'])
        if locale in RTL_LANGUAGES:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle(self.copy[0])
        self.setMinimumWidth(360)
        self.profile_id = None
        self.cancelled = Event()
        self.results = SimpleQueue()
        self.worker = None
        self.auth_url = ''
        self.deadline = 0.0
        self.exchanging = False
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
        self.copy_link = actions.addButton(self.more[4], QDialogButtonBox.ButtonRole.ActionRole)
        self.copy_link.clicked.connect(self.copy_sign_in_link)
        self.copy_link.hide()
        self.manual_key = actions.addButton(self.more[6], QDialogButtonBox.ButtonRole.ActionRole)
        self.manual_key.clicked.connect(self.use_api_key)
        layout.addWidget(actions)
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.consume_result)
        QTimer.singleShot(0, self, self.start)

    def start(self):
        if not self.isVisible():
            return
        self.cancelled.set()
        self.retry.hide()
        self.copy_link.hide()
        self.progress.show()
        self.status.setText(self.copy[2])
        self.cancelled = Event()
        self.results = SimpleQueue()
        self.exchanging = False
        try:
            listener = _LoopbackCallback(self.copy[8])
        except OSError:
            self.show_failure(self.copy[6])
            return
        self.auth_url = listener.authorization_url()
        try:
            self.worker = Thread(target=_authorize, args=(listener, self.cancelled, self.results),
                                 name='openrouter-sign-in', daemon=True)
            self.worker.start()
        except RuntimeError:
            listener.server_close()
            self.show_failure(self.copy[6])
            return
        self.deadline = monotonic() + _SIGN_IN_TIMEOUT + 10
        self.poll.start(80)
        self.copy_link.show()
        # The callback server is already listening, so a manually opened link still works.
        if not QDesktopServices.openUrl(QUrl(self.auth_url)):
            self.status.setText(self.more[3])

    def copy_sign_in_link(self):
        if self.auth_url and self.poll.isActive():
            QGuiApplication.clipboard().setText(self.auth_url)
            self.status.setText(self.more[5])

    def use_api_key(self):
        key, accepted = QInputDialog.getText(self, self.copy[0], self.more[7], QLineEdit.EchoMode.Password)
        if not accepted:
            return
        key = key.strip()
        if not (key.startswith('sk-or-') and _bounded_token(key) and len(key) >= 16):
            self.cancelled.set()
            self.show_failure(self.more[8])
            return
        self.cancelled.set()
        self.save_and_finish(key)

    def save_and_finish(self, key):
        try:
            self.profile_id = _save_connection(key)
        except AIError as error:
            self.show_failure(str(error) or self.copy[6])
        except Exception:
            self.show_failure(self.copy[6])
        else:
            self.accept()

    def failure_message(self, error):
        if isinstance(error, AuthError):
            if error.kind == 'network':
                return self.more[0]
            if error.kind == 'slow':
                return self.more[2]
            if error.kind == 'rejected':
                return self.more[1].format(error.status)
        return self.copy[6]

    def handle_result(self, result, value):
        if result == 'connecting':
            self.status.setText(self.copy[3])
            self.copy_link.hide()
            self.exchanging = True
            self.deadline = monotonic() + _EXCHANGE_TIMEOUT
        elif result == 'connected':
            self.poll.stop()
            self.save_and_finish(value)
        elif result == 'timeout':
            self.show_failure(self.copy[7])
        else:
            self.show_failure(self.failure_message(value))

    def consume_result(self):
        # Read liveness first: a worker that exits after queueing its last result
        # must not be mistaken for one that died without reporting.
        worker_done = self.worker is None or not self.worker.is_alive()
        while self.poll.isActive():
            try:
                result, value = self.results.get_nowait()
            except Empty:
                break
            self.handle_result(result, value)
        if not self.poll.isActive():
            return
        if worker_done:
            self.show_failure(self.copy[6])
        elif monotonic() > self.deadline:
            self.cancelled.set()
            self.show_failure(self.more[2] if self.exchanging else self.copy[7])

    def show_failure(self, message):
        self.poll.stop()
        self.status.setText(message)
        self.progress.hide()
        self.copy_link.hide()
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
