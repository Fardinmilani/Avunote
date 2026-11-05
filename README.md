# Voxriva

Offline desktop speech transcription for Windows 10/11 x64, developed by **Fardin Milani**.

[فارسی](README_FA.md) · [GitHub repository](https://github.com/Fardinmilani/Voxriva) · [Website](https://fardinmilani.ir)

The source repository and release package contain no model weights or personal audio. Choose a language and explicitly download a model inside the app. Once downloaded, transcription runs locally on the CPU without uploading audio. General multilingual models are shared across languages, so switching from Persian to Turkish or English does not require downloading the same model twice.

- Dedicated Iranian/South Azerbaijani models.
- Offline Persian, Turkish, English and other supported languages with multilingual Whisper models.
- File selection, drag-and-drop, microphone recording, raw text export and local history.
- Download progress, transfer speed, pause/resume and cancel, with pinned model revisions and integrity verification.
- Light/Dark/System themes and optional hardware acceleration with CPU recovery.
- Bounded sequential audio chunks and per-segment text checkpoints for long recordings.
- Explicit text-only AI chat with Gemini, OpenAI-compatible APIs, LM Studio or local Ollama.

The interface opens in English by default and can be switched to Persian, Turkish, Arabic or Azerbaijani. There are 99 speech-language categories, separate from these five interface languages. Interface language and speech language are independent: changing the UI never translates the ASR output. Developer information is in About; the main workspace focuses on recording and transcription.

## Run a Windows release

Run Setup to choose an installation directory and optionally create a desktop shortcut on the finish page. Alternatively, extract the entire Windows ZIP and open `Voxriva.exe`; keep `app`, `_internal` and license/source files together. The CPU runtime is included; Python and Node.js are not separate requirements. Recognition stays local. Internet is used for model downloads and, only when explicitly chosen, cloud AI text requests. CUDA/NPU require compatible optional runtimes/drivers/models; errors recover to CPU. No high accuracy guarantee is made for every dialect or recording.

Version **2.1.1** fixes the Windows `WinError 5` progress-file sharing error. Close Voxriva and run the updated Setup to upgrade the existing installation; downloaded models and local profile data are preserved.

See [Voxriva 2.1 features, hardware setup and AI privacy](FEATURES_2_1.md). In particular, Google AI Studio free quotas and privacy terms vary, and local AI requires a running local server/model. AI does not modify the original transcript. Keys are session-only or opt-in Windows-DPAPI encrypted, outside this repository. Setup and portable binaries belong in GitHub Releases; the source package excludes them and model weights.

## Run from source

Use Python 3.11–3.13 x64 and a project-local virtual environment. PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\entrypoint.py
```

The source installation of `imageio-ffmpeg` can contain a general-purpose GPL build. For a redistribution build, use the project's slim LGPL audio-only FFmpeg in `vendor/ffmpeg.exe`; do not silently substitute the PyPI executable. See [third-party notices](THIRD_PARTY_NOTICES.md). The Windows workflow builds this slim decoder from the matching official source release.

## Model downloads and local data

| Model | Approximate model download | Purpose |
|---|---:|---|
| Multilingual Tiny | 78.2 MB | Fast previews |
| Multilingual Base | 147.9 MB | Balanced CPU option |
| Multilingual Small | 486.2 MB | Quality-oriented multilingual option |
| AZB Base Full | 292.3 MB | Dedicated South Azerbaijani default |
| AZB Base | 292.3 MB | Dedicated comparison |
| AZB Tiny | 153.0 MB | Dedicated fast option |
| AZB Small Farsi-init | 968.9 MB | Dedicated South Azerbaijani comparison |

Sizes describe the required repository files, not RAM or total application size. The general Whisper `az` model is not used as a substitute for South Azerbaijani. “Farsi-init” is an Azerbaijani fine-tune initialized from Persian, not the model used for Persian transcription.

Managed downloads and local application data are stored under `%LOCALAPPDATA%\AZBVoiceStudio`; this directory name is retained for compatibility with earlier versions. `VOXRIVA_DATA_DIR` may point to another writable directory; the older `AZB_DATA_DIR` alias is also accepted. Use the local-model-folder option to register an existing cache or the old portable package's `_internal\assets\models` folder. Compatible existing checkpoints can then be reused without copying or downloading them again. A paused download retains its partial bytes; the UI explains the current state. Never send your cache, recordings, results or tokens when sharing the source repository.

## Build and contribute

Install `requirements-dev.txt`, prepare the slim audio decoder and its matching source/notices, then run `build_windows.ps1` from the repository root. The notice-preparation step fetches approximately 85 MB of pinned library source archives and a 2.2 MB official Intel runtime package if not already cached; these are not ASR model weights. To reuse existing archives, pass `-SourceCache C:\path\to\Licenses\Sources` or set `AZB_SOURCE_CACHE`. The helper `scripts/prepare_notices.py --offline --source-cache ...` can verify/collect them without network. The build keeps the application `.py` source alongside the executable in `app`; do not delete it. The GitHub Actions workflow builds an artifact; it does not publish a GitHub release. No model should be downloaded or bundled by a build. Keep the complete third-party license/source directory when sharing a binary release.

Application source is [MIT](LICENSE), copyright 2026 Fardin Milani. Model and library licenses remain separate. The AZB maintainer's MIT confirmation was relayed by Fardin Milani; this repository does not claim that the upstream Hugging Face model card currently contains an MIT notice. Preserve the Kartal Ol attribution and [all third-party notices](THIRD_PARTY_NOTICES.md).
