# Avunote

![Avunote](assets/avunote-logo-transparent.png)

Offline desktop speech transcription for Windows 10/11 x64, developed by **Fardin Milani**.

[فارسی](README_FA.md) · [GitHub repository](https://github.com/Fardinmilani/Voxriva) · [Website](https://fardinmilani.ir)

The source repository and release package contain no model weights or personal audio. Choose a language and explicitly download a model inside the app. Once downloaded, transcription runs locally on the CPU without uploading audio. General multilingual models are shared across languages, so switching from Persian to Turkish or English does not require downloading the same model twice.

- Dedicated Iranian/South Azerbaijani models.
- Offline Persian, Turkish, English and other supported languages with multilingual Whisper models.
- File selection, drag-and-drop, microphone recording, raw text export and local history.
- Download progress, transfer speed, pause/resume and cancel, with pinned model revisions and integrity verification.
- Light/Dark/System themes and optional hardware acceleration with CPU recovery.
- Bounded sequential audio chunks and per-segment text checkpoints for long recordings.
- Continuing AI chats with saved history and repeat voice messages, using the same local speech engine and settings as the studio.
- Connect Gemini, OpenAI-compatible APIs, LM Studio or local Ollama; review transcribed voice text before sending.

The interface opens in English by default and can be switched to Persian, Turkish, Arabic or Azerbaijani. There are 99 speech-language categories, separate from these five interface languages. Interface language and speech language are independent: changing the UI never translates the ASR output. Developer information is in About; the main workspace focuses on recording and transcription.

## Run a Windows release

Run Setup to choose an installation directory and optionally create a desktop shortcut on the finish page. Alternatively, extract the entire Windows ZIP and open `Avunote.exe`; keep `app`, `_internal` and license/source files together. The CPU runtime is included; Python and Node.js are not separate requirements. Recognition stays local. Internet is used for model downloads and, only when explicitly chosen, cloud AI text requests. CUDA/NPU require compatible optional runtimes/drivers/models; errors recover to CPU. No high accuracy guarantee is made for every dialect or recording.

Version **2.3.0** adds more offline speech models, a redesigned light and dark workspace, and explicit installation status in the model picker. Models that need a download remain visible and become selectable after verification. AI chat now includes **Grammar review** for corrections with explanations and **Language practice** for short exercises by text or voice. The conversation saves the chosen mode.

Avunote was previously called Voxriva. Close either application before upgrading. Setup reuses the previous registered installation and preserves downloaded models, preferences, API profiles and local chat history. Internal data-directory and installer identifiers remain compatible with earlier versions. The GitHub repository keeps its existing URL.

See [Avunote 2.2 features, hardware setup and AI privacy](FEATURES_2_2.md). In particular, Google AI Studio free quotas and privacy terms vary, and local AI requires a running local server/model. AI does not modify the original transcript. Keys are session-only or opt-in Windows-DPAPI encrypted, outside this repository. Setup and portable binaries belong in GitHub Releases; the source package excludes them and model weights.

The proposed domain is **avunote.com**; it has not been registered or published by this project. See [the name checks and brand assets](docs/BRAND.md).

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
| [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) | 670.5 MB | Automatic recognition across 25 European languages |
| [Alibaba Qwen3-ASR 0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) | 987.0 MB | Automatic language recognition including Persian, Turkish and Arabic |
| [FunAudioLLM SenseVoice Small](https://huggingface.co/FunAudioLLM/SenseVoiceSmall) | 239.5 MB | Mandarin, English, Japanese and Korean |
| AZB Base Full | 292.3 MB | Dedicated South Azerbaijani default |
| AZB Base | 292.3 MB | Dedicated comparison |
| AZB Tiny | 153.0 MB | Dedicated fast option |
| AZB Small Farsi-init | 968.9 MB | Dedicated South Azerbaijani comparison |

Sizes describe the required repository files, not RAM or total application size. The general Whisper `az` model is not used as a substitute for South Azerbaijani. “Farsi-init” is an Azerbaijani fine-tune initialized from Persian, not the model used for Persian transcription.

The Parakeet, Qwen3-ASR and SenseVoice INT8 exports use the included Sherpa-ONNX CPU engine. The library filters models by the selected speech language. Models labeled automatic detect the spoken language within their supported set. Check the model card and license in the library before downloading.

Managed downloads and local application data are stored under `%LOCALAPPDATA%\AZBVoiceStudio`; this directory name is retained for compatibility with earlier versions. `AVUNOTE_DATA_DIR` may point to another writable directory; the older `VOXRIVA_DATA_DIR` and `AZB_DATA_DIR` aliases are also accepted in that order. Use the local-model-folder option to register an existing cache or the old portable package's `_internal\assets\models` folder. Compatible existing checkpoints can then be reused without copying or downloading them again. A paused download retains its partial bytes; the UI explains the current state. Never send your cache, recordings, results or tokens when sharing the source repository.

## Build and contribute

For a configured development checkout, double-click **`BUILD_SETUP.cmd`** after
editing the source. Change **`VERSION`** when preparing a new release. The script
runs the tests, rebuilds the executable from current source, collects component
licenses and matching sources, and creates
`release/Avunote-<VERSION>-Windows-x64-Setup.exe` plus its SHA-256 file. It keeps
the terminal open to show success or an actionable failure; build logs are in
`.local/build-logs`. It never reuses an old executable as the new application.

Machine-specific tool paths may be set in ignored `.local/build-settings.json`
using `Python`, `QtPath`, `SourceCache` and `Makensis` keys. Relative paths resolve
from the repository root. The default build uses existing tools and verified
source caches; it does not install packages or download models. A fresh clone
needs the development dependencies and slim LGPL FFmpeg described below.
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_setup.ps1 -CheckOnly`
checks those prerequisites without building. This execution policy applies only
to that PowerShell process.

To build entirely on GitHub, open **Actions → Build Windows model-free app → Run
workflow**. Download the Setup artifact when it succeeds. The workflow reads the
same `VERSION` file and does not publish a release automatically. Keep models,
tool caches, installers and private data outside Git; `.local/`, `build/`,
`dist/` and `release/` are ignored.

Install `requirements-dev.txt`, prepare the slim audio decoder and its matching source/notices, then run `build_windows.ps1` from the repository root. The notice-preparation step fetches approximately 85 MB of pinned library source archives and a 2.2 MB official Intel runtime package if not already cached; these are not ASR model weights. To reuse existing archives, pass `-SourceCache C:\path\to\Licenses\Sources` or set `AZB_SOURCE_CACHE`. The helper `scripts/prepare_notices.py --offline --source-cache ...` can verify/collect them without network. The build keeps the application `.py` source alongside the executable in `app`; do not delete it. The GitHub Actions workflow builds an artifact; it does not publish a GitHub release. No model should be downloaded or bundled by a build. Keep the complete third-party license/source directory when sharing a binary release.

Application source is [MIT](LICENSE), copyright 2026 Fardin Milani. Model and library licenses remain separate. The AZB maintainer's MIT confirmation was relayed by Fardin Milani; this repository does not claim that the upstream Hugging Face model card currently contains an MIT notice. Preserve the Kartal Ol attribution and [all third-party notices](THIRD_PARTY_NOTICES.md).
