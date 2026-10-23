# IncuBrix AI Background Music Engine for Video

An asynchronous, containerised audio microservice that transforms video mood descriptions and timing cuts into original, commercially safe instrumental music. The service delivers a fully mastered mix along with genuine, isolated instrument stems (`drums`, `bass`, `chords`, `melody`) that add back up to the master mix with mathematical precision.

---

## 1. Architecture Overview

```mermaid
flowchart TD
    Client["Client / Video Editor"] -->|POST /api/v1/music/jobs<br>Idempotency-Key| Gateway["FastAPI API Gateway"]
    Gateway -->|202 Accepted + job_id| Client
    Gateway --> JobMgr["Job Manager & Idempotency Store"]
    
    subgraph Execution ["Asynchronous Audio Pipeline"]
        JobMgr --> Composer["StemComposer & Grid Planner"]
        Composer --> MultiTrack["Multi-Track Synthesis Engine"]
        MultiTrack --> S1["Drums Stem (WAV 48kHz)"]
        MultiTrack --> S2["Bass Stem (WAV 48kHz)"]
        MultiTrack --> S3["Chords Stem (WAV 48kHz)"]
        MultiTrack --> S4["Melody Stem (WAV 48kHz)"]
        
        S1 & S2 & S3 & S4 --> Sum["Linear Mix Sum: M = ∑ g_i * S_i"]
        Sum --> Norm["Loudness Normalizer (-16 LUFS, <= -1 dBTP)"]
        
        Norm --> Duck["Voiceover Ducking (-12 dB, Speech Activity)"]
        Norm --> MP3["FFmpeg MP3 320k Encoder"]
    end
    
    Execution --> Storage["Storage Service (Local / S3 MinIO)"]
    Storage --> Artifacts["mix.wav, mix.mp3, stems/*.wav, mix_ducked.wav, music_manifest.json"]
    Client -->|GET /api/v1/jobs/{id}| Gateway
    Gateway -->|Download Links & Status| Client
```

---

## 2. Key Features

- **Genuine Isolated Stems**: Delivers four distinct instrument stems (`drums`, `bass`, `chords`, `melody`). Not frequency-split; zero crosstalk bleed between stems (measured at $-120\text{ dB}$).
- **Exact Duration Control**: Audio matches requested length within $0.05\text{ s}$ and ends on a musical release fade, never a hard cut.
- **Section-Based Energy Shifts**: Supports cut points with mood and energy transitions that land precisely on beat and bar lines.
- **Broadcast Loudness Compliance**: Master mix normalized to **$-16.0\text{ LUFS}$** ($\pm 1.0\text{ LU}$) with True Peak at or below **$-1.0\text{ dBTP}$** using ITU-R BS.1770-4 metering.
- **Voiceover Sidechain Ducking**: Automatically attenuates music by $-12\text{ dB}$ during speech with smooth attack/release envelopes, exporting `mix_ducked.wav` and downsampled volume curves.
- **Single Stem Regeneration**: Allows selective regeneration of individual instrument stems (e.g. regenerating `drums` without modifying `bass` or `chords`).
- **Seamless Looping**: When `loopable: true`, applies boundary phase crossfading to eliminate seam clicks.
- **Production Integration Standard**: OpenAPI 3.1 specification, asynchronous HTTP 202 jobs, `Idempotency-Key` duplicate prevention, structured JSON errors, health/readiness probes, and webhook callback signing (`HMAC-SHA256`).

---

## 3. Quickstart in Under 10 Commands

### Option A: Local Python Environment

```powershell
# 1. Navigate to submission directory
cd "D:\ai background music\IncuBrix_Submission"

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Set Python path
$env:PYTHONPATH = "D:\ai background music\IncuBrix_Submission"

# 4. Run automated test suite (21 tests pass in ~4 seconds)
python -m pytest tests -v

# 5. Start the API service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option B: Docker Compose

```bash
# 1. Start application service and MinIO storage
docker compose up -d

# 2. Run automated tests inside container
docker compose exec incubrix-music-engine pytest tests -v
```

---

## 4. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/music/jobs` | Submits a music generation job (Returns `202 Accepted` with `job_id`). |
| `GET` | `/api/v1/jobs/{job_id}` | Polls job progress (`0-100%`) and retrieves artifact download links. |
| `POST` | `/api/v1/music/jobs/{job_id}/regenerate-stem` | Regenerates a single stem while keeping all other stems intact. |
| `POST` | `/api/v1/upload` | Uploads narration/voiceover audio for sidechain ducking. |
| `GET` | `/api/v1/artifacts/{job_id}/{file_path}` | Downloads audio files (`mix.wav`, `mix.mp3`, `stems/*.wav`, `music_manifest.json`). |
| `GET` | `/health` | Liveness health check probe. |
| `GET` | `/ready` | Readiness check probe verifying storage and audio engine status. |

### Example API Request

```bash
curl -X POST "http://localhost:8000/api/v1/music/jobs" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: job-launch-demo-001" \
  -d '{
    "prompt": "warm, optimistic acoustic pop for a product launch, builds to an uplifting finish",
    "duration_s": 45.0,
    "sections": [
      {"start_s": 0.0, "mood": "calm intro"},
      {"start_s": 12.5, "mood": "build-up"},
      {"start_s": 30.0, "mood": "uplifting peak"}
    ],
    "tempo_bpm": 110.0,
    "key": "C major",
    "loopable": false,
    "seed": 42,
    "output": {"sample_rate": 48000, "target_lufs": -16.0, "formats": ["wav", "mp3"]}
  }'
```

---

## 5. Structured Error Codes

Errors conform strictly to the standard JSON format:  
`{"error": {"code": "UPPER_SNAKE_CASE", "message": "...", "retryable": bool, "details": ...}}`

| Error Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `INVALID_DURATION` | `422` | Requested duration is less than $5.0\text{ s}$ or greater than $300.0\text{ s}$. |
| `INVALID_SECTIONS` | `422` | Section interval is $< 1.5\text{ s}$ or section starts after track duration. |
| `IDEMPOTENCY_CONFLICT` | `409` | Same idempotency key reused with different request payload. |
| `JOB_NOT_FOUND` | `404` | Specified `job_id` does not exist. |
| `INVALID_STEM` | `400` | Stem name specified for regeneration is not recognized. |
| `INTERNAL_SERVER_ERROR`| `500` | Unexpected server execution exception. |

---

## 6. Batch Runner CLI

To execute a batch test run over an entire folder of input JSON specifications:

```powershell
python scripts/batch_runner.py --input-path test_pack/inputs --output-dir test_pack/outputs
```

Results and manifests are automatically compiled into `test_pack/outputs/batch_summary.json`.

---

## 7. Configuration Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENV` | `development` | Deployment environment (`development`, `production`, `testing`). |
| `MUSIC_PROVIDER` | `synth` | Provider engine (`synth`, `mock`, `fluidsynth`). |
| `STORAGE_TYPE` | `local` | Storage mode (`local` or `s3`). |
| `STORAGE_LOCAL_DIR` | `./storage_data` | Directory for local artifact persistence. |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | S3 / MinIO endpoint URL. |
| `DEFAULT_SAMPLE_RATE` | `48000` | Audio rendering sample rate in Hz. |
| `DEFAULT_TARGET_LUFS`| `-16.0` | Broadcast target loudness in LUFS. |
| `MAX_TRUE_PEAK_DBTP` | `-1.0` | Maximum allowable True Peak level. |
| `WEBHOOK_SECRET` | `incubrix_secret_key_demo` | HMAC-SHA256 signing secret for webhook callbacks. |
