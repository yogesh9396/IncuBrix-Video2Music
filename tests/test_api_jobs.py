import time
import pytest


def test_health_and_readiness(client):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


def test_job_submission_and_polling(client, mock_job_request):
    res = client.post("/api/v1/music/jobs", json=mock_job_request)
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll until succeeded (mock provider finishes in < 1 second)
    max_wait = 10
    start = time.time()
    succeeded = False
    while time.time() - start < max_wait:
        poll_res = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "succeeded":
            succeeded = True
            assert poll_data["progress"] == 100
            assert poll_data["result"] is not None
            assert "mix_url" in poll_data["result"]
            assert "stems" in poll_data["result"]
            assert "drums" in poll_data["result"]["stems"]
            assert "manifest_url" in poll_data["result"]
            break
        time.sleep(0.2)

    assert succeeded, f"Job {job_id} did not succeed within {max_wait}s"


def test_idempotency_safe_retries(client, mock_job_request):
    idem_key = "test-idem-key-12345"
    headers = {"Idempotency-Key": idem_key}

    # First request
    res1 = client.post("/api/v1/music/jobs", json=mock_job_request, headers=headers)
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    # Second request with exact same payload and key
    res2 = client.post("/api/v1/music/jobs", json=mock_job_request, headers=headers)
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]

    # Must return identical job_id
    assert job_id_1 == job_id_2

    # Third request with differing payload and same key must return 409 Conflict
    conflicting_req = mock_job_request.copy()
    conflicting_req["duration_s"] = 25.0
    res3 = client.post("/api/v1/music/jobs", json=conflicting_req, headers=headers)
    assert res3.status_code == 409
    err = res3.json()["error"]
    assert err["code"] == "IDEMPOTENCY_CONFLICT"


def test_invalid_duration_error(client, mock_job_request):
    # Duration < 5s
    bad_req = mock_job_request.copy()
    bad_req["duration_s"] = 2.0
    res = client.post("/api/v1/music/jobs", json=bad_req)
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_DURATION"


def test_job_not_found(client):
    res = client.get("/api/v1/jobs/non-existent-uuid-999")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "JOB_NOT_FOUND"
