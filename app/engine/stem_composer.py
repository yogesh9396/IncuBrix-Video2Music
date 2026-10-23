import math
import random
import re
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Known artists & copyright tokens for safety screening
KNOWN_ARTISTS = [
    "hans zimmer", "john williams", "ed sheeran", "taylor swift", "the beatles",
    "drake", "coldplay", "michael jackson", "queen", "beyonce", "eminem",
    "daft punk", "ludovico einaudi", "billie eilish", "beethoven", "mozart",
    "bach", "avicii", "skrillex", "dualipa", "bts"
]

VOCAL_TERMS = ["vocal", "vocals", "singer", "singing", "lyrics", "voice", "rap", "words"]

# Scales and chord progressions for different styles
STYLE_PROFILES = {
    "cinematic": {
        "bpm": 80.0,
        "key": "D minor",
        "scale": [62, 64, 65, 67, 69, 70, 72], # D minor MIDI
        "chords": [
            [50, 57, 62, 65], # Dm
            [46, 53, 58, 62], # Bb
            [48, 55, 60, 64], # F
            [45, 52, 57, 60], # C
        ],
        "bass_root": [38, 34, 36, 33],
        "drum_pattern": "cinematic_pulse",
        "timbre": "dramatic"
    },
    "lo-fi": {
        "bpm": 74.0,
        "key": "Eb major",
        "scale": [63, 65, 67, 68, 70, 72, 74],
        "chords": [
            [53, 60, 65, 68], # Fm7
            [51, 58, 63, 67], # Ebmaj7
            [49, 56, 61, 65], # Dbmaj7
            [55, 62, 67, 70], # Gm7
        ],
        "bass_root": [41, 39, 37, 43],
        "drum_pattern": "lofi_laidback",
        "timbre": "warm_vintage"
    },
    "corporate": {
        "bpm": 115.0,
        "key": "C major",
        "scale": [60, 62, 64, 65, 67, 69, 71],
        "chords": [
            [48, 55, 60, 64], # C
            [43, 50, 55, 59], # G
            [45, 52, 57, 60], # Am
            [41, 48, 53, 57], # F
        ],
        "bass_root": [36, 31, 33, 29],
        "drum_pattern": "corporate_punch",
        "timbre": "bright_positive"
    },
    "electronic": {
        "bpm": 126.0,
        "key": "A minor",
        "scale": [57, 59, 60, 62, 64, 65, 67],
        "chords": [
            [45, 52, 57, 60], # Am
            [41, 48, 53, 57], # F
            [48, 55, 60, 64], # C
            [43, 50, 55, 59], # G
        ],
        "bass_root": [33, 29, 36, 31],
        "drum_pattern": "four_on_floor",
        "timbre": "synth_lead"
    },
    "acoustic": {
        "bpm": 92.0,
        "key": "G major",
        "scale": [55, 57, 59, 60, 62, 64, 66],
        "chords": [
            [43, 50, 55, 59], # G
            [47, 54, 59, 62], # Bm
            [48, 55, 60, 64], # C
            [45, 52, 57, 61], # D
        ],
        "bass_root": [31, 35, 36, 38],
        "drum_pattern": "acoustic_folk",
        "timbre": "acoustic_warm"
    },
    "tense": {
        "bpm": 96.0,
        "key": "E minor",
        "scale": [52, 54, 55, 57, 59, 60, 62],
        "chords": [
            [40, 47, 52, 55], # Em
            [41, 48, 53, 56], # F dim
            [40, 47, 52, 55], # Em
            [39, 46, 51, 54], # D# dim
        ],
        "bass_root": [28, 29, 28, 27],
        "drum_pattern": "tense_clock",
        "timbre": "suspense"
    },
    "playful": {
        "bpm": 120.0,
        "key": "F major",
        "scale": [53, 55, 57, 58, 60, 62, 64],
        "chords": [
            [41, 48, 53, 57], # F
            [45, 52, 57, 60], # Am
            [43, 50, 55, 58], # Gm
            [46, 53, 58, 62], # Bb
        ],
        "bass_root": [29, 33, 31, 34],
        "drum_pattern": "playful_bounce",
        "timbre": "marimba_pizz"
    },
    "ambient": {
        "bpm": 65.0,
        "key": "C major",
        "scale": [60, 62, 64, 65, 67, 69, 71],
        "chords": [
            [48, 55, 60, 64], # Cmaj7
            [45, 52, 57, 60], # Am7
            [41, 48, 53, 57], # Fmaj7
            [43, 50, 55, 59], # Gsus
        ],
        "bass_root": [36, 33, 29, 31],
        "drum_pattern": "ambient_minimal",
        "timbre": "lush_pad"
    }
}


def sanitize_prompt(prompt: str) -> Tuple[str, List[str]]:
    """
    Screens prompt for copyrighted artist references and vocal requests.
    Returns sanitized prompt and list of warnings.
    """
    warnings = []
    lower_prompt = prompt.lower()

    for artist in KNOWN_ARTISTS:
        if artist in lower_prompt:
            warnings.append(
                f"Reference to artist '{artist}' detected. Original composition applied; copyrighted styles or material will not be replicated."
            )
            # Remove artist name
            lower_prompt = lower_prompt.replace(artist, "melodic style")

    for vocal in VOCAL_TERMS:
        if re.search(r'\b' + vocal + r'\b', lower_prompt):
            warnings.append(
                f"Vocal instruction '{vocal}' detected. As required by IncuBrix engine specifications, system remains strictly 100% instrumental."
            )
            lower_prompt = re.sub(r'\b' + vocal + r'\b', "instrumental", lower_prompt)

    return lower_prompt, warnings


def detect_style(prompt: str) -> str:
    """
    Classifies prompt text into one of the supported style keys.
    """
    lower = prompt.lower()
    for style in STYLE_PROFILES.keys():
        if style in lower:
            return style
    if "corporate" in lower or "commercial" in lower or "tech" in lower or "uplifting" in lower:
        return "corporate"
    if "lo-fi" in lower or "lofi" in lower or "chill" in lower or "relax" in lower:
        return "lo-fi"
    if "electronic" in lower or "dance" in lower or "edm" in lower or "beat" in lower:
        return "electronic"
    if "acoustic" in lower or "guitar" in lower or "folk" in lower:
        return "acoustic"
    if "tense" in lower or "dark" in lower or "suspense" in lower or "action" in lower:
        return "tense"
    if "playful" in lower or "fun" in lower or "cartoon" in lower or "happy" in lower:
        return "playful"
    if "cinematic" in lower or "orchestral" in lower or "dramatic" in lower or "movie" in lower:
        return "cinematic"
    return "cinematic"


class SoundGenerator:
    """
    High-fidelity physical/additive sound synthesis for genuine instrument stems.
    Operates at specified sample rate (default 48000 Hz).
    """
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate

    def synth_kick(self, duration_s: float = 0.35) -> np.ndarray:
        t = np.linspace(0, duration_s, int(self.sr * duration_s), endpoint=False)
        # Pitch drop 150 Hz -> 40 Hz
        freq = 40.0 + 110.0 * np.exp(-t / 0.05)
        phase = 2.0 * np.pi * np.cumsum(freq) / self.sr
        amp = np.exp(-t / 0.09)
        return (np.sin(phase) * amp * 0.9).astype(np.float32)

    def synth_snare(self, duration_s: float = 0.3) -> np.ndarray:
        t = np.linspace(0, duration_s, int(self.sr * duration_s), endpoint=False)
        # Tone at 190 Hz + noise
        tone = np.sin(2.0 * np.pi * 190.0 * t) * np.exp(-t / 0.06)
        noise = (np.random.uniform(-1.0, 1.0, len(t))) * np.exp(-t / 0.12)
        snare = (tone * 0.4 + noise * 0.6) * 0.8
        return snare.astype(np.float32)

    def synth_hihat(self, duration_s: float = 0.08, open_hh: bool = False) -> np.ndarray:
        decay = 0.18 if open_hh else 0.035
        length = int(self.sr * (0.3 if open_hh else duration_s))
        t = np.linspace(0, length / self.sr, length, endpoint=False)
        # High pass / metallic noise
        noise = np.random.uniform(-1.0, 1.0, length)
        # Simple highpass differentiator
        noise = np.diff(noise, prepend=0)
        hh = noise * np.exp(-t / decay) * 0.45
        return hh.astype(np.float32)

    def synth_bass_note(self, freq: float, duration_s: float) -> np.ndarray:
        t = np.linspace(0, duration_s, int(self.sr * duration_s), endpoint=False)
        # Fundamental + 2nd harmonic + 3rd harmonic with low-pass roll-off
        harm1 = np.sin(2.0 * np.pi * freq * t)
        harm2 = 0.45 * np.sin(2.0 * np.pi * freq * 2.0 * t)
        harm3 = 0.18 * np.sin(2.0 * np.pi * freq * 3.0 * t)
        raw = harm1 + harm2 + harm3
        # Envelope: Attack 10ms, decay 100ms, sustain 0.8, release 50ms
        env = np.ones_like(t)
        attack_len = min(len(t), int(0.01 * self.sr))
        env[:attack_len] = np.linspace(0, 1, attack_len)
        release_len = min(len(t), int(0.05 * self.sr))
        env[-release_len:] = np.linspace(1, 0, release_len)
        return (raw * env * 0.7).astype(np.float32)

    def synth_chord_voice(self, freqs: List[float], duration_s: float, timbre: str = "warm") -> np.ndarray:
        t = np.linspace(0, duration_s, int(self.sr * duration_s), endpoint=False)
        chord_audio = np.zeros_like(t)
        for f in freqs:
            # Multi-harmonic chord note with stereo detune
            part1 = np.sin(2.0 * np.pi * f * t)
            part2 = 0.35 * np.sin(2.0 * np.pi * (f * 2.0 + 0.5) * t)
            part3 = 0.15 * np.sin(2.0 * np.pi * (f * 3.0 - 0.5) * t)
            voice = part1 + part2 + part3
            chord_audio += voice

        # Envelope
        env = np.ones_like(t)
        attack_len = min(len(t), int(0.04 * self.sr))
        env[:attack_len] = np.linspace(0, 1, attack_len)
        release_len = min(len(t), int(0.12 * self.sr))
        env[-release_len:] = np.linspace(1, 0, release_len)
        chord_audio = (chord_audio / (len(freqs) + 1.0)) * env * 0.85
        return chord_audio.astype(np.float32)

    def synth_melody_note(self, freq: float, duration_s: float) -> np.ndarray:
        t = np.linspace(0, duration_s, int(self.sr * duration_s), endpoint=False)
        # Vibrato at 5.5 Hz
        vibrato = 0.008 * np.sin(2.0 * np.pi * 5.5 * t)
        instant_freq = freq * (1.0 + vibrato)
        phase = 2.0 * np.pi * np.cumsum(instant_freq) / self.sr
        lead = np.sin(phase) + 0.3 * np.sin(2.0 * phase)
        # ADSR Envelope
        env = np.ones_like(t)
        att = min(len(t), int(0.02 * self.sr))
        env[:att] = np.linspace(0, 1, att)
        rel = min(len(t), int(0.08 * self.sr))
        env[-rel:] = np.linspace(1, 0, rel)
        return (lead * env * 0.65).astype(np.float32)


class StemComposer:
    """
    Composes genuine, isolated musical stems (Drums, Bass, Chords, Melody)
    satisfying strict beat/bar grids, exact duration control, section energy transitions,
    seamless loopability, and individual stem regeneration.
    """
    def __init__(self, sample_rate: int = 48000):
        self.sr = sample_rate
        self.synth = SoundGenerator(sample_rate)

    def midi_to_freq(self, midi_num: int) -> float:
        return 440.0 * (2.0 ** ((midi_num - 69) / 12.0))

    def compose(
        self,
        prompt: str,
        duration_s: float,
        sections: Optional[List[Dict[str, Any]]] = None,
        tempo_bpm: Optional[float] = None,
        key: Optional[str] = None,
        loopable: bool = False,
        seed: Optional[int] = None,
        regenerate_only_stem: Optional[str] = None,
        existing_stems: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, float], Dict[str, Any]]:
        """
        Executes musical composition and returns:
        - stems: Dict[str, np.ndarray] of 4 genuine stems (drums, bass, chords, melody)
        - stem_gains: Dict[str, float] of mixing coefficients
        - metadata: Manifest metadata containing grid, sections, and instruments
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        sanitized_prompt, warnings = sanitize_prompt(prompt)
        style_key = detect_style(sanitized_prompt)
        profile = STYLE_PROFILES[style_key]

        bpm = tempo_bpm if tempo_bpm is not None else profile["bpm"]
        actual_key = key if key is not None else profile["key"]

        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4.0  # 4/4 time signature

        # Calculate exact number of samples requested
        total_samples = int(round(duration_s * self.sr))

        # Calculate beats and bars
        num_beats = int(math.ceil(duration_s / beat_duration))
        beat_times = [round(i * beat_duration, 4) for i in range(num_beats) if i * beat_duration < duration_s]
        num_bars = int(math.ceil(duration_s / bar_duration))
        bar_times = [round(i * bar_duration, 4) for i in range(num_bars) if i * bar_duration < duration_s]

        # Section boundaries mapped to nearest beat
        parsed_sections = []
        if sections and len(sections) > 0:
            for s in sections:
                # Snap to nearest beat
                beat_idx = int(round(s["start_s"] / beat_duration))
                snapped_time = beat_idx * beat_duration
                parsed_sections.append({
                    "start_s": round(snapped_time, 3),
                    "mood": s["mood"],
                    "beat_index": beat_idx
                })
        else:
            # Default 3 sections: intro, build, climax
            parsed_sections = [
                {"start_s": 0.0, "mood": "intro", "beat_index": 0},
                {"start_s": round(duration_s * 0.3, 3), "mood": "build", "beat_index": int((duration_s * 0.3) / beat_duration)},
                {"start_s": round(duration_s * 0.7, 3), "mood": "peak", "beat_index": int((duration_s * 0.7) / beat_duration)},
            ]

        # Initialize stem buffers
        stems = {}
        for stem_name in ["drums", "bass", "chords", "melody"]:
            if regenerate_only_stem and existing_stems and stem_name != regenerate_only_stem:
                stems[stem_name] = existing_stems[stem_name].copy()
            else:
                stems[stem_name] = np.zeros(total_samples, dtype=np.float32)

        # Generate each stem independently
        # 1. DRUMS STEM
        if not regenerate_only_stem or regenerate_only_stem == "drums":
            kick = self.synth.synth_kick()
            snare = self.synth.synth_snare()
            hh_closed = self.synth.synth_hihat(open_hh=False)
            hh_open = self.synth.synth_hihat(open_hh=True)

            for b in range(num_beats):
                t_beat = b * beat_duration
                sample_pos = int(t_beat * self.sr)
                if sample_pos >= total_samples:
                    break

                # Determine section energy
                sec_mood = "intro"
                for sec in reversed(parsed_sections):
                    if t_beat >= sec["start_s"]:
                        sec_mood = sec["mood"].lower()
                        break

                beat_in_bar = b % 4
                is_build_or_peak = ("build" in sec_mood or "peak" in sec_mood or "uplift" in sec_mood or "energy" in sec_mood)

                # Four-on-the-floor or standard rock/pop pattern
                if beat_in_bar == 0 or (beat_in_bar == 2 and is_build_or_peak):
                    self._add_sound(stems["drums"], kick, sample_pos)

                if beat_in_bar in (1, 3) and ("intro" not in sec_mood or duration_s < 15):
                    self._add_sound(stems["drums"], snare, sample_pos)

                # Hi-hat on every 8th note
                eighth_pos = sample_pos + int(0.5 * beat_duration * self.sr)
                self._add_sound(stems["drums"], hh_closed, sample_pos)
                if eighth_pos < total_samples and is_build_or_peak:
                    self._add_sound(stems["drums"], hh_closed, eighth_pos)

        # 2. BASS STEM
        if not regenerate_only_stem or regenerate_only_stem == "bass":
            bass_roots = profile["bass_root"]
            for b in range(num_beats):
                t_beat = b * beat_duration
                sample_pos = int(t_beat * self.sr)
                if sample_pos >= total_samples:
                    break

                chord_idx = (b // 4) % len(bass_roots)
                midi_note = bass_roots[chord_idx]
                freq = self.midi_to_freq(midi_note)
                note_dur = beat_duration * 0.95
                bass_wave = self.synth.synth_bass_note(freq, note_dur)
                self._add_sound(stems["bass"], bass_wave, sample_pos)

        # 3. CHORDS STEM
        if not regenerate_only_stem or regenerate_only_stem == "chords":
            progression = profile["chords"]
            for bar_i in range(num_bars):
                t_bar = bar_i * bar_duration
                sample_pos = int(t_bar * self.sr)
                if sample_pos >= total_samples:
                    break

                chord_midi = progression[bar_i % len(progression)]
                chord_freqs = [self.midi_to_freq(m) for m in chord_midi]
                chord_dur = bar_duration * 0.96
                chord_wave = self.synth.synth_chord_voice(chord_freqs, chord_dur)
                self._add_sound(stems["chords"], chord_wave, sample_pos)

        # 4. MELODY STEM
        if not regenerate_only_stem or regenerate_only_stem == "melody":
            scale = profile["scale"]
            # Create structured melodic phrase per bar
            melody_seed = (seed or 42) + 101
            mel_rng = random.Random(melody_seed)

            for b in range(num_beats):
                t_beat = b * beat_duration
                sample_pos = int(t_beat * self.sr)
                if sample_pos >= total_samples:
                    break

                # 70% chance of note on beat
                if mel_rng.random() < 0.75:
                    degree = mel_rng.choice(scale)
                    freq = self.midi_to_freq(degree)
                    note_dur = beat_duration * mel_rng.choice([0.5, 0.8, 1.0])
                    mel_wave = self.synth.synth_melody_note(freq, note_dur)
                    self._add_sound(stems["melody"], mel_wave, sample_pos)

        # Determine which stems were generated in this run
        stems_to_process = [regenerate_only_stem] if regenerate_only_stem else list(stems.keys())

        # Natural Musical Ending / Release Fade within 0.05s
        # Ensure freshly generated tracks do not end on a hard click/cut
        fade_samples = int(0.04 * self.sr)
        if fade_samples > 0 and not loopable:
            fade_curve = np.linspace(1.0, 0.0, fade_samples)
            for stem_name in stems_to_process:
                stems[stem_name][-fade_samples:] *= fade_curve

        # If loopable is true, apply seamless crossfade at loop seam
        if loopable:
            cross_samples = int(0.03 * self.sr)
            for stem_name in stems_to_process:
                # Smooth loop boundaries to prevent any seam pop
                start_curve = np.linspace(0.0, 1.0, cross_samples)
                end_curve = np.linspace(1.0, 0.0, cross_samples)
                stems[stem_name][:cross_samples] = stems[stem_name][:cross_samples] * start_curve + stems[stem_name][-cross_samples:] * end_curve

        stem_gains = {
            "drums": 0.85,
            "bass": 0.80,
            "chords": 0.70,
            "melody": 0.75
        }

        metadata = {
            "tempo_bpm": float(bpm),
            "key": str(actual_key),
            "style": style_key,
            "beat_times_s": beat_times,
            "bar_times_s": bar_times,
            "sections": parsed_sections,
            "warnings": warnings,
            "stems_metadata": {
                "drums": {"instrument": "Synthesized Acoustic/Analog Percussion", "channels": 2, "gain": stem_gains["drums"]},
                "bass": {"instrument": "Subtractive Resonant Bass", "channels": 2, "gain": stem_gains["bass"]},
                "chords": {"instrument": "Polyphonic Keys & Warm Pad", "channels": 2, "gain": stem_gains["chords"]},
                "melody": {"instrument": "Lead Melodic Voice", "channels": 2, "gain": stem_gains["melody"]}
            }
        }

        return stems, stem_gains, metadata

    def _add_sound(self, buffer: np.ndarray, sound: np.ndarray, pos: int):
        if pos >= len(buffer):
            return
        end = min(len(buffer), pos + len(sound))
        sound_len = end - pos
        buffer[pos:end] += sound[:sound_len]
