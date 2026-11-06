"""Exercise a built Windows Setup in an isolated workspace (no registration).

Use --legacy-setup to verify an in-place upgrade from an earlier Avunote or Voxriva Setup.
The /TESTMODE switch skips registry writes and desktop/Start-menu shortcuts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', type=Path)
    parser.add_argument('--legacy-setup', type=Path)
    parser.add_argument('--report', type=Path, default=root/'.local/setup-validation.json')
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This verification runs only on Windows.')
    version = (root/'VERSION').read_text(encoding='utf-8').strip()
    setup = (args.setup or root/f'release/Avunote-{version}-Windows-x64-Setup.exe').resolve()
    digest = hashlib.file_digest(setup.open('rb'), 'sha256').hexdigest()
    assert setup.with_name(setup.name+'.sha256.txt').read_text(encoding='utf-8').split()[0] == digest
    local = (root/'.local').resolve()
    local.mkdir(exist_ok=True)
    report = {'version': version, 'setup': str(setup), 'setup_bytes': setup.stat().st_size,
              'setup_sha256': digest}
    with tempfile.TemporaryDirectory(prefix='setup-smoke-', dir=local) as temporary:
        fixture = Path(temporary).resolve()
        assert fixture.is_relative_to(local)
        target = fixture/'installed app'
        profile = fixture/'profile'
        profile.mkdir()
        private_sentinel = profile/'keep-private-history.txt'
        private_sentinel.write_text('Existing local history must survive.', encoding='utf-8')
        env = dict(os.environ)
        env.update(VOXRIVA_DATA_DIR=str(profile), AVUNOTE_DATA_DIR=str(profile),
                   VOXRIVA_SUPPRESS_PROMPTS='1', AVUNOTE_SUPPRESS_PROMPTS='1',
                   PATH=os.pathsep.join([str(Path(os.environ['WINDIR'])/'System32'), os.environ['WINDIR']]),
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', QT_QPA_PLATFORM='offscreen',
                   HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9')
        for key in ['PYTHONHOME', 'PYTHONPATH', 'AZB_QT_PATH', 'AZB_DATA_DIR']:
            env.pop(key, None)

        def run(arguments):
            argv = [str(item) for item in arguments]
            # NSIS requires its final /D= and _?= switches unquoted, even with spaces.
            command = (subprocess.list2cmdline(argv[:-1]) + ' ' + argv[-1]
                       if argv[-1].startswith(('/D=', '_?=')) else argv)
            subprocess.run(command, executable=argv[0], env=env, check=True,
                           timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)

        if args.legacy_setup:
            assert args.legacy_setup.resolve() != setup, 'Use an earlier installer for the upgrade test.'
            run([args.legacy_setup.resolve(), '/S', '/TESTMODE', f'/D={target}'])
            earlier_apps = [app for app in (target/'Voxriva.exe', target/'Avunote.exe') if app.is_file()]
            assert len(earlier_apps) == 1, 'The earlier Setup did not install exactly one application.'
            with earlier_apps[0].open('rb') as stream:
                earlier_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            # Existing private files in the installation must survive an upgrade.
            (target/'keep-user-file.txt').write_text('Preserve unknown user files.', encoding='utf-8')
            (target/'models').mkdir(exist_ok=True)
            (target/'models'/'keep-model.txt').write_text('Preserve user models.', encoding='utf-8')
        run([setup, '/S', '/TESTMODE', f'/D={target}'])
        marker_bytes = (target/'.voxriva-install.ini').read_bytes()
        marker = marker_bytes.decode('utf-16' if marker_bytes.startswith(b'\xff\xfe') else 'mbcs')
        assert 'TestMode=1' in marker and str(target) in marker
        assert not (target/'Voxriva.exe').exists()
        executable = target/'Avunote.exe'
        assert executable.is_file(), 'Setup did not install Avunote.exe.'
        assert (target/'_internal'/'VERSION').read_text(encoding='utf-8-sig').strip() == version
        sys.path.insert(0, str(root/'app'))
        from app_updates import baseline_digest
        assert baseline_digest(target.resolve(), version, verify_files=True), 'Installed update baseline failed verification.'
        for source in (root/'app').glob('*.py'):
            assert (target/'app'/source.name).read_bytes() == source.read_bytes(), source.name
        report.update(setup_install='passed', source_copy_hashes='passed', update_baseline_hashes='passed')
        if args.legacy_setup:
            with executable.open('rb') as stream:
                current_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
            assert current_hash != earlier_hash, 'Upgrade did not replace the earlier application binary.'
            report['earlier_setup'] = args.legacy_setup.name
            report['legacy_in_place_upgrade'] = 'passed'
            assert (target/'keep-user-file.txt').is_file() and (target/'models'/'keep-model.txt').is_file() and private_sentinel.is_file()
            report['upgrade_preserves_models_history_and_unknown_files'] = 'passed'
        for page in ['studio', 'library', 'ai', 'history', 'settings']:
            preview = fixture/f'{page}.png'
            run([target/'Avunote.exe', '--page', page, '--preview', preview])
            assert preview.is_file() and preview.stat().st_size > 1000
        report['installed_gui_without_external_python_path'] = 'passed'
        unknown = target/'keep-user-file.txt'
        unknown.write_text('Preserve unknown user files.', encoding='utf-8')
        model_sentinel = target/'models'/'keep-model.txt'
        model_sentinel.parent.mkdir(exist_ok=True)
        model_sentinel.write_text('Preserve user models.', encoding='utf-8')
        run([target/'Uninstall.exe', '/S', f'_?={target}'])
        assert not (target/'Avunote.exe').exists()
        assert unknown.is_file() and model_sentinel.is_file() and private_sentinel.is_file()
        report['uninstall_preserves_models_history_and_unknown_files'] = 'passed'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
