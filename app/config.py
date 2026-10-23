import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service Environment
    ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SERVICE_NAME: str = "incubrix-music-engine"
    API_PREFIX: str = "/api/v1"

    # Generation Engine & Providers
    # Options: "synth" (built-in 4-stem multitrack synth), "mock" (fast test mock), "fluidsynth"
    MUSIC_PROVIDER: str = "synth"
    SEED_DEFAULT: int = 42

    # Storage Settings
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    STORAGE_LOCAL_DIR: str = str(Path(__file__).resolve().parent.parent / "storage_data")
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_BUCKET_NAME: str = "incubrix-audio"
    S3_ACCESS_KEY: Optional[str] = "minioadmin"
    S3_SECRET_KEY: Optional[str] = "minioadmin"
    S3_REGION: str = "us-east-1"

    # Audio Limits & Standards
    MIN_DURATION_S: float = 5.0
    MAX_DURATION_S: float = 300.0
    DEFAULT_SAMPLE_RATE: int = 48000
    DEFAULT_TARGET_LUFS: float = -16.0
    MAX_TRUE_PEAK_DBTP: float = -1.0
    SUPPORTED_FORMATS: List[str] = ["wav", "mp3"]

    # External Tools & Soundfont
    FLUIDSYNTH_BIN: str = "C:\\tools\\fluidsynth\\bin\\fluidsynth.exe" if os.name == "nt" else "fluidsynth"
    SOUNDFONT_PATH: Optional[str] = (
        "D:\\ai background music\\Video2Music\\soundfonts\\default_sound_font.sf2"
        if os.path.exists("D:\\ai background music\\Video2Music\\soundfonts\\default_sound_font.sf2")
        else None
    )

    # Security & Webhook Callback
    WEBHOOK_SECRET: str = "incubrix_secret_key_demo"
    WEBHOOK_TIMEOUT_S: float = 10.0

    # Job Concurrency & Timeout
    MAX_CONCURRENT_JOBS: int = 2
    JOB_TIMEOUT_S: int = 300
    IDEMPOTENCY_EXPIRY_S: int = 86400  # 24 hours

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
