"""Text-only AI transport tests: every HTTP request is mocked."""
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import ai_clients as ai


class Response:
    def __init__(self, data=None, status=200, headers=None, raw=None):
        self.status_code, self.headers = status, headers or {}
        self.body = raw if raw is not None else json.dumps(data or {}).encode()
        self.closed = False
    def iter_content(self, chunk_size):
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset:offset+chunk_size]
    def close(self):
        self.closed = True


class Session:
    def __init__(self, results):
        self.results, self.calls, self.trust_env = list(results), [], True
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.results.pop(0)
        if isinstance(result, Exception): raise result
        return result
    get = post


def profile(provider='gemini', **values):
    return {'provider': provider, 'model': 'example-model', 'key': 'secret-test-key-12345', **values}


class ClientTests(unittest.TestCase):
    def client(self, *responses):
        session = Session(responses)
        patcher = patch.object(ai.requests, 'Session', return_value=session)
        patcher.start()
        self.addCleanup(patcher.stop)
        return session

    def test_gemini_multiturn_and_header_only_key(self):
        session = self.client(Response({'candidates': [{'content': {'parts': [{'text': 'answer'}]}, 'finishReason': 'STOP'}]}))
        history = [{'role':'system','content':'Help with this text.'}, {'role':'user','content':'First question'},
                   {'role':'assistant','content':'Earlier reply'}, {'role':'user','content':'Follow-up'}]
        self.assertEqual(ai.chat(profile(), history), 'answer')
        url, request = session.calls[0]
        self.assertEqual(url, 'https://generativelanguage.googleapis.com/v1beta/models/example-model:generateContent')
        self.assertNotIn('secret-test-key', url)
        self.assertEqual(request['headers']['x-goog-api-key'], 'secret-test-key-12345')
        self.assertEqual([x['role'] for x in request['json']['contents']], ['user','model','user'])
        self.assertEqual(request['json']['systemInstruction']['parts'][0]['text'], 'Help with this text.')
        self.assertFalse(request['allow_redirects'])
        self.assertEqual(request['json']['generationConfig']['maxOutputTokens'], ai.DEFAULT_OUTPUT_TOKENS)

    def test_list_models_gemini_filters_chat_capable_and_keeps_key_in_header(self):
        session = self.client(Response({'models': [
            {'name': 'models/gemini-2.5-flash', 'supportedGenerationMethods': ['generateContent']},
            {'name': 'models/text-embedding-004', 'supportedGenerationMethods': ['embedContent']},
            {'name': 'models/gemini-2.5-pro', 'supportedGenerationMethods': ['generateContent', 'countTokens']}]}))
        self.assertEqual(ai.list_models(profile()), ['gemini-2.5-flash', 'gemini-2.5-pro'])
        url, request = session.calls[0]
        self.assertTrue(url.startswith('https://generativelanguage.googleapis.com/v1beta/models'))
        self.assertNotIn('secret-test-key', url)
        self.assertEqual(request['headers']['x-goog-api-key'], 'secret-test-key-12345')
        self.assertNotIn('json', request)
        self.assertFalse(request['allow_redirects'])

    def test_list_models_openai_compatible_and_ollama_cloud_filter(self):
        session = self.client(Response({'data': [{'id': 'b-model'}, {'id': 'a-model'}, {'id': 'a-model'}, {'nope': 1}]}))
        p = profile('openai-compatible', base_url='http://127.0.0.1:1234/v1/chat/completions')
        self.assertEqual(ai.list_models(p), ['a-model', 'b-model'])
        self.assertEqual(session.calls[0][0], 'http://127.0.0.1:1234/v1/models')
        self.assertFalse(session.trust_env)
        session = self.client(Response({'models': [{'name': 'qwen3:4b'}, {'name': 'gpt-oss:120b-cloud'}]}))
        self.assertEqual(ai.list_models(profile('ollama', key='', model='qwen3:4b')), ['qwen3:4b'])
        self.assertEqual(session.calls[0][0], 'http://127.0.0.1:11434/api/tags')
        self.assertNotIn('Authorization', session.calls[0][1]['headers'])

    def test_list_models_openrouter_keeps_free_models_only(self):
        self.client(Response({'data': [{'id': 'meta-llama/llama-3.3-70b-instruct:free'}, {'id': 'openai/gpt-4o'},
                                       {'id': 'openrouter/auto'}]}))
        p = profile('openrouter', base_url=ai.OPENROUTER_BASE_URL, model=ai.OPENROUTER_FREE_MODEL)
        self.assertEqual(ai.list_models(p), [ai.OPENROUTER_FREE_MODEL, 'meta-llama/llama-3.3-70b-instruct:free'])
        self.assertTrue(ai.validate_profile({**p, 'model': 'qwen/qwen3-8b:free'}))
        with self.assertRaises(ai.AIError): ai.validate_profile({**p, 'model': 'openai/gpt-4o'})

    def test_list_models_errors_are_safe(self):
        self.client(Response({'error': 'secret-test-key-12345 bad'}, status=401))
        with self.assertRaises(ai.AIError) as caught: ai.list_models(profile())
        self.assertIn('HTTP 401', str(caught.exception))
        self.assertNotIn('secret-test-key', str(caught.exception))
        self.client(Response(raw=b'not json'))
        with self.assertRaises(ai.AIError): ai.list_models(profile())
        self.client(requests.ConnectionError('secret-test-key-12345'))
        with self.assertRaises(ai.AIError) as caught: ai.list_models(profile())
        self.assertNotIn('secret-test-key', str(caught.exception))

    def test_local_openai_compatible_and_proxy_bypass(self):
        session = self.client(Response({'choices':[{'message':{'content':'local answer'}}]}))
        seen = []
        p = profile('openai-compatible', base_url='http://127.0.0.1:1234/v1')
        self.assertEqual(ai.chat(p, [{'role':'user','content':'hello'}], on_delta=seen.append), 'local answer')
        self.assertEqual(seen, ['local answer'])
        self.assertFalse(session.trust_env)
        url, request = session.calls[0]
        self.assertEqual(url, 'http://127.0.0.1:1234/v1/chat/completions')
        self.assertFalse(request['json']['stream'])
        self.assertEqual(request['headers']['Authorization'], 'Bearer secret-test-key-12345')

    def test_ollama_local_no_key_and_cloud_model_rejection(self):
        session = self.client(Response({'message':{'role':'assistant','content':'reply'}}))
        self.assertEqual(ai.chat(profile('ollama', key='', model='qwen3:4b'), [{'role':'user','content':'hello'}]), 'reply')
        url, request = session.calls[0]
        self.assertEqual(url, 'http://127.0.0.1:11434/api/chat')
        self.assertNotIn('Authorization', request['headers'])
        self.assertFalse(request['json']['stream'])
        with self.assertRaises(ai.AIError): ai.validate_profile(profile('ollama', model='model:cloud'))
        with self.assertRaises(ai.AIError): ai.validate_profile(profile('ollama', base_url='https://remote.example'))

    def test_unsafe_urls_never_request(self):
        session = self.client()
        for url in ['http://remote.example/v1','http://192.168.1.2:1234/v1', 'https://user:pass@api.example/v1',
                    'https://api.example/v1?key=secret','https://api.example/v1#fragment','file:///tmp/model',
                    'https://api.example\\@other.example','https://api.example/\nheader','https://api.example:99999']:
            with self.subTest(url=url), self.assertRaises(ai.AIError):
                ai.chat(profile(base_url=url), [{'role':'user','content':'text'}])
        self.assertEqual(session.calls, [])
        for url in ['http://localhost:1234/v1','http://127.0.0.1:1234/v1','http://[::1]:1234/v1','https://api.example/v1']:
            self.assertEqual(ai.validate_base_url(url), url)

    def test_redirect_and_provider_body_cannot_leak_key(self):
        session = self.client(Response({'error':'secret-test-key-12345'}, status=302, headers={'Location':'https://other.example'}))
        with self.assertRaises(ai.AIError) as error:
            ai.chat(profile(), [{'role':'user','content':'private transcript'}])
        self.assertEqual(len(session.calls), 1)
        self.assertNotIn('secret-test-key', str(error.exception))
        self.assertNotIn('private transcript', str(error.exception))

    def test_429_retry_bounded_and_timeout_not_retried(self):
        session = self.client(*[Response(status=429, headers={'Retry-After':'0'}) for _ in range(3)])
        with self.assertRaisesRegex(ai.AIError,'quota'): ai.chat(profile(), [{'role':'user','content':'text'}])
        self.assertEqual(len(session.calls), 3)
        session = self.client(requests.Timeout('secret-test-key-12345'))
        with self.assertRaises(ai.AIError) as error: ai.chat(profile(), [{'role':'user','content':'text'}])
        self.assertEqual(len(session.calls), 1)
        self.assertNotIn('secret-test-key', str(error.exception))

    def test_pre_cancel_and_input_bounds(self):
        cancel = threading.Event(); cancel.set()
        session = self.client()
        with self.assertRaises(ai.AICancelled): ai.chat(profile(), [{'role':'user','content':'text'}], cancel)
        with self.assertRaisesRegex(ai.AIError,'shorter selection'):
            ai.chat(profile(), [{'role':'user','content':'x'*(ai.MAX_CONTEXT_CHARS+1)}])
        self.assertEqual(session.calls, [])

    def test_key_echo_is_redacted(self):
        self.client(Response({'choices':[{'message':{'content':'Key: secret-test-key-12345'}}]}))
        self.assertEqual(ai.chat(profile('openai-compatible'), [{'role':'user','content':'text'}]), 'Key: [REDACTED]')

    def test_blocked_gemini_and_thought_exclusion(self):
        self.client(Response({'promptFeedback':{'blockReason':'SAFETY'}}))
        with self.assertRaisesRegex(ai.AIError,'blocked'): ai.chat(profile(), [{'role':'user','content':'text'}])
        self.client(Response({'candidates':[{'content':{'parts':[{'text':'internal','thought':True},{'text':'answer'}]}}]}))
        self.assertEqual(ai.chat(profile(), [{'role':'user','content':'text'}]), 'answer')

    def test_response_size_and_bad_json(self):
        self.client(Response(raw=b'x'*(ai.MAX_REPLY_BYTES+1)))
        with self.assertRaisesRegex(ai.AIError,'size limit'): ai.chat(profile(), [{'role':'user','content':'text'}])
        self.client(Response(raw=b'not json'))
        with self.assertRaisesRegex(ai.AIError,'invalid JSON'): ai.chat(profile(), [{'role':'user','content':'text'}])


if __name__ == '__main__': unittest.main()
