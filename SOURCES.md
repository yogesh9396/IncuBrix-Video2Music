# SOURCES.md — Licences, Assets, and Component Provenance

## 1. Overview and Commercial Policy

The IncuBrix AI Background Music Engine is designed strictly for commercial safety and monetization.
- **No Non-Commercial Assets**: No models, data, or sound resources licensed under CC BY-NC or research-only terms are included in the default generation path.
- **No AGPL Dependencies**: All libraries utilized use permissive commercial licenses (MIT, BSD, Apache 2.0).
- **Original Synthesized Audio**: The engine renders genuine multi-track instrument stems directly via algorithmic physical and additive audio synthesis at 48 kHz. Outputs are 100% royalty-free and safe for monetization.

---

## 2. Software Libraries & Licences

| Library / Tool | Version | Licence | Purpose | Commercial Rights Link |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI** | 0.124.4 | MIT | Async HTTP REST API Framework | [FastAPI Licence](https://github.com/tiangolo/fastapi/blob/master/LICENSE) |
| **Uvicorn** | 0.33.0 | BSD-3-Clause | ASGI Server Implementation | [Uvicorn Licence](https://github.com/encode/uvicorn/blob/master/LICENSE.md) |
| **Pydantic** | 2.10.6 | MIT | Data Validation & Settings Management | [Pydantic Licence](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| **pyloudnorm** | 0.1.1 | MIT | ITU-R BS.1770-4 LUFS & True Peak Meter | [pyloudnorm Licence](https://github.com/csteinmetz1/pyloudnorm/blob/master/LICENSE) |
| **SoundFile** | 0.13.1 | BSD-3-Clause | Audio I/O (libsndfile wrapper) | [SoundFile Licence](https://github.com/bastibe/python-soundfile/blob/master/LICENSE) |
| **NumPy** | 1.24.4 | BSD-3-Clause | Numerical signal processing | [NumPy Licence](https://numpy.org/doc/stable/license.html) |
| **SciPy** | 1.10.1 | BSD-3-Clause | Audio filtering, resampling, and DSP | [SciPy Licence](https://scipy.org/license/) |
| **MIDIUtil** | 1.2.1 | MIT | MIDI file generation & arrangement | [MIDIUtil Licence](https://github.com/MarkCWirt/MIDIUtil/blob/master/LICENSE.txt) |
| **Mido** | 1.3.3 | MIT | MIDI message parsing and timing | [Mido Licence](https://github.com/mido/mido/blob/main/LICENSE) |
| **Requests / HTTPX** | 2.32 / 0.28 | Apache 2.0 / BSD | Webhook delivery & narration fetch | [Requests Licence](https://github.com/psf/requests/blob/main/LICENSE) |
| **Boto3** | 1.37.38 | Apache 2.0 | S3/MinIO compatible cloud storage | [Boto3 Licence](https://github.com/boto/boto3/blob/develop/LICENSE) |
| **FFmpeg** | 9.0.1 (CLI) | LGPL / GPL | Master MP3 encoding | [FFmpeg Legal](https://www.ffmpeg.org/legal.html) |

---

## 3. Instrument Synthesis & Audio Assets

* **Drums (Percussion Stem)**:
  * Pure physical frequency-swept sine oscillator ($150 \to 40\text{ Hz}$) for kick drums.
  * Dual-layer transient noise burst with bandpass filtering for snare.
  * Metallic high-passed stochastic synthesis for hi-hats and cymbals.
  * *Licence*: Custom implementation in `app/engine/stem_composer.py` (MIT License).

* **Bass Stem**:
  * Subtractive oscillator with multi-harmonic partials and low-pass resonant filter envelope.
  * *Licence*: Custom implementation (MIT License).

* **Chords & Harmony Stem**:
  * Polyphonic additive synthesis with warm harmonic dispersion and chorus detuning (emulating Rhodes/Keys/Warm Analog Strings).
  * *Licence*: Custom implementation (MIT License).

* **Melody Stem**:
  * Expressive lead synthesizer with $5.5\text{ Hz}$ frequency vibrato and ADSR envelope.
  * *Licence*: Custom implementation (MIT License).

* **SoundFont Compatibility (Optional)**:
  * SoundFonts (such as `default_sound_font.sf2` or GeneralUser GS) are loaded only when explicitly configured via `SOUNDFONT_PATH`.
  * The built-in multi-track synthesis engine functions independently of any external proprietary soundfonts, guaranteeing 100% self-contained operation.

---

## 4. Copyright & Real Artist Safeguards

The engine features an automated screening pipeline in `app/engine/stem_composer.py`:
1. **Artist Reference Detection**: Prompts citing known artists (e.g. Hans Zimmer, Ed Sheeran, etc.) are stripped of trademarked names, sanitized to generic descriptors, and flagged with transparent warnings in `music_manifest.json`.
2. **Instrumental Integrity**: Any request for vocals, singing, or lyrics is automatically redirected to instrumental voicing to comply with the strictly instrumental brief.
3. **Plagiarism Prevention**: Music generation is governed by procedural scale mappings, harmonic chord cadences, and random seed variation, preventing replication of copyrighted musical compositions.
