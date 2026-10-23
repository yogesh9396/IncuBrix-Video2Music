import json
import time
import numpy as np
import soundfile as sf
import pytest

from app.engine.audio_renderer import measure_loudness, compute_reconstruction_error_db


def test_full_e2e_audio_generation(client):
    req_payload = {
        "prompt": "inspiring corporate acoustic presentation with uplifting finish",
        "duration_s": 8.0,
        "tempo_bpm": 120.0,
        "key": "C major",
        "loopable": True,
        "sections": [
            {"start_s": 0.0, "mood": "intro"},
            {"start_s": 4.0, "mood": "uplifting finish"}
        ],
        "output": {
            "sample_rate": 48000,
            "target_lufs": -16.0,
            "formats": ["wav", "mp3"]
        }
    }

    # Override provider to real synth provider for e2e
    res = client.post("/api/v1/music/jobs?provider=synth", json=req_payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    # Poll for completion
    max_wait = 25
    start = time.time()
    succeeded = False
    poll_data = {}

    while time.time() - start < max_wait:
        poll_res = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "succeeded":
            succeeded = True
            break
        elif poll_data["status"] == "failed":
            pytest.fail(f"Job failed with error: {poll_data.get('error')}")
        time.sleep(0.5)

    assert succeeded, f"E2E Job {job_id} did not finish within {max_wait}s"

    # Verify download links
    result_links = poll_data["result"]
    assert "mix_url" in result_links
    assert "stems" in result_links
    assert len(result_links["stems"]) == 4

    # Download mix.wav
    mix_res = client.get(result_links["mix_url"])
    assert mix_res.status_code == 200
    assert mix_res.headers["content-type"] == "audio/wav"

    # Download manifest
    manifest_res = client.get(result_links["manifest_url"])
    assert manifest_res.status_code == 200
    manifest = manifest_res.json()

    assert manifest["job_id"] == job_id
    assert abs(manifest["actual_duration_s"] - 8.0) <= 0.05
    assert manifest["tempo_bpm"] == 120.0
    assert manifest["key"] == "C major"
    assert manifest["licence_rights"]["commercial_use_permitted"] is True

    # Download all 4 stems
    stems_audio = {}
    for s_name, s_url in result_links["stems"].items():
        stem_res = client.get(s_url)
        assert stem_res.status_code == 200
        # Check stem content non-empty
        assert len(stem_res.content) > 1000
