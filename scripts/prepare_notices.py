"""Collect installed-package notices and verified corresponding library sources.

No model weights or audio are read, copied, or downloaded. Network is used only
when a pinned library-source archive is absent from the optional source cache.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
QT_SOURCE = 'https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/'
PYSIDE_SOURCE = 'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/'
SOURCES = [
    ('qtbase-everywhere-src-6.12.0.tar.xz', QT_SOURCE, 'a951bd163c7b80fc6b8c88d7668fb56abf91c152373e13c10666763238131307'),
    ('qtsvg-everywhere-src-6.12.0.tar.xz', QT_SOURCE, 'e4ab39534ec97987b1b9b60ef7f4d3253d5912a69f8c713a01753174a4029331'),
    ('qtimageformats-everywhere-src-6.12.0.tar.xz', QT_SOURCE, '0943132b5db8de6b6a7f1d162682173e8763c7ed94e80fd39113292845f67762'),
    ('pyside-setup-everywhere-src-6.12.0.tar.xz', PYSIDE_SOURCE, '099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751'),
    ('ffmpeg-7.1.tar.xz', 'https://ffmpeg.org/releases/', '40973d44970dbc83ef302b0609f2e74982be2d85916dd2ee7472d30678a7abe6'),
]
INTEL_PACKAGE = 'intelopenmp.redist.win.2025.3.0.640.nupkg'
INTEL_BASE = 'https://api.nuget.org/v3-flatcontainer/intelopenmp.redist.win/2025.3.0.640/'
INTEL_PACKAGE_SHA256 = 'a4212c4aec3e528864d56d8b0c87103cd5c21a888d1985124909a1f85624a449'
INTEL_DLL_SHA256 = '982233366b0afcda1e0f55a0b134097e35b779613f54ddb69e685e6cd06b755f'


def provide_intel_runtime(release, licenses, cache, offline):
    """Use the designated NuGet redistributable, not another channel's license.

    The whole NuGet archive remains in the build cache, outside the release.
    Only its unmodified x64 DLL, publisher notices and provenance are shipped.
    """
    build_cache = PROJECT/'build/source-downloads'
    build_cache.mkdir(parents=True, exist_ok=True)
    package = provide_source(INTEL_PACKAGE, INTEL_BASE, INTEL_PACKAGE_SHA256,
                             build_cache, cache, offline)
    notice_folder = licenses/'AppAndModelNotices/Intel-OpenMP-Redistributable-2025.3.0.640'
    notice_folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        runtime = archive.read('runtimes/win-x64/native/libiomp5md.dll')
        if hashlib.sha256(runtime).hexdigest() != INTEL_DLL_SHA256:
            raise RuntimeError('Intel official redistributable DLL hash mismatch')
        license_text = archive.read('license.txt')
        if b'Intel Simplified Software License (Version October 2022)' not in license_text:
            raise RuntimeError('Unexpected Intel redistributable license')
        (notice_folder/'LICENSE.txt').write_bytes(license_text)
        (notice_folder/'third-party-programs.txt').write_bytes(
            archive.read('share/doc/compiler/licensing/openmp/third-party-programs.txt'))
        (notice_folder/'intelopenmp.redist.win.nuspec').write_bytes(archive.read('intelopenmp.redist.win.nuspec'))
    replaced = []
    for path in release.rglob('libiomp5md.dll'):
        path.write_bytes(runtime)
        replaced.append(path.relative_to(release).as_posix())
    provenance = {
        'publisher': 'Intel Corporation', 'package': INTEL_PACKAGE,
        'package_url': INTEL_BASE+INTEL_PACKAGE, 'package_sha256': INTEL_PACKAGE_SHA256,
        'dll': 'runtimes/win-x64/native/libiomp5md.dll',
        'dll_sha256': INTEL_DLL_SHA256, 'dll_bytes': len(runtime),
        'license': 'Intel Simplified Software License, October 2022',
        'redistributable_designation': 'Official Intel runtime redistributable NuGet package',
        'official_documentation': 'https://www.intel.com/content/www/us/en/developer/articles/guide/installing-performance-libraries-using-nuget.html',
        'release_copies_replaced': replaced,
    }
    (notice_folder/'PROVENANCE.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(f'Official Intel redistributable verified; release DLL copies prepared: {len(replaced)}', flush=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def provide_source(name, base_url, expected, destination, cache, offline):
    target = destination/name
    if target.is_file() and digest(target) == expected:
        return target
    cached = cache/name if cache else None
    if cached and cached.is_file():
        if digest(cached) != expected:
            raise RuntimeError(f'Source cache SHA-256 mismatch: {name}')
        shutil.copy2(cached, target)
        return target
    if offline:
        raise RuntimeError(f'Matching source archive missing in offline mode: {name}')
    print(f'Downloading library source: {name}', flush=True)
    temporary = target.with_suffix(target.suffix+'.part')
    request = urllib.request.Request(base_url+name, headers={'User-Agent': 'Voxriva-source-builder/2'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output, length=1024*1024)
        if digest(temporary) != expected:
            raise RuntimeError(f'Downloaded source SHA-256 mismatch: {name}')
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target


def extract_license_texts(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        for member in tar:
            name = Path(member.name).name
            wanted = '/LICENSES/' in member.name or name.upper().startswith(('COPYING', 'LICENSE', 'LICENCE', 'NOTICE'))
            if member.isfile() and wanted and member.size <= 2_000_000:
                stream = tar.extractfile(member)
                if stream is not None:
                    safe_name = hashlib.sha256(member.name.encode()).hexdigest()[:12]+'-'+name[:45]
                    (destination/safe_name).write_bytes(stream.read())


def copy_package_notices(destination):
    rows = []
    for dist in metadata.distributions():
        name = dist.metadata.get('Name') or 'unnamed'
        safe_package = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)
        target = destination/'Packages'/safe_package
        rows.append({'name': name, 'version': dist.version,
                     'license': dist.metadata.get('License-Expression') or dist.metadata.get('License', '')})
        for file in dist.files or []:
            relative = Path(str(file))
            if not any(key in relative.name.upper() for key in ['LICENSE', 'LICENCE', 'COPYING', 'NOTICE']):
                continue
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size <= 5_000_000:
                target.mkdir(parents=True, exist_ok=True)
                safe_name = hashlib.sha256(str(relative).encode()).hexdigest()[:12]+'-'+relative.name[:45]
                shutil.copy2(source, target/safe_name)
    (destination/'package-licenses.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path, default=PROJECT/'dist/Voxriva')
    parser.add_argument('--source-cache', type=Path, default=os.environ.get('AZB_SOURCE_CACHE'))
    parser.add_argument('--package-path', type=Path, action='append', default=[])
    parser.add_argument('--offline', action='store_true', help='Require verified source archives in cache; never use network')
    args = parser.parse_args()
    for path in reversed(args.package_path):
        sys.path.insert(0, str(path))
    if metadata.version('PySide6-Essentials') != '6.12.0' or metadata.version('shiboken6') != '6.12.0':
        raise RuntimeError('Source archive pins require PySide6-Essentials and shiboken6 exactly 6.12.0')
    ffmpeg = PROJECT/'vendor/ffmpeg.exe'
    notice = subprocess.check_output([str(ffmpeg), '-L'], stderr=subprocess.STDOUT, text=True, timeout=30)
    normalized = ' '.join(notice.split())
    if 'GNU Lesser General Public License' not in normalized or not all(flag in notice for flag in ['--disable-gpl', '--disable-version3', '--disable-network']):
        raise RuntimeError('vendor/ffmpeg.exe is not the expected LGPL audio-only configuration')
    licenses = args.release/'Licenses'
    sources = licenses/'Sources'
    cache = Path(args.source_cache) if args.source_cache else None
    sources.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PROJECT/'licenses', licenses/'AppAndModelNotices', dirs_exist_ok=True)
    for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
        shutil.copy2(PROJECT/name, licenses/name)
    copy_package_notices(licenses)
    provide_intel_runtime(args.release, licenses, cache, args.offline)
    for filename in ['LICENSE.txt', 'LICENSE']:
        python_license = Path(sys.base_prefix)/filename
        if python_license.exists():
            shutil.copy2(python_license, licenses/'Python-LICENSE.txt')
            break
    else:
        raise RuntimeError('Python interpreter license file missing; supply the matching PSF notice before distribution')
    manifest = []
    for name, url, expected in SOURCES:
        path = provide_source(name, url, expected, sources, cache, args.offline)
        extract_license_texts(path, licenses/'SourceLicenseTexts'/name.split('-')[0])
        manifest.append({'file': name, 'url': url+name, 'sha256': expected, 'bytes': path.stat().st_size})
    (sources/'source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (licenses/'FFmpeg-NOTICE.txt').write_text(notice, encoding='utf-8')
    matching_build = PROJECT/'vendor/FFmpeg-source'
    if matching_build.is_dir():
        shutil.copytree(matching_build, sources/'FFmpeg-build', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('*.exe', '*.dll', '*.o', '*.obj', '*.a', '*.lib', '*.tar.xz'))
    elif cache and (cache/'FFmpeg-build').is_dir():
        shutil.copytree(cache/'FFmpeg-build', sources/'FFmpeg-build', dirs_exist_ok=True)
    else:
        raise RuntimeError('Matching FFmpeg build information missing: use vendor/FFmpeg-source or cached FFmpeg-build')
    vendor_script = PROJECT/'vendor/build_ffmpeg.sh'
    if vendor_script.exists():
        shutil.copy2(vendor_script, sources/'FFmpeg-build/reference-zig-build.sh')
    workflow = PROJECT/'.github/workflows/windows.yml'
    if workflow.exists():
        shutil.copy2(workflow, sources/'FFmpeg-build/CI-windows.yml')
    print(f'Matching sources and third-party notices prepared: {licenses}', flush=True)


if __name__ == '__main__':
    main()
