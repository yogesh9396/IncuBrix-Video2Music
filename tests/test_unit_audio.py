import numpy as np
import pytest
from app.engine.audio_renderer import (
    normalize_to_target_lufs,
    measure_loudness,
    compute_reconstruction_error_db,
    sum_stems_with_gains
)
from app.engine.ducking import compute_ducking_envelope


def test_lufs_normalization_and_true_peak():
    sr = 48000
    duration_s = 5.0
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    # Generate multi-frequency synthetic signal
    audio = 0.5 * np.sin(2.0 * np.pi * 440.0 * t) + 0.25 * np.sin(2.0 * np.pi * 880.0 * t)
    
    target_lufs = -16.0
    max_dbtp = -1.0
    normalized, actual_lufs, actual_dbtp = normalize_to_target_lufs(
        audio, sample_rate=sr, target_lufs=target_lufs, max_dbtp=max_dbtp
    )

    # Must be within 1.0 LU of target
    assert abs(actual_lufs - target_lufs) <= 1.0, f"LUFS {actual_lufs} not within 1 LU of {target_lufs}"
    # True peak must be <= -1.0 dBTP
    assert actual_dbtp <= max_dbtp + 0.05, f"True peak {actual_dbtp} exceeds max {max_dbtp} dBTP"


def test_stem_linear_reconstruction():
    sr = 48000
    n_samples = 48000 * 3
    t = np.linspace(0, 3, n_samples, endpoint=False)

    stems = {
        "drums": (0.3 * np.sin(2 * np.pi * 60 * t)).astype(np.float32),
        "bass": (0.4 * np.sin(2 * np.pi * 120 * t)).astype(np.float32),
        "chords": (0.25 * np.sin(2 * np.pi * 440 * t)).astype(np.float32),
        "melody": (0.2 * np.sin(2 * np.pi * 880 * t)).astype(np.float32),
    }

    gains = {"drums": 0.85, "bass": 0.80, "chords": 0.70, "melody": 0.75}

    mix = sum_stems_with_gains(stems, gains)
    recon_error = compute_reconstruction_error_db(mix, stems, gains)

    # Reconstruction error must be virtually negative infinity (numerically < -100 dB)
    assert recon_error <= -100.0, f"Reconstruction error {recon_error} dB is too high"


def test_voiceover_ducking_envelope():
    sr = 48000
    total_samples = sr * 4  # 4 seconds

    # Speech in seconds 1.0 to 2.5
    speech = np.zeros(total_samples, dtype=np.float32)
    speech_start = int(1.0 * sr)
    speech_end = int(2.5 * sr)
    t_speech = np.linspace(0, 1.5, speech_end - speech_start, endpoint=False)
    speech[speech_start:speech_end] = 0.6 * np.sin(2 * np.pi * 300 * t_speech)

    envelope, curve_points = compute_ducking_envelope(
        speech_audio=speech,
        target_samples=total_samples,
        sample_rate=sr,
        duck_db=-12.0
    )

    # During initial silence (t=0.2s), gain should be near 1.0 (0 dB)
    idx_silence = int(0.2 * sr)
    assert envelope[idx_silence] >= 0.95

    # During speech (t=1.8s), gain should be ducked close to -12 dB (approx 0.25)
    idx_speech = int(1.8 * sr)
    assert envelope[idx_speech] <= 0.35

    # After speech ends (t=3.8s), gain should recover smoothly towards 1.0
    idx_recovery = int(3.8 * sr)
    assert envelope[idx_recovery] >= 0.90

    # Volume curve points must be populated
    assert len(curve_points) > 0
