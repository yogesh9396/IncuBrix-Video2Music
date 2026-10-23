from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import numpy as np
from app.models.schemas import MusicJobRequest


class BaseMusicProvider(ABC):
    """
    Abstract interface for all music generation providers (Mock, Synth, External/AI).
    Ensures modularity and swappability.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    def generate(
        self,
        request: MusicJobRequest,
        job_id: str,
        regenerate_stem: Optional[str] = None,
        existing_stems: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], Dict[str, float], Dict[str, Any]]:
        """
        Generates music and returns:
        - mix: np.ndarray (48kHz audio array)
        - stems: Dict[str, np.ndarray] (at least 3 genuine instrument stems)
        - stem_gains: Dict[str, float] (mixing gains applied)
        - metadata: Dict[str, Any] (timings, provider details, grid, etc.)
        """
        pass
