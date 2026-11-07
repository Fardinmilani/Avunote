"""Model-free Windows distribution. Build from project root with PyInstaller."""
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
    StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)

project = Path(SPECPATH)
vendor = project/'vendor/ffmpeg.exe'
if not vendor.is_file():
    raise SystemExit('Build the audio-only LGPL FFmpeg described in vendor/README.md first.')
hidden = ['torch', 'numpy', 'psutil', 'sounddevice', 'requests', 'ssl', '_ssl', '_hashlib', 'certifi', 'urllib3',
          'ctranslate2', 'tokenizers',
          'sherpa_onnx', 'sherpa_onnx.lib._sherpa_onnx',
          'wave', 'array', 'uuid', 'tempfile', 'threading', 'traceback',
          'http.server', 'socketserver', 'secrets', 'configparser', 'winreg',
          'ctypes', 'ctypes.wintypes', 'msvcrt', 'base64', 'ipaddress', 'email.utils',
          'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtCore',
          'transformers', 'transformers.models.whisper.processing_whisper',
          'transformers.models.whisper.modeling_whisper',
          'transformers.models.whisper.feature_extraction_whisper',
          'transformers.models.whisper.tokenization_whisper',
          'transformers.models.whisper.tokenization_whisper_fast',
          'transformers.models.auto.processing_auto', 'transformers.generation.utils']
datas = [(str(vendor), 'vendor'), (str(project/'assets/avunote-mark.png'), 'assets'),
         (str(project/'assets/avunote-logo-transparent.png'), 'assets'),
         (str(project/'VERSION'), '.')]
datas += [(str(path), 'assets/fonts') for path in sorted((project/'assets/fonts').glob('*'))]
datas += collect_data_files('_sounddevice_data')
datas += collect_data_files('certifi')
for package in ['transformers', 'tokenizers', 'huggingface_hub', 'ctranslate2', 'sherpa-onnx', 'sherpa-onnx-core', 'requests']:
    datas += copy_metadata(package)
qtpath = __import__('os').environ.get('AZB_QT_PATH')
paths = [str(project/'app')] + ([qtpath] if qtpath else [])
a = Analysis([str(project/'app/entrypoint.py')], pathex=paths,
             binaries=(collect_dynamic_libs('_sounddevice_data') + collect_dynamic_libs('ctranslate2')
                       + collect_dynamic_libs('sherpa_onnx')),
             datas=datas, hiddenimports=hidden,
             excludes=['studio_ui', 'studio_engine', 'model_catalog', 'model_downloads', 'ui_i18n', 'ui_locales', 'atomic_files',
                       'ai_panel', 'ai_clients', 'ai_profiles', 'compute_devices', 'studio_theme', 'ui_v3_strings',
                       'app_updates', 'update_panel', 'openrouter_auth', 'model_picker',
                       'tkinter', 'librosa', 'numba', 'llvmlite', 'sklearn', 'scipy', 'av',
                       'torchaudio', 'torchvision', 'matplotlib', 'pandas', 'pytest', 'soundfile',
                       'IPython', 'nuitka', 'Cython', 'imageio_ffmpeg', 'PySide6.QtQml',
                       'PySide6.QtQuick', 'PySide6.QtSql', 'PySide6.QtTest'],
             noarchive=False, optimize=1)
a.binaries = [entry for entry in a.binaries if not Path(entry[0]).name.lower().startswith(('icuuc', 'icuin', 'icudt', 'cudnn'))]
# PATH lookups can pick another distribution's OpenSSL (Anaconda ships 3.0) for the
# CPython _ssl.pyd linked against a newer one; _ssl then fails to load and every
# HTTPS request (model downloads, OpenRouter, updates) breaks.
python_root = Path(__import__('sys').base_prefix)
def _python_openssl(entry):
    name = Path(entry[0]).name
    if not name.lower().startswith(('libssl-', 'libcrypto-')):
        return entry
    own = next((folder/name for folder in (python_root/'DLLs', python_root/'Library/bin')
                if (folder/name).is_file()), None)
    if own is None:
        raise SystemExit(f'{name} must come from the build Python ({python_root}), not {entry[1]}.')
    return (entry[0], str(own), entry[2])
a.binaries = [_python_openssl(entry) for entry in a.binaries]

# PyInstaller resolves _ssl.pyd's OpenSSL imports through PATH, so a conda
# Library\bin on PATH can contribute an older libssl/libcrypto that _ssl.pyd
# cannot bind to ("DLL load failed ... procedure could not be found"). Ship the
# exact DLLs the build interpreter itself loads for _ssl/_hashlib.
def build_openssl_dlls():
    import _ssl, _hashlib  # noqa: F401
    sys.path.insert(0, str(project/'app'))
    try:
        from entrypoint import _loaded_openssl
    finally:
        sys.path.pop(0)
    loaded = {Path(path).name.lower(): Path(path) for path in _loaded_openssl()}
    if not loaded:
        for folder in (Path(_ssl.__file__).parent, Path(sys.base_prefix)/'DLLs',
                       Path(sys.base_prefix)/'Library'/'bin', Path(sys.prefix)/'Library'/'bin'):
            for path in sorted(folder.glob('lib*-*.dll')) if folder.is_dir() else []:
                if path.name.lower().startswith(('libssl', 'libcrypto')):
                    loaded.setdefault(path.name.lower(), path)
    if not any(n.startswith('libssl') for n in loaded) or not any(n.startswith('libcrypto') for n in loaded):
        raise SystemExit(f'Cannot locate the OpenSSL DLLs used by {sys.executable}: {sorted(loaded)}')
    return loaded

openssl_dlls = build_openssl_dlls()
print('Bundling build-interpreter OpenSSL:', *(str(path) for path in openssl_dlls.values()))
a.binaries = [entry for entry in a.binaries if entry[0].lower() not in openssl_dlls]
a.binaries += [(path.name, str(path), 'BINARY') for path in openssl_dlls.values()]
pyz = PYZ(a.pure)
release_version = (project/'VERSION').read_text(encoding='utf-8').strip()
version_numbers = tuple(map(int, release_version.split('.'))) + (0,)
windows_version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers,
                      mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'Fardin Milani'),
        StringStruct('FileDescription', 'Avunote — Offline speech and AI workspace'),
        StringStruct('FileVersion', release_version),
        StringStruct('InternalName', 'Avunote'),
        StringStruct('OriginalFilename', 'Avunote.exe'),
        StringStruct('ProductName', 'Avunote'),
        StringStruct('ProductVersion', release_version),
        StringStruct('LegalCopyright', 'Copyright 2026 Fardin Milani'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Avunote',
          console=False, debug=False, strip=False, upx=False,
          icon=str(project/'assets/avunote.ico'), version=windows_version)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Avunote')
