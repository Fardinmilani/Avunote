"""Local fixtures for long audio, actual device reporting and CPU retries."""
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import compute_devices as devices
import model_catalog as catalog
import studio_engine as engine


def write_wav(path, samples):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
        stream.writeframes(np.asarray(samples, dtype='<i2').tobytes())


class Streaming(unittest.TestCase):
    def test_quiet_chunks_cover_every_frame_once_with_bounded_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'long.wav'
            original=(np.arange(75*16000+119,dtype=np.int64)%2000-1000).astype(np.int16)
            original[16*16000:17*16000]=0
            original[35*16000:36*16000]=0
            write_wav(path,original)
            calls=[];read=wave.Wave_read.readframes
            def observed(stream,count):
                calls.append(count)
                return read(stream,count)
            with patch.object(wave.Wave_read,'readframes',observed):
                chunks=list(engine.iter_audio_chunks(path,20,quiet=True))
            self.assertGreater(len(chunks),3)
            self.assertEqual(chunks[0][0],0)
            self.assertEqual(chunks[-1][1],len(original))
            for previous,current in zip(chunks,chunks[1:]):self.assertEqual(previous[1],current[0])
            self.assertTrue(all(len(row[2])<=20*16000 for row in chunks))
            self.assertTrue(all(count<=20*16000 for count in calls))
            self.assertEqual(sum(calls),len(original))
            reconstructed=np.concatenate([np.rint(row[2]*32768).astype(np.int16) for row in chunks])
            np.testing.assert_array_equal(reconstructed,original)

    def test_chunk_options_are_exact_in_fast_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'long.wav';write_wav(path,np.ones(63*16000,dtype=np.int16))
            for seconds in [10,15,20,25,30]:
                chunks=list(engine.iter_audio_chunks(path,seconds,quiet=False))
                self.assertEqual(chunks[0][1],seconds*16000)
                self.assertEqual(sum(len(x[2]) for x in chunks),63*16000)
            with self.assertRaises(ValueError):list(engine.iter_audio_chunks(path,60))


class EngineDevices(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'VOXRIVA_DATA_DIR':str(self.root/'cache'),'VOXRIVA_OPENVINO_MODELS_DIR':''})
        self.env.start()
        self.audio=self.root/'input.wav'
        write_wav(self.audio,np.concatenate([np.full(10*16000,value,dtype=np.int16) for value in [1,2,3]]))
        self.calls=[];self.loads=[];self.gpu_fail_value=2;self.cpu_fail=False

    def tearDown(self):self.env.stop();self.tmp.cleanup()

    def runner(self,device):
        outer=self
        class Runner:
            compute_type='float16' if device=='cuda' else 'int8'
            def __init__(self):self.device=device
            def generate(self,samples,beams):
                value=int(round(float(samples[0])*32768));outer.calls.append((device,value))
                if device=='cuda' and value==outer.gpu_fail_value:raise RuntimeError('CUDA out of memory')
                if device=='cpu' and outer.cpu_fail:raise RuntimeError('CPU fixture failure')
                return f'  {device}:{value}  '
            def close(self):pass
        return Runner()

    def load(self,backend,path,device,language):
        self.loads.append(device)
        return self.runner(device)

    def convert(self,args,**kwargs):Path(args[-1]).write_bytes(self.audio.read_bytes())

    def run_engine(self,device='cuda',resolve=True,loader=None):
        output=self.root/'result.txt'
        with patch.object(engine,'find_local_model',return_value=self.root),\
             patch.object(engine,'ffmpeg_executable',return_value='fixture-ffmpeg'),\
             patch.object(engine.subprocess,'run',side_effect=self.convert),\
             patch.object(engine,'load_runner',side_effect=loader or self.load),\
             patch.object(engine,'gpu_memory_sample',return_value=None):
            if resolve:
                with patch.object(engine,'resolve_device',return_value=(device,'fixture device')):
                    code=engine.transcribe(self.audio,output,'multilingual-tiny',1,'fa',device,10)
            else:code=engine.transcribe(self.audio,output,'multilingual-tiny',1,'fa',device,10)
        metrics=json.loads(output.with_suffix('.metrics.json').read_text(encoding='utf-8'))
        return code,output,metrics

    def test_mid_chunk_cuda_failure_retries_only_failed_chunk_on_cpu(self):
        code,output,report=self.run_engine()
        self.assertEqual(code,0,report)
        self.assertEqual(self.calls,[('cuda',1),('cuda',2),('cpu',2),('cpu',3)])
        self.assertEqual(self.loads,['cuda','cpu'])
        self.assertEqual(output.read_text(encoding='utf-8'),'  cuda:1  \n  cpu:2  \n  cpu:3  ')
        self.assertEqual(report['device'],'mixed');self.assertEqual(report['actual_device'],'cpu')
        self.assertEqual([x['device'] for x in report['chunks']],['cuda','cpu','cpu'])
        self.assertEqual([(x['start_sample'],x['end_sample']) for x in report['chunks']],
                         [(0,160000),(160000,320000),(320000,480000)])
        self.assertEqual(len(report['fallback_events']),1)
        self.assertEqual(report['fallback_events'][0]['chunk_index'],1)
        self.assertEqual(report['completed_audio_seconds'],30)
        segments=json.loads(output.with_suffix('.segments.json').read_text(encoding='utf-8'))
        self.assertEqual(len(segments['segments']),3)

    def test_cuda_load_failure_retries_cpu(self):
        def loader(backend,path,device,language):
            self.loads.append(device)
            if device=='cuda':raise RuntimeError('CUDA DLL unavailable')
            return self.runner(device)
        code,output,report=self.run_engine(loader=loader)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['cuda','cpu'])
        self.assertEqual(report['device'],'cpu')
        self.assertEqual(report['fallback_events'][0]['phase'],'loading')

    def test_cpu_retry_failure_preserves_previous_checkpoint(self):
        self.cpu_fail=True
        code,output,report=self.run_engine()
        self.assertEqual(code,1)
        self.assertEqual(self.calls,[('cuda',1),('cuda',2),('cpu',2)])
        self.assertEqual(output.read_text(encoding='utf-8'),'  cuda:1  ')
        self.assertEqual(len(report['chunks']),1)
        self.assertEqual(report['completed_audio_seconds'],10)
        self.assertEqual(report['status'],'failed')

    def create_ir(self,key='multilingual-tiny'):
        model=catalog.get_model(key);path=self.root/'openvino';path.mkdir()
        for name in devices.OPENVINO_FILES:(path/name).write_text('{}',encoding='utf-8')
        (path/'config.json').write_text('{"model_type":"whisper"}',encoding='utf-8')
        info={'format':'openvino-genai-whisper','source_model_key':key,'source_repo':model['repo'],
              'source_revision':model['revision'],'source_subfolder':model['subfolder'],'speech_language':'azb' if key.startswith('whisper-') else 'multilingual'}
        (path/'voxriva-openvino.json').write_text(json.dumps(info),encoding='utf-8')
        return path

    def npu_modules(self,fail_load=False,fail_infer=False):
        outer=self
        class Pipeline:
            def __init__(self,path,device):
                outer.loads.append(device)
                outer.assertEqual(device,'NPU')
                if fail_load:raise RuntimeError('NPU driver incompatible')
            def generate(self,samples,**kwargs):
                value=int(round(samples[0]*32768));outer.calls.append(('npu',value))
                outer.assertEqual(kwargs['task'],'transcribe')
                outer.assertEqual(kwargs['language'],'<|fa|>')
                outer.assertNotIn('initial_prompt',kwargs)
                outer.assertEqual(kwargs['max_length'],448)
                if fail_infer and value==2:raise RuntimeError('NPU device failure')
                return types.SimpleNamespace(texts=[f'  npu:{value}  '])
        return patch.dict(sys.modules,{'openvino':types.SimpleNamespace(Core=lambda:types.SimpleNamespace(available_devices=['CPU','NPU.0'])),
                                       'openvino_genai':types.SimpleNamespace(WhisperPipeline=Pipeline)})

    def test_matching_optional_openvino_npu_really_runs_pipeline(self):
        self.create_ir()
        with self.npu_modules():code,output,report=self.run_engine(device='npu',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['NPU'])
        self.assertEqual(report['device'],'npu')
        self.assertEqual(report['runtime_backend'],'openvino-genai')
        self.assertEqual(output.read_text(encoding='utf-8'),'  npu:1  \n  npu:2  \n  npu:3  ')

    def test_optional_npu_load_failure_retries_cpu(self):
        self.create_ir()
        with self.npu_modules(fail_load=True):code,output,report=self.run_engine(device='npu',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['NPU','cpu'])
        self.assertEqual(report['actual_device'],'cpu')
        self.assertIn('NPU',report['fallback_reasons'][0])

    def test_optional_npu_mid_inference_failure_retries_same_chunk(self):
        self.create_ir()
        with self.npu_modules(fail_infer=True):code,output,report=self.run_engine(device='npu',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.calls,[('npu',1),('npu',2),('cpu',2),('cpu',3)])
        self.assertEqual(report['device'],'mixed')

    def test_auto_can_choose_real_optional_npu_when_cuda_is_unavailable(self):
        self.create_ir()
        with self.npu_modules(),patch.object(devices,'probe_cuda',return_value=(False,'No CUDA runtime')):
            code,output,report=self.run_engine(device='auto',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['NPU'])
        self.assertEqual(report['requested_device'],'auto')
        self.assertEqual(report['actual_device'],'npu')

    def test_npu_hardware_presence_required_in_addition_to_local_export(self):
        self.create_ir()
        with self.npu_modules(),patch.object(sys.modules['openvino'],'Core',return_value=types.SimpleNamespace(available_devices=['CPU','GPU'])):
            code,output,report=self.run_engine(device='npu',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['cpu'])
        self.assertIn('no usable NPU',report['fallback_reasons'][0])

    def test_wrong_npu_checkpoint_provenance_never_substitutes_model(self):
        path=self.create_ir()
        info=json.loads((path/'voxriva-openvino.json').read_text(encoding='utf-8'))
        info['source_revision']='0'*40
        (path/'voxriva-openvino.json').write_text(json.dumps(info),encoding='utf-8')
        with self.npu_modules():code,output,report=self.run_engine(device='npu',resolve=False)
        self.assertEqual(code,0,report)
        self.assertEqual(self.loads,['cpu'])
        self.assertEqual(report['actual_device'],'cpu')
        self.assertTrue(report['fallback_reasons'])


class Capabilities(unittest.TestCase):
    def test_portable_optional_runtime_uses_only_explicit_local_directory(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'VOXRIVA_OPTIONAL_BACKENDS_DIR':directory}),\
             patch.object(sys,'path',list(sys.path)):
            root=str(Path(directory).resolve());before=len(devices._dll_handles)
            try:
                devices.prepare_optional_backends()
                self.assertIn(root,sys.path)
                self.assertEqual(sys.path[-1],root)
            finally:
                devices._backend_directories.discard(root)
                for handle in devices._dll_handles[before:]:handle.close()
                del devices._dll_handles[before:]

    def test_cpu_options_never_import_ml_runtimes(self):
        with patch.object(devices,'probe_cuda',side_effect=AssertionError('Probe must be deferred')),\
             patch.object(devices,'_module_available',return_value=False):
            options=devices.device_options('multilingual-tiny')
        self.assertEqual([x['key'] for x in options],['auto','cpu','cuda','npu'])
        self.assertTrue(options[1]['available'])
        self.assertFalse(options[3]['available'])

    def test_real_backend_capabilities_not_hardware_name(self):
        cpu_torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:False))
        self.assertEqual(devices.resolve_device('cuda','transformers',torch_module=cpu_torch)[0],'cpu')
        cuda_torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda:True))
        self.assertEqual(devices.resolve_device('cuda','transformers',torch_module=cuda_torch)[0],'cuda')
        ct2=types.SimpleNamespace(get_cuda_device_count=lambda:1)
        self.assertEqual(devices.resolve_device('auto','faster-whisper',ct2_module=ct2)[0],'cuda')
        self.assertEqual(devices.resolve_device('npu','faster-whisper')[0],'cpu')
        with self.assertRaises(ValueError):devices.resolve_device('fake','faster-whisper')


if __name__=='__main__':unittest.main()
