import time
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
from app.models.schemas import MusicJobRequest
from app.engine.providers.base import BaseMusicProvider
from app.engine.stem_composer import StemComposer
from app.engine.audio_renderer import sum_stems_with_gains

logger = logging.getLogger(__name__)


class SynthMusicProvider(BaseMusicProvider):
    """
    Production Multi-Track Audio Synthesizer Provider.
    Generates genuine, isolated instrument stems (drums, bass, chords, melody)
    with shared tempo, key, bar grid, section changes, and exact duration.
    100% self-contained and commercially safe (no external proprietary model weights needed).
    """
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.composer = StemComposer(sample_rate=sample_rate)

    @property
    def name(self) -> str:
        return "incubrix-multitrack-synth"

    @property
    def version(self) -> str:
        return "2.1.0"

    def generate(
        self,
        request: MusicJobRequest,
        job_id: str,
        regenerate_stem: Optional[str] = None,
        existing_stems: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], Dict[str, float], Dict[str, Any]]:
        start_time = time.time()
        sr = request.output.sample_rate if request.output else self.sample_rate
        if sr != self.sample_rate:
            self.composer = StemComposer(sample_rate=sr)
            self.sample_rate = sr

        section_dicts = [s.model_dump() for s in request.sections] if request.sections else None

        stems, stem_gains, comp_meta = self.composer.compose(
            prompt=request.prompt,
            duration_s=request.duration_s,
            sections=section_dicts,
            tempo_bpm=request.tempo_bpm,
            key=request.key,
            loopable=bool(request.loopable),
            seed=request.seed,
            regenerate_only_stem=regenerate_stem,
            existing_stems=existing_stems
        )

        # Mix is the exact linear combination of stems
        mix = sum_stems_with_gains(stems, stem_gains)

        gen_time = round(time.time() - start_time, 4)
        metadata = {
            "provider": self.name,
            "version": self.version,
            "tempo_bpm": comp_meta["tempo_bpm"],
            "key": comp_meta["key"],
            "style": comp_meta["style"],
            "beat_times_s": comp_meta["beat_times_s"],
            "bar_times_s": comp_meta["bar_times_s"],
            "sections": comp_meta["sections"],
            "timings": {
                "generation_s": gen_time
            },
            "warnings": comp_meta.get("warnings", []),
            "stems_metadata": comp_meta["stems_metadata"]
        }

        return mix, stems, stem_gains, metadata
