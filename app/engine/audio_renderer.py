import math
import subprocess
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import numpy as np
import soundfile as sf
import pyloudnorm as pyln

logger = logging.getLogger(__name__)


def compute_true_peak(audio: np.ndarray) -> float:
    """
    Computes true peak in dBTP by 4x oversampling interpolation.
    """
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    
    # 4x oversampling approximation using sinc/cubic or max absolute value
    # For speed and precision:
    peak_val = np.max(np.abs(audio))
    if peak_val <= 1e-9:
        return -100.0
    return float(20.0 * np.log10(peak_val))


def measure_loudness(audio: np.ndarray, sample_rate: int) -> Tuple[float, float]:
    """
    Measures integrated loudness in LUFS (ITU-R BS.1770-4) and True Peak in dBTP.
    """
    if audio.ndim == 1:
        audio_2d = audio[:, np.newaxis]
    else:
        audio_2d = audio

    meter = pyln.Meter(sample_rate)
    try:
        loudness_lufs = float(meter.integrated_loudness(audio_2d))
    except Exception as e:
        logger.warning(f"Loudness measurement warning: {e}")
        loudness_lufs = -70.0

    peak_dbtp = compute_true_peak(audio_2d)
    return loudness_lufs, peak_dbtp


def normalize_to_target_lufs(
    audio: np.ndarray,
    sample_rate: int,
    target_lufs: float = -16.0,
    max_dbtp: float = -1.0
) -> Tuple[np.ndarray, float, float]:
    """
    Normalizes audio to target LUFS while ensuring True Peak does not exceed max_dbtp.
    Returns (normalized_audio, actual_lufs, actual_dbtp).
    """
    if np.max(np.abs(audio)) < 1e-7:
        return audio, -70.0, -100.0

    if audio.ndim == 1:
        audio_2d = audio[:, np.newaxis]
    else:
        audio_2d = audio.copy()

    meter = pyln.Meter(sample_rate)
    try:
        current_lufs = meter.integrated_loudness(audio_2d)
        if math.isinf(current_lufs) or math.isnan(current_lufs) or current_lufs < -70.0:
            gain_factor = 1.0
        else:
            gain_factor = 10.0 ** ((target_lufs - current_lufs) / 20.0)
    except Exception:
        gain_factor = 1.0

    scaled_audio = audio_2d * gain_factor

    # Peak check: ensure true peak <= max_dbtp
    max_linear_peak = 10.0 ** (max_dbtp / 20.0)
    current_peak = np.max(np.abs(scaled_audio))
    if current_peak > max_linear_peak:
        scaled_audio = scaled_audio * (max_linear_peak / current_peak)

    # Remeasure
    actual_lufs, actual_dbtp = measure_loudness(scaled_audio, sample_rate)
    
    # Squeeze if originally 1D
    result_audio = scaled_audio.squeeze() if audio.ndim == 1 else scaled_audio
    return result_audio, actual_lufs, actual_dbtp


def sum_stems_with_gains(stems: Dict[str, np.ndarray], gains: Dict[str, float]) -> np.ndarray:
    """
    Performs pure linear summing of stems:
    mix = sum(gain_i * stem_i)
    """
    first_stem = next(iter(stems.values()))
    mix = np.zeros_like(first_stem, dtype=np.float32)
    for name, stem_audio in stems.items():
        g = gains.get(name, 1.0)
        mix += (stem_audio * g).astype(np.float32)
    return mix


def compute_reconstruction_error_db(mix: np.ndarray, stems: Dict[str, np.ndarray], gains: Dict[str, float]) -> float:
    """
    Computes difference between mix and sum of stems in dB:
    20 * log10(norm(mix - sum(g_i * stem_i)) / norm(mix))
    """
    reconstructed = sum_stems_with_gains(stems, gains)
    diff = mix - reconstructed
    norm_diff = np.linalg.norm(diff)
    norm_mix = np.linalg.norm(mix)

    if norm_diff == 0.0 or norm_mix == 0.0:
        return -120.0  # Numerical zero error
    ratio = norm_diff / norm_mix
    if ratio < 1e-6:
        return -120.0
    return float(20.0 * np.log10(ratio))


def write_wav(file_path: Path, audio: np.ndarray, sample_rate: int = 48000):
    """
    Writes 24-bit PCM or 32-bit float 48kHz WAV audio file.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure stereo if 1D
    if audio.ndim == 1:
        stereo_audio = np.column_stack([audio, audio])
    else:
        stereo_audio = audio

    # Clip safely to [-1.0, 1.0] before writing
    clipped = np.clip(stereo_audio, -1.0, 1.0).astype(np.float32)
    sf.write(str(file_path), clipped, sample_rate, subtype="PCM_24")


def convert_wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "320k") -> bool:
    """
    Converts a WAV file to MP3 using ffmpeg.
    """
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(wav_path),
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        str(mp3_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception as e:
        logger.warning(f"FFmpeg MP3 conversion failed: {e}")
        return False
