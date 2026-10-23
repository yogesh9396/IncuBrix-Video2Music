import math
import os
import tempfile
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import requests
import soundfile as sf
from scipy.signal import resample_poly

logger = logging.getLogger(__name__)


def load_audio_from_source(source: str, target_sr: int = 48000) -> np.ndarray:
    """
    Loads audio from either a URL (HTTP/HTTPS) or a local file path,
    resamples to target_sr, and converts to mono.
    """
    temp_file = None
    try:
        if source.startswith("http://") or source.startswith("https://"):
            logger.info(f"Downloading narration audio from URL: {source}")
            resp = requests.get(source, timeout=15)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(resp.content)
                temp_file = f.name
            audio_path = temp_file
        else:
            audio_path = source

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Narration audio not found at: {audio_path}")

        data, sr = sf.read(audio_path)
        # Convert to mono if multi-channel
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        # Resample if needed
        if sr != target_sr:
            gcd = math.gcd(sr, target_sr)
            up = target_sr // gcd
            down = sr // gcd
            data = resample_poly(data, up, down)

        return data.astype(np.float32)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass


def compute_ducking_envelope(
    speech_audio: np.ndarray,
    target_samples: int,
    sample_rate: int = 48000,
    duck_db: float = -12.0,
    attack_ms: float = 150.0,
    release_ms: float = 450.0,
    energy_threshold_db: float = -38.0
) -> Tuple[np.ndarray, List[Dict[str, float]]]:
    """
    Computes a smooth voiceover ducking gain envelope:
    - Drops by duck_db (default -12 dB, range 8-15 dB) under speech.
    - Smooth attack and release curves with no pumping.
    - Generates a downsampled volume curve for the manifest.
    """
    # Align speech length to music target length
    if len(speech_audio) < target_samples:
        padded = np.zeros(target_samples, dtype=np.float32)
        padded[:len(speech_audio)] = speech_audio
        speech_aligned = padded
    else:
        speech_aligned = speech_audio[:target_samples]

    frame_size = int(0.020 * sample_rate)  # 20ms frames
    hop_size = int(0.010 * sample_rate)    # 10ms hops
    num_hops = max(1, (target_samples - frame_size) // hop_size + 1)

    # Compute short-time RMS energy in dBFS
    min_gain_linear = 10.0 ** (duck_db / 20.0)  # e.g. -12 dB ~ 0.251
    raw_gains = np.ones(num_hops, dtype=np.float32)

    for i in range(num_hops):
        start = i * hop_size
        frame = speech_aligned[start : start + frame_size]
        rms = np.sqrt(np.mean(frame ** 2) + 1e-12)
        rms_db = 20.0 * np.log10(rms)

        if rms_db > energy_threshold_db:
            # Speech detected: duck music
            raw_gains[i] = min_gain_linear
        else:
            raw_gains[i] = 1.0

    # Smooth the gain curve using asymmetric IIR attack/release filter
    dt = hop_size / sample_rate
    attack_coeff = 1.0 - math.exp(-dt / (attack_ms / 1000.0))
    release_coeff = 1.0 - math.exp(-dt / (release_ms / 1000.0))

    smoothed_gains = np.ones(num_hops, dtype=np.float32)
    current_gain = 1.0
    for i in range(num_hops):
        target = raw_gains[i]
        if target < current_gain:
            # Ducking (attack)
            current_gain += attack_coeff * (target - current_gain)
        else:
            # Recovery (release)
            current_gain += release_coeff * (target - current_gain)
        smoothed_gains[i] = current_gain

    # Interpolate smoothed hop gains back to full audio sample length
    hop_times = np.arange(num_hops) * hop_size + (frame_size // 2)
    sample_indices = np.arange(target_samples)
    full_envelope = np.interp(sample_indices, hop_times, smoothed_gains).astype(np.float32)

    # Downsample volume curve for manifest points (every 200ms)
    points_interval = int(0.200 * sample_rate)
    manifest_curve = []
    for idx in range(0, target_samples, points_interval):
        t_sec = round(idx / sample_rate, 2)
        gain_val = float(full_envelope[idx])
        gain_db_val = round(float(20.0 * math.log10(max(1e-4, gain_val))), 2)
        manifest_curve.append({"time_s": t_sec, "gain_db": gain_db_val})

    return full_envelope, manifest_curve


def apply_ducking(
    mix_audio: np.ndarray,
    narration_source: str,
    sample_rate: int = 48000,
    duck_db: float = -12.0
) -> Tuple[np.ndarray, List[Dict[str, float]]]:
    """
    Loads narration, calculates smooth ducking curve, and applies it to mix_audio.
    Voiceover itself is not included in the returned audio.
    """
    target_samples = len(mix_audio)
    speech = load_audio_from_source(narration_source, target_sr=sample_rate)
    envelope, curve_points = compute_ducking_envelope(
        speech,
        target_samples=target_samples,
        sample_rate=sample_rate,
        duck_db=duck_db
    )

    if mix_audio.ndim == 2:
        ducked_audio = mix_audio * envelope[:, np.newaxis]
    else:
        ducked_audio = mix_audio * envelope

    return ducked_audio, curve_points
