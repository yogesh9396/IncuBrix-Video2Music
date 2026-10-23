# AI_USE.md — AI Coding Tools Disclosure

In accordance with Section 6 of the IncuBrix Engineering Assessment specification, this document details all AI coding assistants utilized throughout the project and the tasks they assisted with.

---

## 1. Tools Employed

| AI Assistant / Model | Context & Session | Key Contributions |
| :--- | :--- | :--- |
| **ChatGPT (OpenAI GPT-4o)** | Initial research & troubleshooting session | • Exploratory analysis of research repositories (`Video2Music`).<br>• Initial dependency troubleshooting on Windows (FluidSynth DLL paths, PyTorch CPU vs CUDA).<br>• Identification of CPU bottlenecks and memory consumption of heavy vision-audio transformer models. |
| **Google Antigravity (Gemini 3.8 Flash High)** | Backend development, testing & DevOps | • Architectural design of the standalone `IncuBrix_Submission` engine.<br>• Implementation of the 4-stem multi-track synthesis DSP pipeline (`drums`, `bass`, `chords`, `melody`).<br>• Development of voiceover ducking algorithm with smooth IIR envelope filter.<br>• Creation of the FastAPI service, asynchronous job worker, idempotency manager, and OpenAPI 3.1 specification.<br>• Writing and executing the comprehensive 21-test pytest suite.<br>• Implementing batch runner CLI, metrics evaluation, and Docker configuration. |

---

## 2. Specific Contributions & Code Areas

### Architectural Decisions
- Guided the separation of the heavy, research-only transformer approach into a fast, commercially licensed multi-track procedural synthesis engine with zero model weight dependencies.
- Structured the service around OpenAPI 3.1, asynchronous background workers (HTTP 202), and strict Idempotency-Key caching.

### Audio DSP Implementation
- Assisted in formulating the ITU-R BS.1770-4 loudness normalization and peak limiter in `app/engine/audio_renderer.py`.
- Formulated the physical drum synthesis, resonant subtractive bass, polyphonic chord voicings, and lead melody oscillator in `app/engine/stem_composer.py`.
- Formulated the asymmetric IIR smoothing filter (attack/release) for voiceover sidechain ducking in `app/engine/ducking.py`.

### Verification and Quality Assurance
- Developed automated tests covering edge durations (5s to 300s), vague/contradictory prompts, copyright prompt screening, non-English prompts, and stem linear reconstruction.
- All code logic was verified by executing real tests and inspecting generated audio files.
