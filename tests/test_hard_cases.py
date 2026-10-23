import time
import numpy as np
import pytest
from app.models.schemas import MusicJobRequest
from app.engine.stem_composer import StemComposer, sanitize_prompt


def test_hard_case_boundary_durations(client):
    """Test very short (5s) and maximum allowed duration (300s / 5 minutes)."""
    composer = StemComposer(sample_rate=48000)

    # 5.0s track
    stems_short, _, _ = composer.compose("short sting", duration_s=5.0)
    assert abs(len(stems_short["drums"]) / 48000.0 - 5.0) <= 0.05

    # API boundary rejection for < 5s (e.g. 3s) and > 300s (e.g. 350s)
    res_under = client.post("/api/v1/music/jobs", json={"prompt": "too short", "duration_s": 3.0})
    assert res_under.status_code == 422
    assert res_under.json()["error"]["code"] == "INVALID_DURATION"

    res_over = client.post("/api/v1/music/jobs", json={"prompt": "too long", "duration_s": 350.0})
    assert res_over.status_code == 422
    assert res_over.json()["error"]["code"] == "INVALID_DURATION"


def test_hard_case_contradictory_prompt(client):
    """Test contradictory prompt like 'calm but aggressive'."""
    composer = StemComposer(sample_rate=48000)
    stems, gains, meta = composer.compose("calm but aggressive high energy meditation", duration_s=10.0)
    assert len(stems) == 4
    # Ensure system does not crash and produces valid audio
    assert not np.isnan(stems["drums"]).any()


def test_hard_case_copyright_and_artist_prompt():
    """Test prompt naming real artist and requesting vocals."""
    prompt = "remix Shape of You by Ed Sheeran with Hans Zimmer orchestra and female vocals"
    sanitized, warnings = sanitize_prompt(prompt)

    assert "ed sheeran" not in sanitized.lower()
    assert "hans zimmer" not in sanitized.lower()
    assert len(warnings) >= 3


def test_hard_case_non_english_prompt(client):
    """Test non-English prompts (e.g., German, French, Tamil transliterated)."""
    prompts = [
        "musique cinématographique dramatique",
        "entspannende Klaviermusik für Video",
        "cinematic action bgm fast rhythm"
    ]
    composer = StemComposer(sample_rate=48000)
    for p in prompts:
        stems, _, meta = composer.compose(p, duration_s=6.0)
        assert len(stems) == 4


def test_hard_case_invalid_sections(client):
    """Test section changes < 1.5s apart and section after track end."""
    # Section gap < 1.5s
    bad_req1 = {
        "prompt": "dynamic video music",
        "duration_s": 20.0,
        "sections": [
            {"start_s": 0.0, "mood": "intro"},
            {"start_s": 0.8, "mood": "build"}  # 0.8s gap is < 1.5s
        ]
    }
    res1 = client.post("/api/v1/music/jobs", json=bad_req1)
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "INVALID_SECTIONS"

    # Section starting after track end
    bad_req2 = {
        "prompt": "dynamic video music",
        "duration_s": 15.0,
        "sections": [
            {"start_s": 0.0, "mood": "intro"},
            {"start_s": 20.0, "mood": "too late"}  # 20.0s > 15.0s
        ]
    }
    res2 = client.post("/api/v1/music/jobs", json=bad_req2)
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "INVALID_SECTIONS"


def test_hard_case_silent_narration():
    """Test narration file with pure silence."""
    from app.engine.ducking import compute_ducking_envelope
    sr = 48000
    samples = sr * 5
    silent_speech = np.zeros(samples, dtype=np.float32)

    envelope, curve = compute_ducking_envelope(silent_speech, samples, sample_rate=sr)
    # Gain should remain at 1.0 (no ducking) throughout pure silence
    assert np.all(envelope >= 0.99)


def test_hard_case_concurrent_jobs(client):
    """Test two concurrent jobs submitted simultaneously."""
    req1 = {"prompt": "cinematic tension theme", "duration_s": 8.0}
    req2 = {"prompt": "upbeat electronic dance", "duration_s": 8.0}

    res1 = client.post("/api/v1/music/jobs", json=req1)
    res2 = client.post("/api/v1/music/jobs", json=req2)

    assert res1.status_code == 202
    assert res2.status_code == 202

    id1 = res1.json()["job_id"]
    id2 = res2.json()["job_id"]
    assert id1 != id2
