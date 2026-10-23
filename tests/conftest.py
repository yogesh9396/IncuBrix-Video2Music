import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

# Set testing environment before importing app
os.environ["ENV"] = "testing"
os.environ["MUSIC_PROVIDER"] = "mock"
temp_dir = tempfile.mkdtemp(prefix="incubrix_test_")
os.environ["STORAGE_LOCAL_DIR"] = temp_dir

from app.main import app
from app.config import settings
from app.storage.storage_service import storage_service


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    # Cleanup temp directory
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def mock_job_request():
    return {
        "prompt": "warm, optimistic acoustic pop for a product launch",
        "duration_s": 10.0,
        "tempo_bpm": 120.0,
        "key": "C major",
        "loopable": False,
        "output": {
            "sample_rate": 48000,
            "target_lufs": -16.0,
            "formats": ["wav", "mp3"]
        }
    }
