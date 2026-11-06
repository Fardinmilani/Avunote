"""Capability-based selection. Importing this module never loads an ML runtime."""
from importlib import metadata
from importlib.util import find_spec
import json
import os
from pathlib import Path
import subprocess
import sys

from model_catalog import SHERPA_BACKENDS

NPU_REASON = ('NPU requires an optional OpenVINO GenAI runtime, supported NPU driver, and a '
              'local OpenVINO IR export of this exact selected model with provenance. '
              'Current PyTorch/CTranslate2 files cannot run directly on NPU. No runtime or model is downloaded automatically.')
ONNX_CPU_REASON = 'This ONNX model uses the bundled CPU runtime.'
OPENVINO_FILES = ['config.json', 'generation_config.json', 'preprocessor_config.json',
                  'tokenizer_config.json', 'openvino_encoder_model.xml', 'openvino_encoder_model.bin',
                  'openvino_decoder_model.xml', 'openvino_decoder_model.bin',
                  'openvino_tokenizer.xml', 'openvino_tokenizer.bin',
                  'openvino_detokenizer.xml', 'openvino_detokenizer.bin']
_dll_handles = []
_backend_directories = set()


def prepare_optional_backends():
    """Expose only an explicitly configured local optional-runtime directory.

    This also works with the portable Python runtime. Packages must match its
    Python version and architecture; nothing is installed, fetched or copied.
    """
    value = os.environ.get('AVUNOTE_OPTIONAL_BACKENDS_DIR') or os.environ.get('VOXRIVA_OPTIONAL_BACKENDS_DIR')
    if not value:
        return
    root = Path(value).expanduser().resolve()
    if not root.is_dir() or str(root) in _backend_directories:
        return
    if str(root) not in sys.path:
        sys.path.append(str(root))
    if os.name == 'nt' and hasattr(os, 'add_dll_directory'):
        for path in [root, root/'openvino/libs', root/'openvino_genai/libs', root/'openvino_tokenizers/lib']:
            if path.is_dir():
                try:
                    _dll_handles.append(os.add_dll_directory(str(path)))
                except OSError:
                    pass
    _backend_directories.add(str(root))


def find_openvino_model(model_key, model_path=None):
    """A user-supplied export must explicitly identify the selected checkpoint.

    voxriva-openvino.json fields: source_model_key/source_repo/source_revision/
    source_subfolder/speech_language/format. This records export provenance,
    not a claim that arbitrary IR weights can be cryptographically identified.
    """
    from model_catalog import get_model, _registered_roots
    model = get_model(model_key)
    if model['backend'] in SHERPA_BACKENDS:
        return None
    roots = []
    if model_path is not None:
        roots.append(Path(model_path)/'openvino')
    configured_root = os.environ.get('AVUNOTE_OPENVINO_MODELS_DIR') or os.environ.get('VOXRIVA_OPENVINO_MODELS_DIR')
    if configured_root:
        root = Path(configured_root)
        roots.extend([root/model_key, root/model_key/'openvino', root])
    for root in _registered_roots():
        roots.extend([root/'openvino', root/model_key/'openvino', root])
    for root in roots:
        try:
            manifest = root/'avunote-openvino.json'
            if not manifest.is_file():
                manifest = root/'voxriva-openvino.json'
            info = json.loads(manifest.read_text(encoding='utf-8'))
            if not isinstance(info, dict) or info.get('format') != 'openvino-genai-whisper':
                continue
            if any(info.get(k) != v for k, v in {
                'source_model_key': model_key, 'source_repo': model['repo'],
                'source_revision': model['revision'], 'source_subfolder': model['subfolder'],
            }.items()):
                continue
            if model['backend'] == 'transformers' and info.get('speech_language') != 'azb':
                continue
            if not all((root/name).is_file() and (root/name).stat().st_size > 0 for name in OPENVINO_FILES):
                continue
            config = json.loads((root/'config.json').read_text(encoding='utf-8'))
            if not isinstance(config, dict) or config.get('model_type') != 'whisper':
                continue
            return root
        except (OSError, ValueError, TypeError):
            continue
    return None


def _module_available(name):
    prepare_optional_backends()
    if name in sys.modules:
        return sys.modules[name] is not None
    try:
        return find_spec(name) is not None
    except (ValueError, ImportError, ModuleNotFoundError):
        return False


def probe_npu(model_key, model_path=None):
    path = find_openvino_model(model_key, model_path)
    if path is None:
        return False, NPU_REASON
    try:
        prepare_optional_backends()
        import openvino
        import openvino_genai
        if not hasattr(openvino_genai, 'WhisperPipeline'):
            return False, 'The installed OpenVINO GenAI runtime has no WhisperPipeline.'
        devices = openvino.Core().available_devices
        if not any(str(device).upper().split('.')[0] == 'NPU' for device in devices):
            return False, 'OpenVINO found no usable NPU device. Check the NPU driver and hardware.'
        return True, 'Matching OpenVINO export and NPU detected; pipeline loading and inference will be validated.'
    except Exception as exc:
        return False, f'NPU capability check failed: {type(exc).__name__}: {exc}'


def probe_cuda(backend, torch_module=None, ct2_module=None):
    """Run in a worker, not on the UI thread. Detection is not a model-load test."""
    try:
        if backend == 'transformers':
            if torch_module is None:
                import torch as torch_module
            if not torch_module.cuda.is_available():
                return False, 'CUDA is unavailable in the installed PyTorch runtime or NVIDIA driver.'
        elif backend == 'faster-whisper':
            if ct2_module is None:
                import ctranslate2 as ct2_module
            if ct2_module.get_cuda_device_count() < 1:
                return False, 'CTranslate2 did not find an available CUDA device.'
        else:
            return False, 'This model backend has no CUDA implementation.'
        return True, 'CUDA detected; model loading and inference still need runtime validation.'
    except Exception as exc:
        return False, f'CUDA capability check failed: {type(exc).__name__}: {exc}'


def resolve_device(requested, backend, torch_module=None, ct2_module=None, model_key=None, model_path=None):
    if requested not in {'auto', 'cpu', 'cuda', 'npu'}:
        raise ValueError('Device must be auto, cpu, cuda, or npu')
    if requested == 'cpu':
        return 'cpu', 'CPU was explicitly selected.'
    if backend in SHERPA_BACKENDS:
        return 'cpu', ONNX_CPU_REASON
    if requested == 'npu':
        available, reason = probe_npu(model_key, model_path) if model_key else (False, NPU_REASON)
        return ('npu' if available else 'cpu'), reason
    available, reason = probe_cuda(backend, torch_module, ct2_module)
    if available:
        return 'cuda', reason
    if requested == 'auto' and model_key and find_openvino_model(model_key, model_path):
        npu_available, npu_reason = probe_npu(model_key, model_path)
        if npu_available:
            return 'npu', npu_reason
    return 'cpu', reason


def device_options(model_key=None, probe=False):
    """Cheap UI choices; available=None means validation is deferred to processing."""
    backend = None
    if model_key:
        from model_catalog import get_model
        backend = get_model(model_key)['backend']
    if backend in SHERPA_BACKENDS:
        return [
            {'key': key, 'title': title, 'available': key in {'auto', 'cpu'}, 'reason': ONNX_CPU_REASON}
            for key, title in [('auto', 'Automatic'), ('cpu', 'CPU'), ('cuda', 'NVIDIA GPU (CUDA)'),
                               ('npu', 'NPU (OpenVINO GenAI)')]
        ]
    available, reason = None, 'Checked at processing time. CUDA runtime and NVIDIA drivers are required.'
    if backend == 'transformers':
        try:
            if '+cpu' in metadata.version('torch'):
                available, reason = False, 'This PyTorch build is CPU-only. CUDA needs a separately installed compatible runtime.'
        except metadata.PackageNotFoundError:
            available, reason = False, 'PyTorch is not installed for this model backend.'
    if probe and backend:
        available, reason = probe_cuda(backend)
    npu_available, npu_reason = False, NPU_REASON
    if model_key:
        from model_catalog import find_local_model
        path = find_local_model(model_key)
        if find_openvino_model(model_key, path):
            if _module_available('openvino') and _module_available('openvino_genai'):
                npu_available, npu_reason = None, 'Matching NPU model export found. OpenVINO device validation will run when processing starts.'
                if probe:
                    npu_available, npu_reason = probe_npu(model_key, path)
            else:
                npu_reason = 'Matching OpenVINO model export found, but the optional OpenVINO GenAI runtime is not installed.'
    return [
        {'key': 'auto', 'title': 'Automatic', 'available': True,
         'reason': 'Try compatible CUDA, otherwise use CPU. No automatic runtime downloads.'},
        {'key': 'cpu', 'title': 'CPU', 'available': True, 'reason': 'Local CPU processing.'},
        {'key': 'cuda', 'title': 'NVIDIA GPU (CUDA)', 'available': available, 'reason': reason},
        {'key': 'npu', 'title': 'NPU (OpenVINO GenAI)', 'available': npu_available, 'reason': npu_reason},
    ]


def gpu_memory_sample(torch_module=None):
    """Best effort; None means unavailable rather than an invented zero reading."""
    if torch_module is not None:
        try:
            return {'mib': torch_module.cuda.max_memory_allocated()/1024**2, 'source': 'torch.cuda allocator'}
        except Exception:
            pass
    try:
        result = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,used_gpu_memory', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                values = [x.strip() for x in line.split(',')]
                if len(values) == 2 and values[0] == str(os.getpid()):
                    return {'mib': float(values[1]), 'source': 'nvidia-smi process sample'}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None
