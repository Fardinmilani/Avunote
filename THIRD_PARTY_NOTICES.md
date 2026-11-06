# Third-party notices and model provenance

Application developer: **Fardin Milani**, <https://github.com/Fardinmilani>, <https://fardinmilani.ir>.
The application source is MIT. Its license does not replace or relicense dependencies, models, or upstream datasets.

## South Azerbaijani models: Kartal Ol

Credit: **Kartal Ol Foundation / مؤسسه Kartal Ol**, <https://github.com/Kartalol>.

- Model repository: <https://huggingface.co/Kartal-Ol/ASR-AZB>
- Research/code repository: <https://github.com/Kartalol/Kartalol-azb-asr>
- Pinned revision: `ca9890cd78fb181633a61f4b8a71a750acdcfdf4`
- Included catalog folders: `whisper-base-full`, `whisper-base`, `whisper-tiny`, `whisper-Small-Farsi`.

On 2026-11-03, application developer Fardin Milani reported that the model maintainer directly confirmed the AZB models are MIT-licensed and requested attribution to Kartal Ol. The application preserves that attribution. This records the maintainer confirmation as relayed by the developer; it does not claim the current upstream Hugging Face metadata or model card contains an MIT license notice. The research repository's own code license is separate from the model permission. Preserve any upstream copyright/license notices received with a model; do not replace them with the application's copyright.

Model weights are not part of the source repository or default executable release. No training datasets are redistributed here.

## Multilingual Whisper / CTranslate2 models

The catalog uses these public, ungated repositories with MIT license declarations:

- <https://huggingface.co/Systran/faster-whisper-tiny>
- <https://huggingface.co/Systran/faster-whisper-base>
- <https://huggingface.co/Systran/faster-whisper-small>

The model cards describe conversion of the original OpenAI Whisper models into CTranslate2 format. Download revisions, file sizes and SHA-256 hashes are pinned in the catalog. The checkpoint files are FP16 on disk; CPU inference uses INT8 conversion at load time. A single multilingual checkpoint is shared across supported general-language categories.

Original Whisper model/code attribution: **Copyright (c) 2022 OpenAI**, MIT. Full notice: [licenses/WHISPER-MIT.txt](licenses/WHISPER-MIT.txt). Original repository: <https://github.com/openai/whisper>. Conversion model repositories are published by **SYSTRAN**. Their MIT declarations and source provenance are retained by these links and catalog records; the application does not claim model authorship.

The application uses CTranslate2 directly, not the faster-whisper Python package. CTranslate2 is MIT: <https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE>. Its actual installed release's notices must be retained in the binary distribution.

The CTranslate2 4.8.5 MIT notice is preserved in [licenses/CTRANSLATE2-MIT.txt](licenses/CTRANSLATE2-MIT.txt). Its Windows wheel includes native dependencies with their own terms; they are not relicensed as MIT by this application.

For OpenMP, the Windows release uses the unmodified x64 `libiomp5md.dll` from Intel's official **`intelopenmp.redist.win` 2025.3.0.640 NuGet redistributable package**. That publisher package explicitly supplies the **Intel Simplified Software License, October 2022**. The full license permits use/redistribution of the unchanged binary with its notices and contains restrictions applying to the Intel component, not Voxriva's source. The exact license, copyright metadata and third-party notice are in [licenses/Intel-OpenMP-Redistributable-2025.3.0.640](licenses/Intel-OpenMP-Redistributable-2025.3.0.640). See also [component-specific runtime terms](licenses/BINARY_RUNTIME_TERMS.md).

- Official publisher description of the OpenMP runtime redistributable and NuGet license: <https://www.intel.com/content/www/us/en/developer/articles/guide/installing-performance-libraries-using-nuget.html>
- Exact package: <https://www.nuget.org/packages/intelopenmp.redist.win/2025.3.0.640>
- Package SHA-256: `a4212c4aec3e528864d56d8b0c87103cd5c21a888d1985124909a1f85624a449`.
- DLL: 1,614,192 bytes, version `20250910`, SHA-256 `982233366b0afcda1e0f55a0b134097e35b779613f54ddb69e685e6cd06b755f`.

The build verifies that package and DLL, then places that exact redistributable into every packaged OpenMP runtime location, including CTranslate2 and PyTorch. It does not modify installed developer environments. The license/provenance for this NuGet distribution is the redistribution basis; an alternate-channel Intel PyPI EULA is not substituted for it.

## Per-model license record

The application license is not used to infer a model's license. Each included catalog entry has its own repository and license basis:

| Catalog entry | Model repository / folder | License basis |
|---|---|---|
| `whisper-base-full` | Kartal-Ol/ASR-AZB — `whisper-base-full` | MIT confirmation from the model maintainer, relayed by Fardin Milani; Kartal Ol attribution retained |
| `whisper-base` | Kartal-Ol/ASR-AZB — `whisper-base` | Same maintainer confirmation for this AZB model collection; upstream metadata gap disclosed above |
| `whisper-tiny` | Kartal-Ol/ASR-AZB — `whisper-tiny` | Same maintainer confirmation for this AZB model collection; attribution retained |
| `whisper-Small-Farsi` | Kartal-Ol/ASR-AZB — `whisper-Small-Farsi` | Same maintainer confirmation for this AZB model collection; attribution retained |
| `multilingual-tiny` | [Systran/faster-whisper-tiny](https://huggingface.co/Systran/faster-whisper-tiny) | This repository's own MIT model-card declaration; original OpenAI MIT notice retained |
| `multilingual-base` | [Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base) | This repository's own MIT model-card declaration; original OpenAI MIT notice retained |
| `multilingual-small` | [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small) | This repository's own MIT model-card declaration; original OpenAI MIT notice retained |
| `parakeet-tdt-v3` | [Sherpa-ONNX Parakeet TDT 0.6B v3 INT8 export](https://huggingface.co/csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8) | [NVIDIA Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Converted to ONNX and quantized by the Sherpa-ONNX project |
| `qwen3-asr-06b` | [Sherpa-ONNX Qwen3-ASR 0.6B INT8 export](https://huggingface.co/csukuangfj2/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25) | [Alibaba Qwen](https://huggingface.co/Qwen/Qwen3-ASR-0.6B), Apache-2.0. Converted and quantized by Wasser1462; export published by Sherpa-ONNX |
| `sensevoice-small` | [Sherpa-ONNX SenseVoice Small INT8 export](https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17) | [FunAudioLLM SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall), [FunASR Model Open Source License Agreement v1.1](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE). Attribution and model name are preserved |

Pinned revisions and exact artifacts are in `app/model_catalog.py`. Adding a future model requires reviewing its own published license, original model provenance and required notices; do not inherit the AZB collection's license by assumption.

## Sherpa-ONNX / ONNX Runtime

The three optional ONNX models run through the unmodified Windows x64 CPU
wheels [sherpa-onnx 2.0.1](https://pypi.org/project/sherpa-onnx/2.0.1/) and
[sherpa-onnx-core 2.0.1](https://pypi.org/project/sherpa-onnx-core/2.0.1/).
Sherpa-ONNX is Apache-2.0. The application packages the Python binding and
shared libraries. [Sherpa-ONNX release and source](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v2.0.1).

The core wheel includes Microsoft ONNX Runtime 1.28.2. The build verifies
the exact Windows x64 DLL before creating Setup. [ONNX Runtime MIT license](licenses/ONNXRuntime-1.28.2/LICENSE)
and [Microsoft third-party notices](licenses/ONNXRuntime-1.28.2/ThirdPartyNotices.txt)
are included alongside the [Sherpa-ONNX and native component notices](licenses/Sherpa-ONNX-2.0.1).

## Vazirmatn font

The interface bundles the Regular, Medium, SemiBold and Bold static TTF files of [Vazirmatn](https://github.com/rastikerdar/vazirmatn) v33.003 for Persian and Arabic text. Copyright 2015 The Vazirmatn Project Authors. The fonts are unmodified and licensed under the SIL Open Font License 1.1; the license text is kept beside them in [`assets/fonts/Vazirmatn-OFL.txt`](assets/fonts/Vazirmatn-OFL.txt).

## Qt / PySide6 / Shiboken

PySide6, Shiboken and the distributed Qt modules are used as dynamically loaded, separate libraries under LGPLv3 or the applicable upstream license option. Preserve the exact release's license/copyright files and corresponding source archives with binary distributions. The intended release uses Qt/PySide 6.12.0; archives for Qt Base, Qt SVG, Qt Image Formats and PySide/Shiboken must match the shipped components. Add matching sources for any additional Qt modules shipped later.

Users may replace or relink compatible LGPL libraries. No program restriction is intended to prevent modification or reverse engineering for debugging changes to those libraries. This app's MIT source is available independently.

- LGPL obligations: <https://www.qt.io/development/open-source-lgpl-obligations>
- Qt source archives: <https://download.qt.io/official_releases/qt/6.12/6.12.0/submodules/>
- Qt for Python source: <https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/>
- Build instructions: <https://doc.qt.io/qt-6/build-sources.html> and <https://doc.qt.io/qtforpython-6/building_from_source/index.html>.

## FFmpeg audio decoder

Release builds use a separate slim FFmpeg 7.1 executable, built from unmodified upstream source with GPL, version3, autodetected external libraries and networking disabled. Enable only the file protocol, required audio demuxers/decoders, PCM16 WAV output and audio resampling. The resulting FFmpeg component is **LGPL-2.1-or-later** and may be replaced with a compatible executable.

Ship the exact source archive, configuration/build instructions, compiler/runtime notices and LGPL text alongside that binary. The source archive SHA-256 for `ffmpeg-7.1.tar.xz` is `40973d44970dbc83ef302b0609f2e74982be2d85916dd2ee7472d30678a7abe6`.

- Source: <https://ffmpeg.org/releases/ffmpeg-7.1.tar.xz>
- License: <https://ffmpeg.org/legal.html>

The `imageio-ffmpeg` Python package is a helper used to locate the executable. A general-purpose FFmpeg binary installed by that package can have a different GPL license and statically linked external components. Do not ship that binary as if it were the slim LGPL build. The build must require `vendor/ffmpeg.exe` and preserve its matching source package; if it is missing, stop the redistribution build rather than silently substituting a different FFmpeg binary.

## Other libraries and build tools

The binary distribution must retain notices from the actual installed packages and their bundled components, including Python, PyTorch CPU, NumPy, Transformers, Tokenizers, Hugging Face Hub, safetensors, requests, psutil, sounddevice/PortAudio, imageio-ffmpeg, CTranslate2, PySide/Shiboken and the packaging tools. Their upstream licenses remain in force. PyInstaller's bootloader has its upstream license exception; consult its included notice. Build tools are not model authors.

This file describes the project's distribution approach and known provenance. It does not claim a legal audit or grant rights beyond the respective licenses and maintainer permission. Keep all release `Licenses` files when redistributing an executable package.
