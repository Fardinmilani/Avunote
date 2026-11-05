"""Explicit, text-only AI requests. Importing or validating never uses network.

Call chat only after an explicit user Send action. This module does not read
audio, discover models, ping providers, or persist prompts/responses/credentials.
"""
from __future__ import annotations

from email.utils import parsedate_to_datetime
import ipaddress
import json
import re
import threading
import time
from urllib.parse import urlsplit, urlunsplit

import requests

PROVIDERS = ('gemini', 'openai-compatible', 'ollama')
MAX_CONTEXT_CHARS = 120_000
MAX_MESSAGES = 80
MAX_OUTPUT_TOKENS = 4096
DEFAULT_OUTPUT_TOKENS = 1024
MAX_REPLY_BYTES = 2_000_000
REQUEST_TIMEOUT = (10, 60)
DEFAULT_BASE_URLS = {
    'gemini': 'https://generativelanguage.googleapis.com/v1beta',
    'openai-compatible': 'https://api.openai.com/v1',
    'ollama': 'http://127.0.0.1:11434',
}


class AIError(ValueError):
    """Safe user-facing error; never contains provider bodies or credentials."""


class AICancelled(AIError):
    pass


def is_local_url(value):
    try:
        host = urlsplit(value).hostname
        if not host:
            return False
        if host.rstrip('.').lower() == 'localhost':
            return True
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_base_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise AIError('Enter a valid API base URL.')
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value:
        raise AIError('The API URL contains invalid characters.')
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError:
        raise AIError('Enter a valid API base URL.') from None
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise AIError('The API URL must contain a hostname and no embedded credentials.')
    if parsed.query or parsed.fragment:
        raise AIError('Use a base URL without query parameters, API keys or fragments.')
    if port is not None and not 1 <= port <= 65535:
        raise AIError('The API URL port is invalid.')
    if parsed.scheme not in {'https', 'http'}:
        raise AIError('Use HTTPS for remote APIs or HTTP for a loopback server.')
    normalized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip('/'), '', ''))
    if parsed.scheme == 'http' and not is_local_url(normalized):
        raise AIError('Remote APIs require HTTPS. HTTP is allowed only for localhost or loopback IP addresses.')
    return normalized


def validate_profile(profile):
    """Return normalized nonsecret request configuration; no network/DNS lookup."""
    if not isinstance(profile, dict):
        raise AIError('Invalid AI profile.')
    provider = profile.get('provider', '')
    if provider not in PROVIDERS:
        raise AIError('Choose Gemini, an OpenAI-compatible API, or local Ollama.')
    base_url = validate_base_url(profile.get('base_url') or DEFAULT_BASE_URLS[provider])
    model = profile.get('model', '')
    if not isinstance(model, str):
        raise AIError('Enter the provider model ID.')
    model = model.strip()
    if provider == 'gemini' and model.startswith('models/'):
        model = model[7:]
    pattern = r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}' if provider != 'gemini' else r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}'
    if not re.fullmatch(pattern, model):
        raise AIError('Enter a valid provider model ID (up to 200 characters).')
    if provider == 'ollama':
        if not is_local_url(base_url):
            raise AIError('The local Ollama profile requires a loopback server.')
        if model.lower().endswith((':cloud', '-cloud')):
            raise AIError('Choose an installed local Ollama model, not a cloud-routed model.')
    try:
        output_tokens = int(profile.get('max_output_tokens', DEFAULT_OUTPUT_TOKENS))
    except (ValueError, TypeError):
        raise AIError('The output token limit must be an integer.') from None
    if not 16 <= output_tokens <= MAX_OUTPUT_TOKENS:
        raise AIError(f'The output token limit must be between 16 and {MAX_OUTPUT_TOKENS}.')
    return {'provider': provider, 'base_url': base_url, 'model': model,
            'max_output_tokens': output_tokens, 'is_local': is_local_url(base_url)}


def _messages(values):
    if not isinstance(values, (list, tuple)) or not values or len(values) > MAX_MESSAGES:
        raise AIError(f'Send between 1 and {MAX_MESSAGES} conversation messages.')
    normalized = []
    count = 0
    for value in values:
        if not isinstance(value, dict) or value.get('role') not in {'system', 'user', 'assistant'}:
            raise AIError('Conversation messages must use system, user or assistant roles.')
        content = value.get('content')
        if not isinstance(content, str) or not content.strip():
            raise AIError('Conversation messages must contain nonempty text.')
        count += len(content)
        normalized.append({'role': value['role'], 'content': content})
    if count > MAX_CONTEXT_CHARS:
        raise AIError(f'This conversation exceeds {MAX_CONTEXT_CHARS:,} text characters. Start a new chat or explicitly send a shorter selection.')
    if normalized[-1]['role'] != 'user':
        raise AIError('The conversation must end with the new user message.')
    return normalized


def _endpoint(config):
    base = config['base_url']
    path = urlsplit(base).path
    if config['provider'] == 'gemini':
        if not path:
            base += '/v1beta'
        return base + '/models/' + config['model'] + ':generateContent'
    if config['provider'] == 'ollama':
        if path.endswith('/api/chat'):
            return base
        return base + ('/chat' if path.endswith('/api') else '/api/chat')
    if path.endswith('/chat/completions'):
        return base
    return base + ('/v1/chat/completions' if not path else '/chat/completions')


def _payload(config, messages):
    model = config['model']
    tokens = config['max_output_tokens']
    if config['provider'] == 'gemini':
        body = {'contents': [
            {'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [{'text': m['content']}]}
            for m in messages if m['role'] != 'system'
        ], 'generationConfig': {'maxOutputTokens': tokens}}
        instructions = [m['content'] for m in messages if m['role'] == 'system']
        if instructions:
            body['systemInstruction'] = {'parts': [{'text': '\n\n'.join(instructions)}]}
        return body
    if config['provider'] == 'ollama':
        return {'model': model, 'messages': messages, 'stream': False,
                'options': {'num_predict': tokens}}
    return {'model': model, 'messages': messages, 'stream': False, 'max_tokens': tokens}


def _reply(config, data):
    if not isinstance(data, dict):
        raise AIError('The provider returned an invalid response.')
    try:
        if config['provider'] == 'gemini':
            candidate = data.get('candidates', [])[0]
            reason = candidate.get('finishReason', '')
            if reason not in {'', 'STOP', 'MAX_TOKENS'}:
                raise AIError('Google blocked or stopped the response. Check its content policies or try a different prompt.')
            parts = candidate['content']['parts']
            result = ''.join(p['text'] for p in parts if isinstance(p, dict) and isinstance(p.get('text'), str) and not p.get('thought'))
        elif config['provider'] == 'ollama':
            result = data['message']['content']
        else:
            result = data['choices'][0]['message']['content']
            if isinstance(result, list):
                result = ''.join(p['text'] for p in result if isinstance(p, dict) and isinstance(p.get('text'), str))
    except (KeyError, IndexError, TypeError):
        raise AIError('The provider returned no text answer. The response may have been blocked or the model may require a different API.') from None
    if not isinstance(result, str) or not result.strip():
        raise AIError('The provider returned no text answer.')
    if len(result.encode('utf-8')) > MAX_REPLY_BYTES:
        raise AIError('The provider response exceeds the application size limit.')
    return result


def _retry_delay(headers, attempt):
    value = headers.get('Retry-After', '')
    try:
        delay = float(value)
    except (TypeError, ValueError):
        try:
            delay = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            delay = 2 ** attempt
    return max(0.0, min(delay, 30.0))


def chat(profile, messages, cancel_event=None, on_delta=None):
    """Send text only, on caller authorization, and return the final answer.

    Non-streaming by design. on_delta, if supplied, receives the final answer
    once. Cancellation is checked around HTTP waits; an already submitted remote
    request may still finish/bill at the provider. No retry on ambiguous network
    failures or server errors; only explicit HTTP 429 rejection is retried twice.
    """
    config = validate_profile(profile)
    history = _messages(messages)
    cancel = cancel_event or threading.Event()
    key = profile.get('key', '') or ''
    if not isinstance(key, str) or len(key) > 8192 or any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise AIError('The API key contains invalid characters.')
    if config['provider'] == 'gemini' and not key:
        raise AIError('Add your Google AI Studio API key to this profile.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if key:
        headers['x-goog-api-key' if config['provider'] == 'gemini' else 'Authorization'] = key if config['provider'] == 'gemini' else 'Bearer '+key
    payload = _payload(config, history)
    endpoint = _endpoint(config)
    with requests.Session() as session:
        if config['is_local']:
            session.trust_env = False  # Do not proxy local conversations/API keys.
        for attempt in range(3):
            if cancel.is_set():
                raise AICancelled('AI request cancelled.')
            try:
                response = session.post(endpoint, json=payload, headers=headers,
                                        timeout=REQUEST_TIMEOUT, allow_redirects=False, stream=True)
            except requests.Timeout:
                raise AIError('The AI provider timed out. The submitted request may still finish there; it was not retried.') from None
            except requests.RequestException:
                raise AIError('Could not reach the AI provider. Check the endpoint, connection or local server. The request was not retried.') from None
            if cancel.is_set():
                response.close()
                raise AICancelled('AI request cancelled. A submitted provider request may still finish.')
            status = response.status_code
            if status == 429:
                delay = _retry_delay(response.headers, attempt)
                response.close()
                if attempt == 2:
                    raise AIError('The provider rate limit or quota was reached. Check the project quota/billing or try again later.')
                if cancel.wait(delay):
                    raise AICancelled('AI request cancelled.')
                continue
            if status != 200:
                response.close()
                detail = {400: 'Check the model ID, context length and API compatibility.',
                          401: 'Check your API key.', 403: 'Check API access, region and project permissions.',
                          404: 'Check the endpoint and model ID; local models must already be installed.'}.get(status, 'Try again later or check the provider status.')
                raise AIError(f'AI provider HTTP {status}. {detail}')
            try:
                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    if cancel.is_set():
                        raise AICancelled('AI request cancelled.')
                    body.extend(chunk)
                    if len(body) > MAX_REPLY_BYTES:
                        raise AIError('The provider response exceeds the application size limit.')
                data = json.loads(body.decode('utf-8'))
            except (ValueError, UnicodeError) as exc:
                if isinstance(exc, AIError):
                    raise
                raise AIError('The provider returned invalid JSON.') from None
            except requests.RequestException:
                raise AIError('The AI response was interrupted. The submitted request was not retried.') from None
            finally:
                response.close()
            result = _reply(config, data)
            if key:
                result = result.replace(key, '[REDACTED]')
            if cancel.is_set():
                raise AICancelled('AI request cancelled.')
            if on_delta:
                on_delta(result)
            return result
    raise AIError('The AI request did not complete.')
