import argparse
from pathlib import Path
import sys
import traceback

if getattr(sys, 'frozen', False):
    # Ship the MIT application source beside the runtime. It remains reviewable
    # and updateable independently from large third-party libraries.
    application_source = Path(sys.executable).parent / 'app'
    if application_source.is_dir():
        sys.path.insert(0, str(application_source))
    try:
        startup_log = (Path(sys.executable).parent / 'startup.log').open('a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = startup_log
        print('Starting Avunote')
    except OSError:
        pass

if not getattr(sys, 'frozen', False):
    qt = Path(__file__).resolve().parents[3] / 'work' / 'qt'
    if qt.exists():
        sys.path.insert(0, str(qt))

def _loaded_openssl():
    """Paths of the OpenSSL DLLs mapped into this process (Windows only)."""
    if sys.platform != 'win32':
        return []
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                         wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    modules = (wintypes.HMODULE * 2048)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModules(kernel32.GetCurrentProcess(), modules, ctypes.sizeof(modules),
                                    ctypes.byref(needed)):
        return []
    found = []
    name = ctypes.create_unicode_buffer(32768)
    for handle in modules[:min(needed.value // ctypes.sizeof(wintypes.HMODULE), len(modules))]:
        if handle and kernel32.GetModuleFileNameW(handle, name, len(name)):
            if Path(name.value).name.lower().startswith(('libssl', 'libcrypto')):
                found.append(name.value)
    return found


def _self_test(output, url):
    """Non-UI packaging check used by the build: HTTPS must work in the frozen runtime."""
    import json
    report = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'executable': sys.executable}
    try:
        import ssl
        import _hashlib  # noqa: F401  (OpenSSL-backed hashing shares the same DLLs)
        import certifi
        import requests
        import urllib3
        report.update(openssl=ssl.OPENSSL_VERSION, urllib3=urllib3.__version__, certifi=certifi.where())
        context = ssl.create_default_context(cafile=certifi.where())
        report['ca_certificates'] = context.cert_store_stats()['x509_ca']
        if not report['ca_certificates']:
            raise RuntimeError('certifi CA bundle is empty or missing')
        report['openssl_dlls'] = _loaded_openssl()
        bundle = getattr(sys, '_MEIPASS', None)
        if bundle:
            root = Path(bundle).resolve()
            foreign = [path for path in report['openssl_dlls'] if root not in Path(path).resolve().parents]
            if foreign or not report['openssl_dlls']:
                raise RuntimeError(f'OpenSSL is not loaded from the bundle: {report["openssl_dlls"]}')
        if url:
            with requests.get(url, timeout=(10, 20), stream=True) as response:
                report['https'] = {'url': url, 'status': response.status_code}
        report['ok'] = True
    except BaseException as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        report['traceback'] = traceback.format_exc()
    text = json.dumps(report, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding='utf-8')
    print(text)
    return 0 if report['ok'] else 1


def _guard_https():
    """Replace urllib3's bare 'SSL module is not available' with an actionable message."""
    try:
        import ssl  # noqa: F401
        return
    except ImportError as exc:
        reason = str(exc)
    message = ('Secure (HTTPS) connections are unavailable because this Avunote installation cannot '
               f'load its OpenSSL runtime ({reason}). Model downloads, sign-in and update checks will '
               'fail until Avunote is repaired or reinstalled from the latest Setup.')
    print(message)
    try:
        from urllib3 import connectionpool

        def unavailable(self):
            raise ImportError(message)
        connectionpool.HTTPSConnectionPool._new_conn = unavailable
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--self-test-url')
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--model', default='whisper-base-full')
    parser.add_argument('--beams', type=int, default=5)
    parser.add_argument('--language', default='azb')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda', 'npu'], default='auto')
    parser.add_argument('--chunk-seconds', type=int, choices=[10, 15, 20, 25, 30], default=20)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--page', choices=['studio', 'library', 'history', 'ai', 'settings'], default='studio')
    parser.add_argument('audio', nargs='?')
    args = parser.parse_args()
    if args.self_test:
        sys.exit(_self_test(args.output, args.self_test_url))
    _guard_https()
    if args.worker:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        log = args.output.with_suffix('.log').open('w', encoding='utf-8')
        sys.stdout = sys.stderr = log
        from studio_engine import transcribe
        sys.exit(transcribe(args.worker, args.output, args.model, args.beams, args.language,
                            device=args.device, chunk_seconds=args.chunk_seconds))
    try:
        print('Loading desktop interface')
        from studio_ui import launch
        print('Desktop interface loaded')
        launch(args.audio, args.preview, args.page)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
