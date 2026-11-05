"""Per-user AI profile metadata and opt-in Windows DPAPI secret storage.

No plaintext API key is written to disk. Other platforms keep keys in process
memory only. Listing profiles never decrypts or exposes a key.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import sys
import threading
import uuid

from ai_clients import AIError, PROVIDERS, validate_profile
from model_catalog import data_root

_LOCK = threading.RLock()
_SESSION_KEYS = {}
_ENTROPY = b'Voxriva.AIProfiles.DPAPI.v1'
_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,80}')


class SecretStorageError(AIError):
    pass


def persistent_keys_available():
    return sys.platform == 'win32'


class _Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]


def _blob(value):
    buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    return _Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _dpapi(value, decrypt=False):
    if not persistent_keys_available():
        raise SecretStorageError('Persistent API-key storage requires Windows DPAPI. This key can be used for this session only.')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    source, source_buffer = _blob(value)
    entropy, entropy_buffer = _blob(_ENTROPY)
    result = _Blob()
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.POINTER(_Blob),
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, ctypes.byref(entropy), None, None, 1, ctypes.byref(result)):
        raise SecretStorageError('Windows could not access the protected API key. Re-enter it in this Windows user account.')
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel.LocalFree(ctypes.cast(result.pbData, ctypes.c_void_p))


def _protect(key):
    return 'dpapi-v1:'+base64.b64encode(_dpapi(key.encode('utf-8'))).decode('ascii')


def _unprotect(value):
    try:
        if not value.startswith('dpapi-v1:'):
            raise ValueError('Unknown secret format')
        return _dpapi(base64.b64decode(value[9:], validate=True), decrypt=True).decode('utf-8')
    except (ValueError, UnicodeError, TypeError):
        raise SecretStorageError('The protected API key cannot be read. Re-enter it instead of copying another user\'s key file.') from None


def _path():
    return data_root()/'ai-profiles.json'


def _read():
    path = _path()
    if not path.exists():
        return []
    try:
        if path.stat().st_size > 1_000_000:
            raise ValueError('Oversized profile file')
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('profiles'), list):
            raise ValueError('Invalid profile file')
        profiles = data['profiles']
        if len(profiles) > 100 or any(not isinstance(x, dict) or not _ID_PATTERN.fullmatch(x.get('id', '')) for x in profiles):
            raise ValueError('Invalid profile records')
        return profiles
    except (OSError, ValueError, TypeError, AttributeError):
        raise AIError('The AI profile file cannot be read. Keep a backup before repairing or removing it.') from None


def _write(profiles):
    path = _path()
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps({'version': 1, 'profiles': profiles}, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, path)
    except OSError:
        raise AIError('The AI profile settings could not be saved. Check free space and folder permissions.') from None
    finally:
        if temporary.exists():
            temporary.unlink()


def _public(profile):
    profile_id = profile['id']
    encrypted = bool(profile.get('key_ciphertext'))
    session = bool(_SESSION_KEYS.get(profile_id))
    result = {key: profile.get(key) for key in ['id', 'name', 'provider', 'base_url', 'model', 'max_output_tokens']}
    result.update({'store_key': encrypted, 'has_key': encrypted or session,
                   'key_storage': 'windows-dpapi' if encrypted else 'session' if session else 'none',
                   'storage_notice': '' if persistent_keys_available() else 'This platform keeps API keys in memory for this session only.'})
    return result


def list_profiles():
    with _LOCK:
        return [_public(profile) for profile in _read()]


def get_profile(profile_id, include_secret=True):
    with _LOCK:
        for profile in _read():
            if profile['id'] == profile_id:
                result = _public(profile)
                if include_secret:
                    key = _SESSION_KEYS.get(profile_id, '')
                    if not key and profile.get('key_ciphertext'):
                        key = _unprotect(profile['key_ciphertext'])
                    result['key'] = key
                return result
    raise AIError('The AI profile no longer exists.')


def save_profile(value):
    if not isinstance(value, dict):
        raise AIError('Invalid AI profile.')
    normalized = validate_profile(value)
    name = value.get('name', '')
    if not isinstance(name, str) or not name.strip() or len(name) > 100:
        raise AIError('Give the profile a name of up to 100 characters.')
    key = value.get('key', '') or ''
    if not isinstance(key, str) or len(key) > 8192 or any(ord(c) < 32 or ord(c) == 127 for c in key):
        raise AIError('The API key contains invalid characters.')
    if key and any(key in str(x) for x in [name, normalized['base_url'], normalized['model']]):
        raise AIError('Keep the API key only in the password field, not in profile metadata.')
    profile_id = value.get('id') or uuid.uuid4().hex
    if not isinstance(profile_id, str) or not _ID_PATTERN.fullmatch(profile_id):
        raise AIError('Invalid AI profile ID.')
    with _LOCK:
        profiles = _read()
        existing = next((x for x in profiles if x['id'] == profile_id), None)
        same_connection = existing and all(existing.get(field) == normalized[field] for field in ['provider', 'base_url'])
        if same_connection and not key and not value.get('clear_key'):
            key = get_profile(profile_id, include_secret=True)['key']
        if value.get('clear_key'):
            key = ''
        if key and any(key in str(x) for x in [name, normalized['base_url'], normalized['model']]):
            raise AIError('Keep the API key only in the password field, not in profile metadata.')
        store_key = bool(value.get('store_key', False)) and persistent_keys_available()
        profile = {field: normalized[field] for field in ['provider', 'base_url', 'model', 'max_output_tokens']}
        profile.update({'id': profile_id, 'name': name.strip(), 'key_ciphertext': _protect(key) if key and store_key else ''})
        if existing:
            profiles[profiles.index(existing)] = profile
        else:
            if len(profiles) >= 100:
                raise AIError('At most 100 AI profiles can be saved.')
            profiles.append(profile)
        _write(profiles)
        if key:
            _SESSION_KEYS[profile_id] = key
        else:
            _SESSION_KEYS.pop(profile_id, None)
        return profile_id


def delete_profile(profile_id):
    with _LOCK:
        profiles = _read()
        kept = [profile for profile in profiles if profile['id'] != profile_id]
        if len(kept) == len(profiles):
            raise AIError('The AI profile no longer exists.')
        _write(kept)
        _SESSION_KEYS.pop(profile_id, None)
