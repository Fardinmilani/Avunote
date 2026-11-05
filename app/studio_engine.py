"""Local ASR with bounded streaming chunks, checkpointed output and CPU fallback."""
import gc
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import wave

from model_catalog import CATALOG, LANGUAGES, get_model, models_for_language, find_local_model
from compute_devices import resolve_device, gpu_memory_sample, find_openvino_model


def ffmpeg_executable():
    root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    for file in [root/'vendor/ffmpeg.exe', root/'ffmpeg.exe']:
        if file.is_file():
            return str(file)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def write_json(path, payload):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def _write_text(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(value, encoding='utf-8')
    os.replace(temporary, path)


def wav_info(path):
    with wave.open(str(path), 'rb') as stream:
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or stream.getframerate() != 16000:
            raise ValueError('Expected mono PCM16 WAV at 16000 Hz')
        frames = stream.getnframes()
        if frames <= 0:
            raise ValueError('The decoded audio is empty')
        return frames, stream.getframerate()


def iter_audio_chunks(path, chunk_seconds=20, quiet=True):
    """Yield every frame once, buffering at most one chosen-size PCM16 window.

    A quiet boundary may shorten a chunk to 75% of its requested maximum.
    Remaining samples stay in the bounded buffer: no overlaps, gaps, or text edits.
    """
    import numpy as np
    if chunk_seconds not in {10, 15, 20, 25, 30}:
        raise ValueError('Chunk duration must be 10, 15, 20, 25, or 30 seconds')
    total, rate = wav_info(path)
    maximum, start, pending = int(chunk_seconds*rate), 0, b''
    with wave.open(str(path), 'rb') as stream:
        while start < total:
            wanted = min(maximum, total-start)
            needed = wanted-len(pending)//2
            if needed > 0:
                pending += stream.readframes(needed)
            if len(pending)//2 != wanted:
                raise ValueError('Decoded WAV ended before its declared audio length')
            samples = np.frombuffer(pending, dtype='<i2').astype(np.float32)/32768.0
            count = wanted
            if quiet and start+wanted < total:
                first = max(int(maximum*.75), maximum-5*rate)
                points = np.arange(first, wanted-rate//10, rate//10, dtype=np.int64)
                if len(points):
                    energy = np.array([np.mean(samples[x:x+rate//10]**2) for x in points])
                    if energy.min() < np.mean(samples**2)*.15:
                        count = int(points[int(energy.argmin())]+rate//20)
            yield start, start+count, samples[:count]
            pending = pending[count*2:]
            start += count


class _TransformersRunner:
    def __init__(self, path, device, language):
        import torch
        from transformers import AutoProcessor, WhisperForConditionalGeneration
        self.torch, self.device = torch, device
        self.compute_type = 'float16' if device == 'cuda' else 'float32'
        self.dtype = torch.float16 if device == 'cuda' else torch.float32
        torch.set_num_threads(min(8, os.cpu_count() or 1))
        self.processor = AutoProcessor.from_pretrained(str(path), local_files_only=True)
        self.model = WhisperForConditionalGeneration.from_pretrained(str(path), local_files_only=True,
                      use_safetensors=True, torch_dtype=self.dtype).to(device).eval()

    def generate(self, samples, beams):
        inputs = self.processor(samples, sampling_rate=16000, return_tensors='pt', return_attention_mask=True)
        features = inputs.input_features.to(device=self.device, dtype=self.dtype)
        attention = inputs.attention_mask.to(self.device)
        with self.torch.inference_mode():
            ids = self.model.generate(features, attention_mask=attention, task='transcribe', num_beams=beams, do_sample=False)
        return self.processor.batch_decode(ids, skip_special_tokens=True, normalize=False, basic_normalize=False)[0]

    def close(self):
        self.model = None
        gc.collect()
        if self.device == 'cuda':
            try:
                self.torch.cuda.empty_cache()
            except Exception:
                pass


class _CT2Runner:
    def __init__(self, path, device, language):
        import ctranslate2
        from tokenizers import Tokenizer
        from transformers import WhisperFeatureExtractor
        self.ct2, self.device = ctranslate2, device
        self.compute_type = 'float16' if device == 'cuda' else 'int8'
        self.model = ctranslate2.models.Whisper(str(path), device=device, compute_type=self.compute_type,
                    intra_threads=min(8, os.cpu_count() or 1), inter_threads=1)
        self.tokenizer = Tokenizer.from_file(str(path/'tokenizer.json'))
        self.processor = WhisperFeatureExtractor()
        code = next(row['whisper_code'] for row in LANGUAGES if row['code'] == language)
        self.prompt = [self.tokenizer.token_to_id(token) for token in
                      ['<|startoftranscript|>', f'<|{code}|>', '<|transcribe|>', '<|notimestamps|>']]
        if any(token is None for token in self.prompt):
            raise ValueError('Language token is unavailable in this model')

    def generate(self, samples, beams):
        import numpy as np
        inputs = self.processor(samples, sampling_rate=16000, return_tensors='np').input_features
        features = self.ct2.StorageView.from_array(np.ascontiguousarray(inputs, dtype=np.float32))
        result = self.model.generate(features, [list(self.prompt)], beam_size=beams, max_length=448)[0]
        return self.tokenizer.decode(result.sequences_ids[0], skip_special_tokens=True)

    def close(self):
        model, self.model = self.model, None
        if model is not None and hasattr(model, 'unload_model'):
            try:
                model.unload_model()
            except Exception:
                pass
        del model
        gc.collect()


def load_runner(backend, path, device, language):
    return (_TransformersRunner if backend == 'transformers' else _CT2Runner)(path, device, language)


class _OpenVINORunner:
    def __init__(self, path, language):
        import openvino_genai
        self.device, self.compute_type = 'npu', 'openvino-ir'
        self.runtime_backend = 'openvino-genai'
        self.pipeline = openvino_genai.WhisperPipeline(str(path), 'NPU')
        self.language = next(row['whisper_code'] for row in LANGUAGES if row['code'] == language)
        self.source_path = str(path)

    def generate(self, samples, beams):
        # Each call is a separate short-form request; no previous transcript prompt.
        # Dedicated AZB has no generic Whisper AZB token; preserve its exported
        # language configuration instead of substituting North Azerbaijani.
        kwargs = {'task': 'transcribe', 'return_timestamps': False,
                  'num_beams': beams, 'max_length': 448, 'do_sample': False}
        if self.language is not None:
            kwargs['language'] = f'<|{self.language}|>'
        result = self.pipeline.generate(samples.tolist(), **kwargs)
        if not result.texts or not isinstance(result.texts[0], str):
            raise ValueError('OpenVINO Whisper did not return decoded text')
        return result.texts[0]

    def close(self):
        self.pipeline = None
        gc.collect()


def transcribe(audio_path, output_path, model_key='whisper-base-full', beams=5, language='azb',
               device='auto', chunk_seconds=20, skip_digital_silence=False):
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', HF_HUB_DISABLE_XET='1')
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    report = {'subfolder': model_key, 'language': language, 'requested_device': device,
              'device': 'cpu', 'actual_device': 'cpu', 'devices_used': [], 'chunk_seconds': chunk_seconds,
              'beams': beams, 'errors': [], 'fallback_reasons': [], 'fallback_events': [],
              'peak_rss_mib_sampled': 0, 'gpu_peak_memory_mib_sampled': None,
              'load_seconds': 0.0, 'inference_seconds': 0.0, 'chunks': [], 'status': 'preparing',
              'completed_audio_seconds': 0.0, 'skip_digital_silence': bool(skip_digital_silence)}
    stop, monitor, runner = threading.Event(), None, None
    metrics_path = output.with_suffix('.metrics.json')

    def progress(phase, **values):
        write_json(output.with_suffix('.progress.json'), {'phase': phase,
                   'elapsed_seconds': time.perf_counter()-start, 'actual_device': report['actual_device'],
                   'device': report['device'], 'requested_device': device,
                   'fallback_reasons': list(report['fallback_reasons']), **values})

    def checkpoint():
        report['total_seconds'] = time.perf_counter()-start
        _write_text(output, '\n'.join(chunk['text'] for chunk in report['chunks']))
        write_json(output.with_suffix('.segments.json'), {'language': language, 'model': model_key,
                   'completed_audio_seconds': report['completed_audio_seconds'], 'segments': report['chunks']})
        write_json(metrics_path, report)

    def fallback(phase, reason, index=None):
        report['fallback_reasons'].append(reason)
        report['fallback_events'].append({'phase': phase, 'reason': reason, 'chunk_index': index,
                                          'from': report['actual_device'], 'to': 'cpu'})
        report['actual_device'] = 'cpu'
        progress('fallback', reason=reason, chunk_index=index)

    def load(actual):
        nonlocal runner
        began = time.perf_counter()
        try:
            if actual == 'npu':
                ir_path = find_openvino_model(model_key, model_path)
                if ir_path is None:
                    raise ValueError('Matching OpenVINO export is no longer available')
                runner = _OpenVINORunner(ir_path, language)
                report['openvino_model_path'] = str(ir_path)
            else:
                runner = load_runner(item['backend'], model_path, actual, language)
            report['compute_type'] = runner.compute_type
            report['runtime_backend'] = getattr(runner, 'runtime_backend', item['backend'])
            report['actual_device'] = actual
            module = sys.modules.get('torch' if item['backend'] == 'transformers' else 'ctranslate2')
            if module is not None:
                report['torch_version' if item['backend'] == 'transformers' else 'ctranslate2_version'] = getattr(module, '__version__', 'unknown')
        finally:
            report['load_seconds'] += time.perf_counter()-began

    def release():
        nonlocal runner
        if runner is not None:
            runner.close()
            runner = None
        gc.collect()
        if item['backend'] == 'transformers':
            torch = sys.modules.get('torch')
            if torch is not None:
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass

    try:
        if model_key not in {row['key'] for row in CATALOG}:
            raise ValueError('Unknown model')
        if chunk_seconds not in {10, 15, 20, 25, 30}:
            raise ValueError('Chunk duration must be 10, 15, 20, 25, or 30 seconds')
        if not isinstance(beams, int) or not 1 <= beams <= 10:
            raise ValueError('Beam count must be between 1 and 10')
        item = get_model(model_key)
        if model_key not in {row['key'] for row in models_for_language(language)}:
            raise ValueError('The selected model does not support this language category')
        model_path = find_local_model(model_key)
        if model_path is None:
            raise FileNotFoundError('Model is not installed. Download it from the library or add a local model first.')
        if not Path(audio_path).is_file():
            raise ValueError('Audio file does not exist')
        report.update(repo=item['repo'], revision=item['revision'], backend=item['backend'])
        progress('preparing')
        import psutil
        process = psutil.Process()

        def sample():
            while not stop.is_set():
                try:
                    report['peak_rss_mib_sampled'] = max(report['peak_rss_mib_sampled'], process.memory_info().rss/1024**2)
                except Exception:
                    pass
                stop.wait(.15)

        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        progress('decoding')
        with tempfile.TemporaryDirectory(prefix='decode-', dir=output.parent) as temporary:
            wav = Path(temporary)/'mono.wav'
            subprocess.run([ffmpeg_executable(), '-nostdin', '-v', 'error', '-i', str(audio_path),
                            '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav)],
                           capture_output=True, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            frames, rate = wav_info(wav)
            report['audio_seconds'] = frames/rate
            actual, reason = resolve_device(device, item['backend'], model_key=model_key, model_path=model_path)
            report['actual_device'] = report['device'] = actual
            report['device_selection_reason'] = reason
            if device in {'cuda', 'npu'} and actual == 'cpu':
                fallback('capability', reason)
            progress('loading')
            try:
                load(actual)
            except Exception as exc:
                if actual not in {'cuda', 'npu'}:
                    raise
                fallback('loading', f'{actual.upper()} model loading failed: {type(exc).__name__}: {exc}. Retrying on CPU.')
                release()
                load('cpu')
            report['status'] = 'running'
            for index, (begin, end, samples) in enumerate(iter_audio_chunks(wav, chunk_seconds, quiet=beams > 1)):
                estimated = max(index+1, math.ceil(report['audio_seconds']/chunk_seconds))
                progress('transcribing', completed=index, total=estimated, total_is_estimate=True,
                         processed_seconds=begin/rate, audio_seconds=frames/rate, fraction=begin/frames)
                skipped = skip_digital_silence and not samples.any()
                if skipped:
                    decoded, elapsed = '', 0.0
                else:
                    before = time.perf_counter()
                    try:
                        decoded = runner.generate(samples, beams)
                    except Exception as exc:
                        report['inference_seconds'] += time.perf_counter()-before
                        if runner.device not in {'cuda', 'npu'}:
                            raise
                        fallback('inference', f'{runner.device.upper()} failed in segment {index+1}: {type(exc).__name__}: {exc}. Retrying this segment once on CPU.', index)
                        release()
                        load('cpu')
                        before = time.perf_counter()
                        decoded = runner.generate(samples, beams)
                    elapsed = time.perf_counter()-before
                    report['inference_seconds'] += elapsed
                actual = runner.device
                if actual not in report['devices_used']:
                    report['devices_used'].append(actual)
                report['actual_device'] = actual
                report['device'] = 'mixed' if len(report['devices_used']) > 1 else actual
                if actual == 'cuda':
                    observation = gpu_memory_sample(getattr(runner, 'torch', None))
                    if observation:
                        report['gpu_peak_memory_mib_sampled'] = max(report['gpu_peak_memory_mib_sampled'] or 0, observation['mib'])
                        report['gpu_memory_source'] = observation['source']
                report['chunks'].append({'start_seconds': begin/rate, 'end_seconds': end/rate,
                    'start_sample': begin, 'end_sample': end, 'text': decoded, 'device': actual,
                    'compute_type': runner.compute_type, 'runtime_backend': getattr(runner, 'runtime_backend', item['backend']),
                    'inference_seconds': elapsed, 'digital_silence_skipped': bool(skipped)})
                report['completed_audio_seconds'] = end/rate
                checkpoint()
                progress('transcribing', completed=index+1, total=max(index+1, estimated), total_is_estimate=True,
                         processed_seconds=end/rate, audio_seconds=frames/rate, fraction=end/frames)
            report['status'] = 'success'
            checkpoint()
            progress('done', completed=len(report['chunks']), total=len(report['chunks']), fraction=1.0,
                     processed_seconds=frames/rate, audio_seconds=frames/rate)
        return 0
    except Exception as exc:
        detail = exc.stderr.decode('utf-8', errors='replace') if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        report['status'] = 'failed'
        report['errors'].append(f'{type(exc).__name__}: {detail}')
        report['traceback'] = traceback.format_exc()
        try:
            progress('error', error=detail, processed_seconds=report['completed_audio_seconds'])
        except OSError:
            pass
        return 1
    finally:
        stop.set()
        if monitor:
            monitor.join(2)
        if runner is not None:
            try:
                runner.close()
            except Exception:
                pass
        report['total_seconds'] = time.perf_counter()-start
        write_json(metrics_path, report)
