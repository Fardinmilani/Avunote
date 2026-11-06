import argparse
from pathlib import Path
import sys
import traceback

if getattr(sys, 'frozen', False):
    # Ship the MIT application source beside the runtime. It remains reviewable
    # and updateable independently from large third-party libraries.
    application_source = Path(sys.executable).parent / 'app'
    if application_source.is_dir():
        sys.path.insert(0, str(application_source))
    try:
        startup_log = (Path(sys.executable).parent / 'startup.log').open('a', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = startup_log
        print('Starting Avunote')
    except OSError:
        pass

if not getattr(sys, 'frozen', False):
    qt = Path(__file__).resolve().parents[3] / 'work' / 'qt'
    if qt.exists():
        sys.path.insert(0, str(qt))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--model', default='whisper-base-full')
    parser.add_argument('--beams', type=int, default=5)
    parser.add_argument('--language', default='azb')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda', 'npu'], default='auto')
    parser.add_argument('--chunk-seconds', type=int, choices=[10, 15, 20, 25, 30], default=20)
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--page', choices=['studio', 'library', 'history', 'ai', 'settings'], default='studio')
    parser.add_argument('audio', nargs='?')
    args = parser.parse_args()
    if args.worker:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        log = args.output.with_suffix('.log').open('w', encoding='utf-8')
        sys.stdout = sys.stderr = log
        from studio_engine import transcribe
        sys.exit(transcribe(args.worker, args.output, args.model, args.beams, args.language,
                            device=args.device, chunk_seconds=args.chunk_seconds))
    try:
        print('Loading desktop interface')
        from studio_ui import launch
        print('Desktop interface loaded')
        launch(args.audio, args.preview, args.page)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
