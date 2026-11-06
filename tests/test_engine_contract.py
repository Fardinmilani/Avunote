"""Offline engine contract tests; no weights, downloads, or audio uploads."""
import json
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import wave

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import studio_engine as engine


class EngineContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.audio=self.root/'fixture.wav'
        with wave.open(str(self.audio),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000)
            stream.writeframes(b'\0\0'*16000)
        self.calls=[]
        self.text='  متنِ خام، Əİö؟\nبدون بازنویسی  '
        outer=self

        class Tokenizer:
            @classmethod
            def from_file(cls,path):
                outer.calls.append(('tokenizer',path))
                return cls()
            def token_to_id(self,token):
                return {'<|startoftranscript|>':1,'<|fa|>':2,'<|tr|>':3,'<|en|>':4,
                        '<|transcribe|>':5,'<|notimestamps|>':6}.get(token)
            def decode(self,ids,skip_special_tokens=False):
                outer.calls.append(('decode',ids,skip_special_tokens))
                return outer.text

        class Whisper:
            def __init__(self,path,**kwargs):
                outer.calls.append(('model',path,kwargs))
            def generate(self,features,prompts,**kwargs):
                outer.calls.append(('generate',prompts,kwargs))
                return [types.SimpleNamespace(sequences_ids=[[11,12]])]

        class Features:
            def __call__(self,audio,**kwargs):
                outer.calls.append(('features',len(audio),kwargs))
                return types.SimpleNamespace(input_features=np.zeros((1,80,3000),dtype=np.float32))

        self.modules=patch.dict(sys.modules,{
            'ctranslate2':types.SimpleNamespace(__version__='fixture',models=types.SimpleNamespace(Whisper=Whisper),
                          StorageView=types.SimpleNamespace(from_array=lambda a:a)),
            'tokenizers':types.SimpleNamespace(Tokenizer=Tokenizer),
            'transformers':types.SimpleNamespace(WhisperFeatureExtractor=Features),
        })
        self.modules.start()

    def tearDown(self):
        self.modules.stop();self.tmp.cleanup()

    def convert(self,args,**kwargs):
        self.assertFalse(any('http' in str(x) for x in args))
        Path(args[-1]).write_bytes(self.audio.read_bytes())
        return types.SimpleNamespace(returncode=0)

    def run_engine(self,language,key='multilingual-tiny',local=True):
        output=self.root/f'{language}.txt'
        with patch.object(engine,'find_local_model',return_value=self.root if local else None),\
             patch.object(engine,'ffmpeg_executable',return_value='local-ffmpeg'),\
             patch.object(engine.subprocess,'run',side_effect=self.convert),\
             patch('requests.sessions.Session.request',side_effect=AssertionError('Network forbidden during inference')):
            result=engine.transcribe(self.audio,output,key,beams=5,language=language)
        metrics=json.loads(output.with_suffix('.metrics.json').read_text(encoding='utf-8'))
        return result,output,metrics

    def test_explicit_language_transcribe_prompt_cpu_and_raw_text(self):
        for lang,token in [('fa',2),('tr',3),('en',4)]:
            with self.subTest(language=lang):
                self.calls.clear()
                result,output,metrics=self.run_engine(lang)
                self.assertEqual(result,0,metrics)
                self.assertEqual(output.read_text(encoding='utf-8'),self.text)
                call=next(x for x in self.calls if x[0]=='generate')
                self.assertEqual(call[1],[[1,token,5,6]])
                self.assertEqual(call[2]['beam_size'],5)
                model=next(x for x in self.calls if x[0]=='model')
                self.assertEqual(model[2]['device'],'cpu')
                self.assertEqual(model[2]['compute_type'],'int8')
                self.assertEqual(metrics['language'],lang)
                self.assertEqual(metrics['device'],'cpu')
                self.assertEqual(metrics['compute_type'],'int8')
                self.assertEqual(metrics['status'],'success')
                self.assertEqual(os.environ['HF_HUB_OFFLINE'],'1')
                self.assertEqual(os.environ['TRANSFORMERS_OFFLINE'],'1')

    def test_qwen_persian_uses_offline_onnx_and_recovers_from_saved_cuda_preference(self):
        stream = Mock()
        stream.result = types.SimpleNamespace(text='این یک آزمون محلی است.')
        recognizer = Mock()
        recognizer.create_stream.return_value = stream
        sherpa = types.SimpleNamespace(
            __version__='fixture', OfflineRecognizer=types.SimpleNamespace(
                from_qwen3_asr=Mock(return_value=recognizer)))
        output = self.root/'persian-onnx.txt'
        with patch.dict(sys.modules, {'sherpa_onnx': sherpa}), \
             patch.object(engine, 'find_local_model', return_value=self.root), \
             patch.object(engine, 'ffmpeg_executable', return_value='local-ffmpeg'), \
             patch.object(engine.subprocess, 'run', side_effect=self.convert), \
             patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden during inference')):
            status = engine.transcribe(self.audio, output, 'qwen3-asr-06b', language='fa', device='cuda')
        self.assertEqual(status, 0)
        self.assertEqual(output.read_text(encoding='utf-8'), stream.result.text)
        recognizer.decode_stream.assert_called_once_with(stream)
        self.assertEqual(stream.accept_waveform.call_args.args[0], 16000)
        self.assertEqual(len(stream.accept_waveform.call_args.args[1]), 16000)
        report = json.loads(output.with_suffix('.metrics.json').read_text(encoding='utf-8'))
        self.assertEqual(report['actual_device'], 'cpu')
        self.assertEqual(report['runtime_backend'], 'sherpa-onnx')
        self.assertEqual(report['fallback_events'][0]['phase'], 'capability')

    def test_south_azerbaijani_cannot_use_generic_multilingual_model(self):
        result,output,metrics=self.run_engine('azb')
        self.assertEqual(result,1)
        self.assertFalse(output.exists())
        self.assertFalse(self.calls)
        self.assertIn('does not support',metrics['errors'][0])

    def test_persian_cannot_use_dedicated_azb_model(self):
        result,output,metrics=self.run_engine('fa',key='whisper-base-full')
        self.assertEqual(result,1)
        self.assertFalse(output.exists())
        self.assertFalse(self.calls)

    def test_missing_model_never_downloads_implicitly(self):
        result,output,metrics=self.run_engine('fa',local=False)
        self.assertEqual(result,1)
        self.assertFalse(output.exists())
        self.assertFalse(self.calls)
        self.assertIn('FileNotFoundError',metrics['errors'][0])

    def test_final_progress_lock_does_not_turn_saved_result_into_failure(self):
        write = engine.write_json
        def locked_final_progress(path, payload, **kwargs):
            if Path(path).name.endswith('.progress.json') and payload['phase'] == 'done':
                raise PermissionError('Windows status file is held by another reader')
            return write(path, payload, **kwargs)
        with patch.object(engine, 'write_json', side_effect=locked_final_progress), \
             contextlib.redirect_stderr(io.StringIO()):
            result, output, metrics = self.run_engine('fa')
        self.assertEqual(result, 0, metrics)
        self.assertEqual(metrics['status'], 'success')
        self.assertEqual(metrics['errors'], [])
        self.assertEqual(metrics['progress_write_failures'], 1)
        self.assertEqual(len(metrics['warnings']), 1)
        self.assertEqual(output.read_text(encoding='utf-8'), self.text)

    def test_unavailable_progress_file_is_advisory_throughout_transcription(self):
        write = engine.write_json
        def locked_progress(path, payload, **kwargs):
            if Path(path).name.endswith('.progress.json'):
                raise PermissionError('Busy progress file')
            return write(path, payload, **kwargs)
        with patch.object(engine, 'write_json', side_effect=locked_progress), \
             contextlib.redirect_stderr(io.StringIO()):
            result, output, metrics = self.run_engine('fa')
        self.assertEqual(result, 0, metrics)
        self.assertEqual(metrics['status'], 'success')
        self.assertGreater(metrics['progress_write_failures'], 1)
        self.assertEqual(len(metrics['warnings']), 1)
        self.assertEqual(output.read_text(encoding='utf-8'), self.text)

    def test_result_storage_failure_remains_a_real_error(self):
        with patch.object(engine, '_write_text', side_effect=PermissionError('Result folder is not writable')), \
             contextlib.redirect_stderr(io.StringIO()):
            result, output, metrics = self.run_engine('fa')
        self.assertEqual(result, 1)
        self.assertEqual(metrics['status'], 'failed')
        self.assertIn('Result folder is not writable', metrics['errors'][0])
        self.assertFalse(output.exists())

    def test_final_metrics_error_does_not_hide_original_failure(self):
        write = engine.write_json
        def locked_metrics(path, payload, **kwargs):
            if Path(path).name.endswith('.metrics.json'):
                raise PermissionError('Metrics file is locked permanently')
            return write(path, payload, **kwargs)
        log = io.StringIO()
        with patch.object(engine, 'find_local_model', return_value=None), \
             patch.object(engine, 'write_json', side_effect=locked_metrics), \
             contextlib.redirect_stderr(log):
            result = engine.transcribe(self.audio, self.root/'failed.txt', 'multilingual-tiny', language='fa')
        self.assertEqual(result, 1)
        self.assertIn('FileNotFoundError', log.getvalue())
        self.assertIn('Could not save final processing metrics', log.getvalue())


if __name__=='__main__':
    unittest.main()
