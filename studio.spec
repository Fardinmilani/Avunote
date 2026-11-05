"""Model-free Windows distribution. Build from project root with PyInstaller."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

project = Path(SPECPATH)
vendor = project/'vendor/ffmpeg.exe'
if not vendor.is_file():
    raise SystemExit('Build the audio-only LGPL FFmpeg described in vendor/README.md first.')
hidden = ['torch', 'numpy', 'psutil', 'sounddevice', 'requests', 'ctranslate2', 'tokenizers',
          'wave', 'array', 'uuid', 'tempfile', 'threading', 'traceback',
          'ctypes', 'ctypes.wintypes', 'base64', 'ipaddress', 'email.utils',
          'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtCore',
          'transformers', 'transformers.models.whisper.processing_whisper',
          'transformers.models.whisper.modeling_whisper',
          'transformers.models.whisper.feature_extraction_whisper',
          'transformers.models.whisper.tokenization_whisper',
          'transformers.models.whisper.tokenization_whisper_fast',
          'transformers.models.auto.processing_auto', 'transformers.generation.utils']
datas = [(str(vendor), 'vendor'), (str(project/'assets/voxriva-logo.png'), 'assets'),
         (str(project/'assets/voxriva-logo-transparent.png'), 'assets')]
datas += collect_data_files('_sounddevice_data')
for package in ['transformers', 'tokenizers', 'huggingface_hub', 'ctranslate2', 'requests']:
    datas += copy_metadata(package)
qtpath = __import__('os').environ.get('AZB_QT_PATH')
paths = [str(project/'app')] + ([qtpath] if qtpath else [])
a = Analysis([str(project/'app/entrypoint.py')], pathex=paths,
             binaries=collect_dynamic_libs('_sounddevice_data')+collect_dynamic_libs('ctranslate2'),
             datas=datas, hiddenimports=hidden,
             excludes=['studio_ui', 'studio_engine', 'model_catalog', 'model_downloads', 'ui_i18n', 'ui_locales',
                       'ai_panel', 'ai_clients', 'ai_profiles', 'compute_devices', 'studio_theme', 'ui_v3_strings',
                       'tkinter', 'librosa', 'numba', 'llvmlite', 'sklearn', 'scipy', 'av',
                       'torchaudio', 'torchvision', 'matplotlib', 'pandas', 'pytest', 'soundfile',
                       'IPython', 'nuitka', 'Cython', 'imageio_ffmpeg', 'PySide6.QtQml',
                       'PySide6.QtQuick', 'PySide6.QtSql', 'PySide6.QtTest'],
             noarchive=False, optimize=1)
a.binaries = [entry for entry in a.binaries if not Path(entry[0]).name.lower().startswith(('icuuc', 'icuin', 'icudt', 'cudnn'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Voxriva',
          console=False, debug=False, strip=False, upx=False, icon=str(project/'assets/voxriva.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Voxriva')
