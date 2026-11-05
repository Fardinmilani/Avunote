# Voxriva 2.1

## Processing device and long recordings

Choose Automatic, CPU, CUDA, or NPU in the advanced recognition settings.
Availability means that the selected model and its software backend work on that
device, not just that the computer contains a GPU/NPU. The default distribution
contains CPU PyTorch; it does not silently fetch multi-gigabyte CUDA libraries.
Compatible CTranslate2 CUDA libraries and drivers must already be available for
that backend's CUDA path. A load or inference error falls back to CPU, retries
the affected chunk once, and preserves earlier completed chunks. Metrics record
the requested and actual devices and the fallback reason.

Audio is converted locally to PCM16 mono 16 kHz on disk, then read in bounded
10/15/20/25/30-second windows (default 20). Quiet boundaries are preferred. Every
frame is processed once, without overlapping text or an arbitrary rewrite.
Each successful chunk checkpoints the raw `.txt`, `.segments.json`, and metrics.
This bounds audio memory and avoids carrying hallucinated context between chunks;
it does not guarantee recognition accuracy on noisy or ambiguous speech.

NPU is an **optional OpenVINO GenAI path**, not a claim that ordinary PyTorch or
CTranslate2 model files run directly on NPU. It needs a supported NPU driver,
compatible OpenVINO GenAI packages, and a local IR export of the **same selected
checkpoint**. An explicit `VOXRIVA_OPTIONAL_BACKENDS_DIR` may point to optional
packages matching the portable Python ABI (CPython 3.13 x64 for this build).
No optional package or IR export is downloaded automatically.

Place the export in `<checkpoint>/openvino`, or set
`VOXRIVA_OPENVINO_MODELS_DIR/<model-key>`. Required files are listed in
`app/compute_devices.py`. Add `voxriva-openvino.json` with:

```json
{
  "format": "openvino-genai-whisper",
  "source_model_key": "multilingual-tiny",
  "source_repo": "Systran/faster-whisper-tiny",
  "source_revision": "d90ca5fe260221311c53c58e660288d3deb8d356",
  "source_subfolder": "",
  "speech_language": "multilingual"
}
```

Use the exact catalog identity for your own export; dedicated Iranian Azerbaijani
exports must declare `speech_language: "azb"`. This records user-supplied export
provenance, not a cryptographic proof of an arbitrary export's training history.
If the runtime, export or hardware is unavailable, CPU remains usable.
Physical GPU/NPU execution has not been tested on this development laptop;
selection and recovery are covered by mocked tests.

## AI chat and API profiles

AI is separate from ASR. Add a connection for:

- Google AI Studio / Gemini (`generateContent`, editable model ID).
- OpenAI-compatible text chat APIs, including local LM Studio.
- A local Ollama server and an already installed local model.

The application does not download a local LLM. Add your own endpoint, model name
and API key. Keys are session-only by default; optional remembered keys use
Windows DPAPI for the current account. They are never committed to the source,
included in chat exports, or logged. Keys copied to another Windows account may
need to be entered again.

Use **Discuss with AI** or **Use current transcript** to select reference text.
Only pressing **Send** submits text. A separate cloud consent checkbox is required
for a remote endpoint. Neither the audio file nor raw ASR output is modified.
Chat replies and follow-up conversations are stored separately in the local
profile's `ai-chats` folder. Original transcripts retain their original spelling.
Large conversations are rejected with an explanation rather than silently cut.
Stopping a request discards its reply, but a cloud provider may still finish or
charge for a request it has already received.

Google's free tier depends on the model, project, region and current quotas; it is
not unlimited or guaranteed. Unpaid requests/replies may be used to improve Google
products and reviewed by humans under Google's applicable terms. Model IDs are
editable because availability changes. Creating an API profile makes no request.
Real cloud credentials have not been used in development tests.

Official references: [Gemini API](https://aistudio.google.com/api-reference/generate-content/generate-content),
[keys](https://aistudio.google.com/apikey), [quotas](https://aistudio.google.com/docs/rate-limits),
[terms](https://ai.google.dev/gemini-api/terms),
[Ollama chat](https://docs.ollama.com/api/chat),
[OpenVINO NPU](https://docs.openvino.ai/2026/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html).

## Appearance, installation and GitHub

Light, Dark and System themes persist independently of the five interface
languages. The logo uses a transparent asset and native dark-theme foreground
rendering. A one-time optional invitation after successful transcription can
open https://github.com/Fardinmilani/Voxriva. Declining or closing it also marks
it as seen. Voxriva never performs a GitHub star action or checks your account.

The source package excludes model weights, native runtime libraries, API keys,
chat history, recordings, build caches, generated release archives and installers.
Put Setup/portable binaries in GitHub **Releases**, not the Git repository.
The app is MIT; model and dependency licenses retain their separate terms.
The per-user uninstaller preserves downloaded models and personal profile data.
