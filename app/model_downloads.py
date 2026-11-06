"""Explicit, resumable, verified Hugging Face downloads. Never transfers audio."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import threading
import time
from urllib.parse import quote, urlparse

import requests

from model_catalog import get_model, model_dir, find_local_model, _safe_file


class _Stopped(Exception):
    pass


def _atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def _validate_url(url):
    value = urlparse(url)
    hostname = (value.hostname or '').lower()
    if value.scheme != 'https' or value.username or value.password or not (
            hostname == 'huggingface.co' or hostname.endswith('.huggingface.co')
            or hostname == 'hf.co' or hostname.endswith('.hf.co')):
        raise ValueError('Download host is outside the approved Hugging Face service')


def _request(session, url, **kwargs):
    # Validate *before* each hop rather than following an arbitrary Location first.
    from urllib.parse import urljoin
    for _ in range(8):
        _validate_url(url)
        response = session.get(url, allow_redirects=False, timeout=(8, 8), **kwargs)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location')
            response.close()
            if not location:
                raise ValueError('Redirect missing destination')
            url = urljoin(url, location)
            continue
        return response
    raise ValueError('Too many download redirects')


def _resolve_artifacts(model, session):
    revision = model['revision']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Model revision must be an immutable commit')
    if 'artifacts' in model:
        artifacts = [dict(item) for item in model['artifacts']]
    else:
        url = f'https://huggingface.co/api/models/{model["repo"]}/revision/{revision}?blobs=true'
        with _request(session, url) as response:
            response.raise_for_status()
            payload = response.json()
        if payload.get('sha') != revision or payload.get('id') != model['repo']:
            raise ValueError('Repository revision did not match the pinned catalog')
        siblings = {item['rfilename']: item for item in payload.get('siblings', [])}
        artifacts = []
        for name in model['files']:
            relative = f'{model["subfolder"]}/{name}' if model['subfolder'] else name
            item = siblings.get(relative)
            if not item:
                raise ValueError('A required model file is missing from the repository')
            artifact = {'name': name, 'size': item['size']}
            lfs = item.get('lfs') or {}
            if lfs.get('sha256'):
                artifact['sha256'] = lfs['sha256']
            elif item.get('blobId'):
                artifact['git_sha1'] = item['blobId']
            else:
                raise ValueError('No integrity hash for required model file')
            artifacts.append(artifact)
    if {item['name'] for item in artifacts} != set(model['files']) or len(artifacts) != len(model['files']):
        raise ValueError('Required-file manifest does not match the catalog')
    for item in artifacts:
        _safe_file(item['name'])
        if not isinstance(item['size'], int) or not 0 < item['size'] < 20_000_000_000:
            raise ValueError('Invalid model file size')
        name = 'sha256' if 'sha256' in item else 'git_sha1'
        length = 64 if name == 'sha256' else 40
        if not re.fullmatch(f'[0-9a-f]{{{length}}}', item.get(name, '')):
            raise ValueError('Invalid integrity hash')
        # Some published models put tokenizer assets in a nested repository
        # folder; the local cache retains the existing flat and safe filenames.
        prefix = item.get('remote_prefix')
        if prefix is not None:
            _safe_file(prefix)
        relative = '/'.join(filter(None, [model['subfolder'], prefix, item['name']]))
        item['url'] = f'https://huggingface.co/{model["repo"]}/resolve/{revision}/{quote(relative)}?download=true'
    return artifacts


def _matches(path, artifact, checkpoint=None):
    if not path.is_file() or path.stat().st_size != artifact['size']:
        return False
    name = 'sha256' if artifact.get('sha256') else 'sha1'
    digest = hashlib.new(name)
    if name == 'sha1':
        digest.update(f'blob {artifact["size"]}\0'.encode())
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if checkpoint:
                checkpoint()
            digest.update(block)
    return digest.hexdigest() == artifact.get('sha256', artifact.get('git_sha1'))


def _provenance(model):
    """Model-specific terms, never inherited from the application's MIT license."""
    fields = ['repo', 'revision', 'license', 'license_url', 'attribution', 'model_license_basis']
    if any(not isinstance(model.get(field), str) or not model[field].strip() for field in fields):
        raise ValueError('Model catalog must explicitly specify its own license and attribution')
    return {**{field: model[field] for field in fields}, 'source_url': model['url']}


class DownloadManager:
    """One active transfer at a time; independent resumable state per model.

    All state can be polled from a UI thread. No worker mutates UI widgets.
    close() pauses the current download and keeps partial bytes for next launch.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._states = {}
        self._thread = None
        self._active = None
        self._stop = threading.Event()
        self._cancel = False
        self._last_save = 0.0

    def _state(self, key):
        if key not in self._states:
            model = get_model(key)
            value = {'status': 'idle', 'bytes_done': 0, 'bytes_total': model['bytes'],
                     'speed_bps': 0.0, 'eta_seconds': None, 'error': '', 'file': ''}
            try:
                saved = json.loads((model_dir(key)/'download-state.json').read_text(encoding='utf-8'))
                for name in value:
                    if name in saved:
                        value[name] = saved[name]
                if value['status'] in {'resolving', 'downloading', 'verifying'}:
                    value['status'] = 'paused'
                value['speed_bps'] = 0.0
                value['eta_seconds'] = None
            except (OSError, ValueError, TypeError):
                pass
            self._states[key] = value
        return self._states[key]

    def snapshot(self, key):
        with self._lock:
            return dict(self._state(key))

    def active_key(self):
        with self._lock:
            return self._active if self._thread and self._thread.is_alive() else None

    def _update(self, key, force=False, **values):
        with self._lock:
            state = self._state(key)
            state.update(values)
            now = time.monotonic()
            if force or now-self._last_save >= .5:
                try:
                    folder = model_dir(key)
                    folder.mkdir(parents=True, exist_ok=True)
                    _atomic_json(folder/'download-state.json', state)
                    state.pop('persistence_error', None)
                except OSError as exc:
                    # Progress persistence is best effort; final completed.json is not.
                    # Keep the in-memory error/state visible even if a full disk also
                    # prevents writing the failure report itself.
                    state['persistence_error'] = f'{type(exc).__name__}: {exc}'
                self._last_save = now

    def start(self, key):
        get_model(key)
        with self._lock:
            if self._thread and self._thread.is_alive():
                if self._active == key:
                    return
                raise RuntimeError('ابتدا دانلود فعال را متوقف کنید؛ هر بار یک مدل دانلود می‌شود.')
            if find_local_model(key):
                self._update(key, force=True, status='completed', bytes_done=get_model(key)['bytes'], error='')
                return
            self._active = key
            self._stop = threading.Event()
            self._cancel = False
            self._update(key, force=True, status='resolving', error='', speed_bps=0.0, eta_seconds=None)
            self._thread = threading.Thread(target=self._run, args=(key,), daemon=True, name='model-download')
            self._thread.start()

    def pause(self, key):
        with self._lock:
            if self._active == key and self._thread and self._thread.is_alive():
                self._stop.set()

    def resume(self, key):
        self.start(key)

    def cancel(self, key):
        with self._lock:
            if self._active == key and self._thread and self._thread.is_alive():
                self._cancel = True
                self._stop.set()
            else:
                self._remove_parts(key)
                self._update(key, force=True, status='cancelled', speed_bps=0.0, eta_seconds=None, error='')

    def _remove_parts(self, key):
        folder = model_dir(key).resolve()
        # Never recurse, remove a model directory, touch registered roots, or delete ready files.
        for name in get_model(key)['files']:
            path = folder/(_safe_file(name)+'.part')
            if path.parent.resolve() == folder and not path.is_symlink():
                path.unlink(missing_ok=True)
        for name in ['transfer.json', 'completed.json.tmp']:
            path = folder/name
            if path.parent.resolve() == folder and not path.is_symlink():
                path.unlink(missing_ok=True)

    def _prepare_manifest(self, key, folder, artifacts):
        model = get_model(key)
        expected = {'repo': model['repo'], 'revision': model['revision'],
                    'files': [{k: v for k, v in item.items() if k != 'url'} for item in artifacts]}
        path = folder/'download-manifest.json'
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            saved = None
        # Never append bytes saved for a different catalog revision or artifact hash.
        if saved is not None and saved != expected:
            self._remove_parts(key)
        _atomic_json(path, expected)

    def _checkpoint(self):
        if self._stop.is_set():
            raise _Stopped()

    def _run(self, key):
        session = requests.Session()
        session.headers['User-Agent'] = 'Avunote/2.2 (model downloader; no audio transfer)'
        try:
            model = get_model(key)
            folder = model_dir(key)
            folder.mkdir(parents=True, exist_ok=True)
            artifacts = _resolve_artifacts(model, session)
            self._checkpoint()
            self._prepare_manifest(key, folder, artifacts)
            total = sum(item['size'] for item in artifacts)
            self._update(key, force=True, status='verifying', bytes_total=total)
            verified_existing = {x['name'] for x in artifacts if _matches(folder/x['name'], x, self._checkpoint)}
            available = sum(min((folder/(x['name']+'.part')).stat().st_size, x['size'])
                            for x in artifacts if (folder/(x['name']+'.part')).is_file())
            available += sum(x['size'] for x in artifacts if x['name'] in verified_existing)
            if shutil.disk_usage(folder).free < max(0, total-available) + 64*1024*1024:
                raise OSError('فضای آزاد دیسک برای مدل کافی نیست.')
            self._update(key, force=True, bytes_total=total)
            finished = 0
            for artifact in artifacts:
                self._checkpoint()
                target = folder/artifact['name']
                if artifact['name'] in verified_existing:
                    finished += artifact['size']
                    self._update(key, bytes_done=finished)
                    continue
                self._transfer(key, artifact, folder, session, finished)
                self._update(key, force=True, status='verifying', file=artifact['name'], speed_bps=0.0, eta_seconds=None)
                partial = folder/(artifact['name']+'.part')
                if not _matches(partial, artifact, self._checkpoint):
                    partial.unlink(missing_ok=True)
                    raise ValueError('هش فایل دانلودشده معتبر نیست؛ دانلود آن فایل را دوباره آغاز کنید.')
                self._checkpoint()
                os.replace(partial, target)
                finished += artifact['size']
            self._checkpoint()
            provenance = _provenance(model)
            _atomic_json(folder/'model-source.json', provenance)
            marker = {**provenance, 'files': [{k: v for k, v in item.items() if k != 'url'} for item in artifacts]}
            _atomic_json(folder/'completed.json', marker)
            self._update(key, force=True, status='completed', bytes_done=total, bytes_total=total,
                         speed_bps=0.0, eta_seconds=0, error='', file='')
        except _Stopped:
            if self._cancel:
                self._remove_parts(key)
            self._update(key, force=True, status='cancelled' if self._cancel else 'paused',
                         speed_bps=0.0, eta_seconds=None, error='')
        except Exception as exc:
            self._update(key, force=True, status='error', error=f'{type(exc).__name__}: {exc}',
                         speed_bps=0.0, eta_seconds=None)
        finally:
            session.close()

    def _transfer(self, key, artifact, folder, session, finished):
        partial = folder/(artifact['name']+'.part')
        identity = folder/'transfer.json'
        for attempt in range(4):
            self._checkpoint()
            offset = partial.stat().st_size if partial.is_file() else 0
            if offset > artifact['size']:
                partial.unlink()
                offset = 0
            if offset == artifact['size']:
                return
            headers = {}
            if offset:
                headers['Range'] = f'bytes={offset}-'
                try:
                    saved = json.loads(identity.read_text(encoding='utf-8'))
                    if saved.get('file') == artifact['name'] and saved.get('revision') == get_model(key)['revision'] and saved.get('etag'):
                        headers['If-Range'] = saved['etag']
                except (OSError, ValueError):
                    pass
            try:
                with _request(session, artifact['url'], headers=headers, stream=True) as response:
                    if response.status_code == 416:
                        # Complete files are handled above; a stale range is safely restarted.
                        partial.unlink(missing_ok=True)
                        continue
                    response.raise_for_status()
                    if response.status_code == 206:
                        content_range = response.headers.get('Content-Range', '')
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', content_range)
                        if not match or int(match[1]) != offset or int(match[3]) != artifact['size']:
                            raise ValueError('Invalid Content-Range from model server')
                        mode = 'ab'
                    elif response.status_code == 200:
                        offset = 0  # Server ignored Range or If-Range changed: never append.
                        mode = 'wb'
                    else:
                        raise ValueError('Unexpected model server response')
                    _atomic_json(identity, {'file': artifact['name'], 'etag': response.headers.get('ETag'),
                                           'revision': get_model(key)['revision']})
                    started, initial = time.monotonic(), offset
                    self._update(key, force=True, status='downloading', file=artifact['name'], bytes_done=finished+offset)
                    with partial.open(mode) as stream:
                        for chunk in response.iter_content(chunk_size=64*1024):
                            self._checkpoint()
                            if not chunk:
                                continue
                            if offset+len(chunk) > artifact['size']:
                                raise ValueError('Model response exceeds declared size')
                            stream.write(chunk)
                            offset += len(chunk)
                            elapsed = max(.01, time.monotonic()-started)
                            speed = (offset-initial)/elapsed
                            done = finished+offset
                            left = max(0, self._state(key)['bytes_total']-done)
                            self._update(key, bytes_done=done, speed_bps=speed,
                                         eta_seconds=left/speed if speed > 0 else None)
                    if offset != artifact['size']:
                        raise requests.ConnectionError('Incomplete model response')
                    return
            except (requests.RequestException, OSError):
                self._checkpoint()
                if attempt == 3:
                    raise
                self._stop.wait(min(4, .5 * 2**attempt))
        raise requests.ConnectionError('Model download did not finish')

    def close(self):
        with self._lock:
            self._stop.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=12)
        return not (thread and thread.is_alive())
