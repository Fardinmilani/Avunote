"""Model-free Windows distribution. Build from project root with PyInstaller."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
    StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)

project = Path(SPECPATH)
vendor = project/'vendor/ffmpeg.exe'
if not vendor.is_file():
    raise SystemExit('Build the audio-only LGPL FFmpeg described in vendor/README.md first.')
hidden = ['torch', 'numpy', 'psutil', 'sounddevice', 'requests', 'ctranslate2', 'tokenizers',
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
datas += collect_data_files('_sounddevice_data')
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
