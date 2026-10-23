from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator


class Section(BaseModel):
    start_s: float = Field(..., ge=0.0, description="Start time of the section in seconds")
    mood: str = Field(..., min_length=1, description="Mood or intensity description for this section")


class OutputConfig(BaseModel):
    sample_rate: int = Field(default=48000, description="Audio sample rate (Hz), standard 48000")
    target_lufs: float = Field(default=-16.0, description="Target integrated loudness in LUFS (standard -16 LUFS)")
    formats: List[str] = Field(default_factory=lambda: ["wav", "mp3"], description="Formats to export")


class MusicJobRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Style and mood prompt description")
    duration_s: float = Field(..., ge=5.0, le=300.0, description="Requested duration in seconds (5 to 300s)")
    sections: Optional[List[Section]] = Field(default=None, description="Optional cut points and mood transitions")
    tempo_bpm: Optional[float] = Field(default=None, ge=40.0, le=240.0, description="Optional fixed tempo in BPM")
    key: Optional[str] = Field(default=None, description="Optional musical key (e.g. 'C major', 'A minor')")
    loopable: Optional[bool] = Field(default=False, description="Whether the track must loop seamlessly")
    narration_url: Optional[str] = Field(default=None, description="URL or local path to voiceover audio to duck music")
    callback_url: Optional[str] = Field(default=None, description="Webhook URL called when job finishes")
    seed: Optional[int] = Field(default=None, description="Deterministic random seed")
    output: Optional[OutputConfig] = Field(default_factory=OutputConfig, description="Output rendering options")

    @model_validator(mode="after")
    def validate_sections(self):
        if self.sections:
            # Sort sections by start time
            sorted_sections = sorted(self.sections, key=lambda s: s.start_s)
            self.sections = sorted_sections
            
            # Check sections boundaries
            for i, sec in enumerate(self.sections):
                if sec.start_s >= self.duration_s:
                    raise ValueError(f"Section at {sec.start_s}s starts after track duration {self.duration_s}s")
                if i > 0:
                    gap = sec.start_s - self.sections[i-1].start_s
                    if gap < 1.5:
                        raise ValueError(f"Section interval between section {i-1} and {i} is {gap:.2f}s, which is under the minimum 1.5s threshold")
        return self


class StemRegenerateRequest(BaseModel):
    stem_name: str = Field(..., description="Name of the stem to regenerate (e.g. 'drums', 'melody', 'bass', 'chords')")
    prompt_modifier: Optional[str] = Field(default=None, description="Optional specific prompt modifier for this stem")
    seed: Optional[int] = Field(default=None, description="New seed for this stem")


class JobResultFiles(BaseModel):
    mix_url: str = Field(..., description="Download link for mix.wav")
    mix_mp3_url: Optional[str] = Field(default=None, description="Download link for mix.mp3")
    mix_ducked_url: Optional[str] = Field(default=None, description="Download link for mix_ducked.wav if narration provided")
    stems: Dict[str, str] = Field(..., description="Download links for each individual stem.wav")
    manifest_url: str = Field(..., description="Download link for music_manifest.json")


class MusicManifest(BaseModel):
    job_id: str
    prompt: str
    duration_s: float
    actual_duration_s: float
    tempo_bpm: float
    key: str
    seed: int
    loopable: bool
    sections: List[Dict[str, Any]]
    beat_times_s: List[float]
    bar_times_s: List[float]
    stem_gains: Dict[str, float]
    stems_metadata: Dict[str, Dict[str, Any]]
    loudness: Dict[str, Any]
    ducking_applied: bool
    volume_curve: Optional[List[Dict[str, float]]] = None
    models_providers: Dict[str, Any]
    timings: Dict[str, float]
    cost_estimate: Dict[str, Any]
    warnings: List[str]
    licence_rights: Dict[str, Any]


class JobStatusResponse(BaseModel):
    job_id: str
    status: str = Field(..., description="queued, running, succeeded, failed")
    progress: int = Field(default=0, ge=0, le=100, description="Job progress percentage 0-100")
    created_at: str
    updated_at: str
    result: Optional[JobResultFiles] = None
    manifest: Optional[MusicManifest] = None
    error: Optional[Dict[str, Any]] = None


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Job accepted and queued for generation"
    created_at: str
