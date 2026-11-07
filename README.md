# Avunote

![Avunote](assets/avunote-logo-transparent.png)

Local speech transcription for **Windows 10/11 x64**, developed by **Fardin Milani**. Record or drop an audio file, pick a language and a downloaded model, and the words stay on your machine.

[فارسی](README_FA.md) · [GitHub](https://github.com/Fardinmilani/Voxriva) · [Website](https://fardinmilani.ir)

Version **2.4.0**. The product name is Avunote (آوونوت). The GitHub repository URL remains `Fardinmilani/Voxriva`; Avunote was previously called Voxriva. The source tree and release packages contain no model weights and no personal audio.

![Speech studio](docs/screenshots/studio.png)

![AI chat](docs/screenshots/ai-chat.png)

## What it does

Avunote is a desktop studio: microphone recording or WAV/MP3/M4A/OGG files, a local ASR model library, transcript history, and optional AI chat about those transcripts. Recognition never uploads audio. Internet is used to download models you choose, to check GitHub Releases for updates (Setup installs only), and — only after you press Send on a remote connection — to send **text** to an AI API.

The workspace opens in English by default. Interface language and speech language are independent: changing menus never translates the ASR output. Developer credits live in About; the main pages are Studio, History, Model library, AI chat, and Settings.

## Features

### Speech studio

- Choose a speech language, then a model that the library filters for that language.
- Record from a selected microphone, or choose / drag-and-drop WAV, MP3, M4A, or OGG.
- Transcription starts when recording stops, or when a file is submitted.
- Output is the model’s raw text: no translation, spelling “fix”, or rewrite of the original transcript.
- Copy, save as text, and transcribe the same file again with another language or model.
- Processing options: higher-accuracy vs faster beam setting; Automatic / CPU / CUDA / NPU; chunk length 10–30 seconds (default 20). Long files are converted locally to PCM16 mono 16 kHz and processed in bounded windows with per-chunk text checkpoints. CUDA and NPU need compatible optional runtimes, drivers, and (for NPU) a local OpenVINO export; a load or inference error retries the current chunk on CPU. The default build ships a CPU PyTorch runtime and does not fetch CUDA libraries.
- Light, Dark, or System theme. The UI follows a monochrome “Signal” direction (ink surfaces, one tally accent for record/live state).

### Model library

Models are listed in the app until you download or register them. Downloads show progress, speed, pause/resume, and cancel. Files are size-checked and integrity-verified against the pinned catalog; incomplete files are not treated as ready. A multilingual checkpoint is shared across supported languages, so switching Persian → Turkish → English does not download the same Whisper model twice.

Catalog in 2.4.0 (sizes are required repository files, not RAM or the installer):

| Model | Approx. download | Engine | Notes |
|---|---:|---|---|
| Whisper Tiny / Base / Small / Medium | 78 MB · 148 MB · 486 MB · 1.53 GB | faster-whisper (CTranslate2) | Shared multilingual models |
| [Omnilingual ASR 300M](https://huggingface.co/facebook/omniASR-CTC-300M) | 365 MB | Sherpa-ONNX CTC | Broad multilingual set with automatic language/script detection (INT8 export) |
| [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) | 670 MB | Sherpa-ONNX | Automatic recognition among 25 European languages |
| [Alibaba Qwen3-ASR 0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) | 987 MB | Sherpa-ONNX | Automatic language recognition including Persian, Turkish, and Arabic |
| [FunAudioLLM SenseVoice Small](https://huggingface.co/FunAudioLLM/SenseVoiceSmall) | 240 MB | Sherpa-ONNX | Mandarin, English, Japanese, Korean |
| AZB Base Full / Base / Tiny / Small Farsi-init | 292 · 292 · 153 · 969 MB | Transformers | Dedicated Iranian / South Azerbaijani models ([Kartal Ol](https://github.com/Kartalol)) |

There are 99 speech-language categories. General Whisper `az` is not used as a stand-in for Iranian Azerbaijani. “Farsi-init” names an Azerbaijani fine-tune’s starting point, not the Persian transcription model. Models labeled automatic detect language within their own supported set. Read the card and license in the library before downloading. No accuracy percentage is claimed for every dialect or recording.

### History

Local results list file/recording, duration, processing time, and date. Double-click (or Open transcript) to restore the raw text and metrics. A folder action opens the on-disk recordings and transcripts.

### AI chat

AI is separate from ASR. You can discuss a studio transcript, paste text, or add voice inside the conversation. Chat modes: **Chat**, **Grammar review** (correction with a short explanation), and **Language practice**. The chosen mode is stored with the conversation. Saved chats reopen after restart.

Voice-in-chat uses **its own speech-language and ASR-model pickers** (including auto-detect when the selected model supports it), not a hidden copy of the studio combo boxes. Record another clip or attach another audio file while the app is idle. Recognition uses the same local engine as Studio. The recognized words land in an editable draft; **Send** is still required. Audio is not sent to the AI provider.

### API connectors

Add a connection from presets; Avunote does not download an LLM. Creating a profile makes no network request. Model IDs are editable because provider catalogs change. Refresh the model list only when you ask.

| Connection | How it talks |
|---|---|
| Google AI Studio / Gemini | Gemini `generateContent` (not Vertex AI) |
| OpenAI | OpenAI-compatible chat API |
| Anthropic Claude | Anthropic Messages API |
| OpenRouter | Browser sign-in for **free** models, or paste an `sk-or-` API key |
| Groq, Mistral, Together, DeepSeek, Fireworks, xAI | OpenAI-compatible presets |
| OpenAI-compatible (custom) | Your base URL and key |
| LM Studio (local) | `http://127.0.0.1:1234/v1` |
| Local Ollama | Local chat API; use an already installed local model (not a cloud-routed Ollama tag) |

Remote endpoints need an explicit cloud-send confirmation. Google AI Studio free quotas and privacy terms vary and are not guaranteed. OpenRouter free models have provider usage limits; text goes to OpenRouter and the selected upstream. Stopping a request discards the local reply; a provider may still finish a request it already accepted. AI replies are stored separately from the original transcript and do not rewrite it.

### Interface languages and RTL

Twelve UI locales: English, Persian, Turkish, Arabic, Azerbaijani, Spanish, French, German, Brazilian Portuguese, Russian, Simplified Chinese, and Japanese. Persian and Arabic use RTL layout and the bundled Vazirmatn font.

### Privacy and keys

- ASR runs locally after the model is on disk. Audio is not uploaded for recognition.
- API keys are session-only unless you opt in to store them with Windows DPAPI for the current account. Keys are not written into chat exports or logs, and they are not in this repository.
- Local data (models, recordings, transcripts, chats, encrypted keys) live under `%LOCALAPPDATA%\AZBVoiceStudio` — that folder name is kept for upgrades from earlier builds. Overrides, in order: `AVUNOTE_DATA_DIR`, `VOXRIVA_DATA_DIR`, `AZB_DATA_DIR`.
- Point “add local model” at an existing cache or an old portable `_internal\assets\models` folder; compatible checkpoints are reused in place.

See [Avunote 2.2 notes on hardware, NPU exports, and AI privacy](FEATURES_2_2.md) and [in-app updates](docs/UPDATES.md). Setup installations can check GitHub Releases (`Fardinmilani/Voxriva`); set `AVUNOTE_DISABLE_UPDATES=1` to turn that off.

The proposed domain **avunote.com** is not registered or published by this project. Name-check notes and brand assets: [docs/BRAND.md](docs/BRAND.md).

## Requirements

- Windows 10 or 11, **x64**
- Microphone permission in Windows Settings if you record
- Disk space for whichever models you download
- Optional: internet for model downloads, update checks, and cloud AI
- Optional CUDA/NPU only with extra local runtimes — not bundled as a silent download

## Install a Windows release

1. Download `Avunote-<version>-Windows-x64-Setup.exe` from [GitHub Releases](https://github.com/Fardinmilani/Voxriva/releases) (and the `.sha256.txt` sidecar if you want to verify).
2. Close Avunote or Voxriva if either is running.
3. Run Setup, choose an install directory, and optionally create a desktop shortcut on the finish page. Default install is per-user.
4. Open Avunote, pick a speech language, download a model from the library, then record or open a file.

Setup reuses a previous registered install and keeps downloaded models, preferences, API profiles, and local chats. Internal data-directory and installer identities stay compatible with Voxriva / earlier Avunote builds.

Alternatively, extract the Windows ZIP and run `Avunote.exe`. Keep `app`, `_internal`, and the license/source files next to the executable. Python and Node.js are not separate requirements. Put installers in Releases, not in the git tree.

## Run from source

Python **3.11–3.13 x64** and a project-local virtual environment. PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\entrypoint.py
```

Install the CPU PyTorch wheel first so a CUDA extra is not pulled in by accident. A source install of `imageio-ffmpeg` may ship a general-purpose GPL FFmpeg. Redistributable builds must use this project’s slim LGPL audio-only `vendor/ffmpeg.exe` — see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Build and contribute

For a configured development checkout, run **`BUILD_SETUP.cmd`**. Bump **`VERSION`** when cutting a release. The script runs tests, rebuilds from current source, collects licenses/sources, and writes `release/Avunote-<VERSION>-Windows-x64-Setup.exe` plus SHA-256 (and, when applicable, a smaller update package — [docs/UPDATES.md](docs/UPDATES.md)). Logs: `.local/build-logs`. It never reuses an old executable as the new app.

Optional machine paths in ignored `.local/build-settings.json`: `Python`, `QtPath`, `SourceCache`, `Makensis`. Check tools without building:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_setup.ps1 -CheckOnly
```

GitHub Actions: **Actions → Build Windows model-free app → Run workflow**. The workflow reads `VERSION` and does not publish a Release by itself. Keep models, caches, installers, and private data out of git (`.local/`, `build/`, `dist/`, `release/`).

Install `requirements-dev.txt`, prepare the slim decoder and matching source/notices, then run `build_windows.ps1`. Notice preparation may fetch about 85 MB of pinned library source plus a 2.2 MB Intel runtime package if they are not cached — these are not ASR weights. Reuse archives with `-SourceCache` or `AZB_SOURCE_CACHE`. Application `.py` source is kept beside the frozen executable in `app`.

## License

Application source is [MIT](LICENSE), copyright 2026 Fardin Sheikh Milani. Model and library licenses stay separate. AZB MIT confirmation was relayed by the developer from the model maintainer; this repo does not claim the current Hugging Face model card contains an MIT file. Keep the Kartal Ol attribution and [third-party notices](THIRD_PARTY_NOTICES.md).

Qt/PySide is used as a separate LGPL library; licenses and corresponding sources ship with the binary so replacement is not blocked.
