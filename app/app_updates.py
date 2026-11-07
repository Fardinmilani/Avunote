"""Release selection, verification and handoff for the Windows Setup updater."""
from __future__ import annotations

from dataclasses import dataclass
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

import requests


# Canonical public repository after the Voxriva → Avunote rename. GitHub still
# serves the old name; download URLs may keep /Voxriva/ and redirect.
REPOSITORY = 'Fardinmilani/Avunote'
REPOSITORY_ALIASES = (REPOSITORY, 'Fardinmilani/Voxriva')
GITHUB_PAGE_URL = f'https://github.com/{REPOSITORY}'
LATEST_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
MAX_INSTALLER_BYTES = 1_500_000_000
MAX_METADATA_BYTES = 2_000_000
MANIFEST_NAME = 'manifest.json'
MARKER_NAME = '.voxriva-install.ini'
PRODUCT = 'Voxriva-FardinMilani-x64'
_VERSION = r'(?:0|[1-9][0-9]{0,4})\.(?:0|[1-9][0-9]{0,4})\.(?:0|[1-9][0-9]{0,4})'
_HASH = r'[0-9a-f]{64}'
_DOWNLOAD_HOSTS = {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
_OWNED_ROOTS = {'app', 'assets', '_internal', 'docs', 'licenses', 'scripts'}
_OWNED_FILES = {'avunote.exe', 'license', 'third_party_notices.md', 'readme.md',
                'readme_fa.md', 'features_2_2.md'}


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    digest: str


@dataclass(frozen=True)
class Update:
    version: str
    setup: Asset
    delta: Asset | None = None


class UpdateCancelled(Exception):
    pass


def version_parts(text):
    if not isinstance(text, str) or not re.fullmatch(_VERSION, text):
        raise ValueError('Invalid release version.')
    parts = tuple(map(int, text.split('.')))
    if any(part > 65535 for part in parts):
        raise ValueError('Invalid release version.')
    return parts


def setup_name(version):
    return f'Avunote-{version}-Windows-x64-Setup.exe'


def delta_name(version, previous, baseline_hash):
    return f'Avunote-{version}-Windows-x64-Update-from-{previous}-{baseline_hash}.exe'


def running_version():
    # Embedded by the launcher for frozen builds. A file is used for local dev.
    if getattr(sys, 'frozen', False):
        path = Path(sys._MEIPASS) / 'VERSION'
    else:
        path = Path(__file__).resolve().parent.parent / 'VERSION'
    result = path.read_text(encoding='utf-8-sig').strip()
    version_parts(result)
    return result


def _reparse_point(path):
    stat = path.lstat()
    return path.is_symlink() or bool(getattr(stat, 'st_file_attributes', 0) & 0x400)


def install_root(current):
    """Only registered Setup installations are eligible for automatic handoff."""
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        return None
    root = Path(sys.executable).resolve().parent
    try:
        import winreg

        marker_path = root / MARKER_NAME
        if _reparse_point(marker_path):
            return None
        raw = _read_bytes(marker_path, 8192)
        marker = configparser.ConfigParser(interpolation=None)
        encoding = 'utf-16' if raw.startswith(b'\xff\xfe') else 'mbcs'
        marker.read_string(raw.decode(encoding))
        values = marker['Voxriva']
        if (values.get('Product') == PRODUCT and values.get('Version') == current
                and values.get('TestMode') == '0' and Path(values['InstallDir']).resolve() == root):
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Voxriva', 0,
                               winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                registered, value_type = winreg.QueryValueEx(key, 'InstallDir')
            if value_type == winreg.REG_SZ and Path(registered).resolve() == root:
                return root
    except (OSError, ValueError, KeyError, configparser.Error):
        pass
    return None


def _file_sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_manifest(raw):
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError('Release manifest is too large.')
    content = json.loads(raw)
    if not isinstance(content, dict) or content.get('schema') != 1:
        raise ValueError('Invalid release manifest.')
    version = content.get('version')
    version_parts(version)
    rows = content.get('files')
    if not isinstance(rows, list) or not rows or len(rows) > 12000:
        raise ValueError('Invalid release manifest.')
    result = {}
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid release manifest.')
        name = row.get('path')
        size = row.get('bytes')
        digest = row.get('sha256')
        if not isinstance(name, str) or len(name) > 230:
            raise ValueError('Invalid payload path.')
        parts = name.split('/')
        lower = [part.lower() for part in parts]
        if (not all(re.fullmatch(r'[A-Za-z0-9_. @()+,\-]+', part)
                    and not part.endswith((' ', '.'))
                    and not re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', part.split('.', 1)[0], re.I)
                    for part in parts)
                or (len(parts) == 1 and parts[0].lower() not in _OWNED_FILES)
                or (len(parts) > 1 and parts[0].lower() not in _OWNED_ROOTS)
                or lower[:2] == ['assets', 'models']
                or any(part in {'__pycache__', 'ai-chats', 'recordings', 'results'} for part in lower)):
            raise ValueError('Invalid payload path.')
        if (name.casefold() in seen or type(size) is not int or not 0 <= size <= MAX_INSTALLER_BYTES
                or not isinstance(digest, str) or not re.fullmatch(_HASH, digest)):
            raise ValueError('Invalid payload entry.')
        seen.add(name.casefold())
        result[name] = (size, digest)
    if 'Avunote.exe' not in result:
        raise ValueError('Release executable is missing from manifest.')
    return version, result


def _read_bytes(path, maximum):
    with path.open('rb') as stream:
        result = stream.read(maximum + 1)
    if len(result) > maximum:
        raise ValueError('File exceeds its expected size.')
    return result


def baseline_digest(root, current, *, verify_files=False):
    """Return a delta baseline fingerprint only for an intact matching payload."""
    if root is None:
        return None
    try:
        manifest = root / MANIFEST_NAME
        if _reparse_point(manifest):
            return None
        raw = _read_bytes(manifest, MAX_METADATA_BYTES)
        version, files = read_manifest(raw)
        if version != current:
            return None
        if verify_files:
            for name, (size, digest) in files.items():
                path = root / name
                if (path.resolve() != path or _reparse_point(path) or not path.is_file()
                        or path.stat().st_size != size or _file_sha256(path) != digest):
                    return None
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError):
        return None


def _release_download_url(url, tag, name):
    if not isinstance(url, str) or not isinstance(tag, str) or not isinstance(name, str):
        return False
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc.casefold() != 'github.com'
            or parts.query or parts.fragment or parts.username or parts.password):
        return False
    return any(parts.path.casefold() == f'/{repository}/releases/download/{tag}/{name}'.casefold()
               for repository in REPOSITORY_ALIASES)


def _trusted_github_latest(url):
    if not isinstance(url, str):
        return False
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc.casefold() != 'api.github.com'
            or parts.query or parts.fragment or parts.username or parts.password):
        return False
    path = parts.path
    if re.fullmatch(r'/repositories/[1-9][0-9]{0,15}/releases/latest', path):
        return True
    return any(path.casefold() == f'/repos/{repository}/releases/latest'.casefold()
               for repository in REPOSITORY_ALIASES)


def _asset(row, tag, expected):
    if not isinstance(row, dict) or row.get('name') != expected or row.get('state') != 'uploaded':
        return None
    url = row.get('browser_download_url')
    size = row.get('size')
    digest = row.get('digest')
    # Only use the digest from GitHub's authenticated release metadata.
    if (not _release_download_url(url, tag, expected)
            or type(size) is not int or not 0 < size <= MAX_INSTALLER_BYTES
            or not isinstance(digest, str) or not re.fullmatch('sha256:' + _HASH, digest)):
        return None
    return Asset(expected, url, size, digest[7:])


def parse_release(content, current, baseline=None):
    installed = version_parts(current)
    if not isinstance(content, dict) or content.get('draft') is not False or content.get('prerelease') is not False:
        return None
    tag = content.get('tag_name')
    if not isinstance(tag, str) or not re.fullmatch('v?' + _VERSION, tag):
        return None
    version = tag.removeprefix('v')
    if version_parts(version) <= installed:
        return None
    assets = content.get('assets')
    if not isinstance(assets, list) or len(assets) > 200:
        raise ValueError('Invalid GitHub release assets.')
    full_name = setup_name(version)
    small_name = delta_name(version, current, baseline) if baseline and re.fullmatch(_HASH, baseline) else None
    setup = next((item for row in assets if (item := _asset(row, tag, full_name))), None)
    if setup is None:
        raise ValueError('This release has no verified Windows Setup asset.')
    delta = next((item for row in assets if (item := _asset(row, tag, small_name))
                  and item.size < setup.size), None) if small_name else None
    return Update(version, setup, delta)


def _read_response(response, maximum):
    output = bytearray()
    deadline = time.monotonic() + 45
    for chunk in response.iter_content(65536):
        if time.monotonic() > deadline:
            raise TimeoutError('GitHub release metadata timed out.')
        output.extend(chunk)
        if len(output) > maximum:
            raise ValueError('GitHub response exceeds its allowed size.')
    return bytes(output)


def _fetch_latest_release(url):
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
               'User-Agent': 'Avunote Windows Updater'}
    for _ in range(5):
        with requests.get(url, headers=headers, timeout=(7, 12),
                          stream=True, allow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get('Location', '')
                if location.startswith('/'):
                    location = 'https://api.github.com' + location
                if not _trusted_github_latest(location):
                    raise ValueError('The GitHub release API redirected to an untrusted address.')
                url = location
                continue
            if response.status_code == 404:
                return None
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('Unexpected GitHub release response.')
            return json.loads(_read_response(response, MAX_METADATA_BYTES))
    raise ValueError('Too many redirects reading GitHub releases.')


def check_release(current, root=None):
    baseline = baseline_digest(root, current)
    content = None
    for repository in REPOSITORY_ALIASES:
        content = _fetch_latest_release(f'https://api.github.com/repos/{repository}/releases/latest')
        if content is not None:
            break
    if content is None:
        return None
    release = parse_release(content, current, baseline)
    if release and release.delta and baseline_digest(root, current, verify_files=True) != baseline:
        return Update(release.version, release.setup)
    return release


def _download_response(session, asset):
    url = asset.url
    for _ in range(5):
        response = session.get(url, timeout=(7, 12), stream=True, allow_redirects=False)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        try:
            url = response.headers.get('Location', '')
            parts = urlsplit(url)
            if (parts.scheme != 'https' or parts.netloc not in _DOWNLOAD_HOSTS or parts.fragment
                    or not parts.path.startswith('/')):
                raise ValueError('The release asset redirected to an untrusted address.')
        finally:
            response.close()
    raise ValueError('Too many redirects downloading the update.')


def _known_asset(asset):
    name = asset.name
    if not isinstance(name, str) or not re.fullmatch(
            rf'Avunote-{_VERSION}-Windows-x64-(?:Setup|Update-from-{_VERSION}-{_HASH})\.exe', name):
        return False
    parts = urlsplit(asset.url)
    aliases = '|'.join(re.escape(repository) for repository in REPOSITORY_ALIASES)
    return (parts.scheme == 'https' and parts.netloc == 'github.com' and not parts.query
            and not parts.fragment and bool(re.fullmatch(
                rf'/(?:{aliases})/releases/download/v?{_VERSION}/{re.escape(name)}', parts.path, re.I))
            and type(asset.size) is int and 0 < asset.size <= MAX_INSTALLER_BYTES
            and bool(re.fullmatch(_HASH, asset.digest)))


def stage_update(asset, folder, cancel, progress=lambda count, total: None):
    """Stream only an allowlisted release asset and publish the file after SHA-256 verification."""
    if not _known_asset(asset):
        raise ValueError('Untrusted update asset.')
    folder.mkdir(parents=True, exist_ok=True)
    if _reparse_point(folder):
        raise ValueError('Unsafe update download location.')
    target = folder / asset.name
    if target.exists() and not _reparse_point(target) and target.is_file():
        if target.stat().st_size == asset.size and _file_sha256(target) == asset.digest:
            return target
    if shutil.disk_usage(folder).free < asset.size + 32_000_000:
        raise OSError('Not enough free space for the update download.')
    received = 0
    sha = hashlib.sha256()
    deadline = time.monotonic() + 1800
    temporary = None
    try:
        with requests.Session() as session:
            session.headers.update({'User-Agent': 'Avunote Windows Updater', 'Accept-Encoding': 'identity'})
            with _download_response(session, asset) as response:
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError('Unexpected update download response.')
                with tempfile.NamedTemporaryFile(dir=folder, prefix='.avunote-', suffix='.part',
                                                 mode='wb', delete=False) as stream:
                    temporary = Path(stream.name)
                    for chunk in response.iter_content(256 * 1024):
                        if cancel.is_set():
                            raise UpdateCancelled()
                        if time.monotonic() > deadline:
                            raise TimeoutError('Update download timed out.')
                        received += len(chunk)
                        if received > asset.size:
                            raise ValueError('The update size does not match GitHub metadata.')
                        sha.update(chunk)
                        stream.write(chunk)
                        progress(received, asset.size)
        if cancel.is_set():
            raise UpdateCancelled()
        if received != asset.size or sha.hexdigest() != asset.digest:
            raise ValueError('The update failed SHA-256 verification.')
        os.replace(temporary, target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_staged(path, asset):
    return (path.name == asset.name and not _reparse_point(path) and path.is_file()
            and path.stat().st_size == asset.size and _file_sha256(path) == asset.digest)


def clean_staged_updates(folder, current):
    """Remove only Avunote's own completed, superseded downloads."""
    try:
        if not folder.is_dir() or _reparse_point(folder):
            return
        installed = version_parts(current)
        pattern = rf'Avunote-({_VERSION})-Windows-x64-(?:Setup|Update-from-{_VERSION}-{_HASH})\.exe'
        for path in folder.iterdir():
            match = re.fullmatch(pattern, path.name)
            if match and version_parts(match.group(1)) <= installed and not _reparse_point(path) and path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass  # The installer may still be completing its handoff.
    except (OSError, ValueError):
        pass


def launch_installer(path, root, current):
    # NSIS's /D= argument must be unquoted and last, even for paths with spaces.
    version_parts(current)
    if not root.is_absolute() or any(char in str(root) for char in ('"', '\r', '\n', '/')):
        raise ValueError('Invalid installation directory.')
    prefix = subprocess.list2cmdline([str(path), '/S', '/AVUNOTEUPDATE',
                                     f'/WAITPID={os.getpid()}', f'/FROMVERSION={current}'])
    subprocess.Popen(prefix + ' /D=' + str(root), executable=str(path), cwd=str(path.parent),
                     close_fds=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
