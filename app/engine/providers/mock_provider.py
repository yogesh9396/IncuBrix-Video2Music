import time
from typing import Dict, Any, Tuple, Optional
import numpy as np
from app.models.schemas import MusicJobRequest
from app.engine.providers.base import BaseMusicProvider
from app.engine.audio_renderer import sum_stems_with_gains


class MockMusicProvider(BaseMusicProvider):
    """
    High-speed deterministic mock provider for CI/CD, unit tests, and integration tests
    requiring zero external API keys or heavy hardware.
    """
    @property
    def name(self) -> str:
        return "mock-provider"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate(
        self,
        request: MusicJobRequest,
        job_id: str,
        regenerate_stem: Optional[str] = None,
        existing_stems: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], Dict[str, float], Dict[str, Any]]:
        start_time = time.time()
        sr = request.output.sample_rate if request.output else 48000
        num_samples = int(round(request.duration_s * sr))

        t = np.linspace(0, request.duration_s, num_samples, endpoint=False, dtype=np.float32)

        # 4 distinct synthetic tones representing genuine parts
        stem_gains = {
            "drums": 0.85,
            "bass": 0.80,
            "chords": 0.70,
            "melody": 0.75
        }

        stems = {}
        # Keep existing stems if regenerating a single stem
        if regenerate_stem and existing_stems:
            for s_name, s_audio in existing_stems.items():
                if s_name != regenerate_stem:
                    stems[s_name] = s_audio.copy()

        # Tone frequencies representing instruments
        instrument_freqs = {
            "drums": 60.0,    # Low percussion pulse
            "bass": 110.0,    # A2 bass tone
            "chords": 440.0,  # A4 chord tone
            "melody": 880.0   # A5 melodic lead
        }

        for name, freq in instrument_freqs.items():
            if name not in stems:
                # Add envelope with 0.05s fade at the end
                audio = 0.3 * np.sin(2.0 * np.pi * freq * t, dtype=np.float32)
                fade_len = min(num_samples, int(0.04 * sr))
                if fade_len > 0 and not request.loopable:
                    audio[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
                stems[name] = audio

        # Linear sum equals mix
        mix = sum_stems_with_gains(stems, stem_gains)

        beat_duration = 60.0 / (request.tempo_bpm or 120.0)
        num_beats = int(request.duration_s / beat_duration)
        beat_times = [round(i * beat_duration, 4) for i in range(num_beats)]

        metadata = {
            "provider": self.name,
            "version": self.version,
            "tempo_bpm": request.tempo_bpm or 120.0,
            "key": request.key or "C major",
            "beat_times_s": beat_times,
            "bar_times_s": [round(i * beat_duration * 4.0, 4) for i in range(num_beats // 4 + 1)],
            "sections": [s.model_dump() for s in (request.sections or [])],
            "timings": {
                "generation_s": round(time.time() - start_time, 4)
            },
            "warnings": [],
            "stems_metadata": {
                name: {"instrument": f"Mock {name.capitalize()}", "channels": 2, "gain": stem_gains[name]}
                for name in stems
            }
        }

        return mix, stems, stem_gains, metadata
