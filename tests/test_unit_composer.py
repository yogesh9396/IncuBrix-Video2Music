import numpy as np
import pytest
from app.engine.stem_composer import StemComposer, detect_style, sanitize_prompt


def test_composer_multitrack_stems_and_exact_duration():
    composer = StemComposer(sample_rate=48000)
    durations = [5.0, 10.0, 30.0]

    for req_dur in durations:
        stems, gains, meta = composer.compose(
            prompt="uplifting corporate technology background track",
            duration_s=req_dur,
            tempo_bpm=120.0
        )

        assert set(stems.keys()) == {"drums", "bass", "chords", "melody"}
        for s_name, audio in stems.items():
            actual_dur = len(audio) / 48000.0
            # Must match requested duration within 0.05 seconds
            assert abs(actual_dur - req_dur) <= 0.05, f"Stem {s_name} duration {actual_dur} deviates from {req_dur}"


def test_section_plan_and_energy_changes():
    composer = StemComposer(sample_rate=48000)
    sections = [
        {"start_s": 0.0, "mood": "calm intro"},
        {"start_s": 6.0, "mood": "build-up"},
        {"start_s": 12.0, "mood": "uplifting peak"}
    ]

    stems, gains, meta = composer.compose(
        prompt="cinematic build-up to an epic finish",
        duration_s=20.0,
        sections=sections,
        tempo_bpm=120.0
    )

    # Check sections land on beat
    for sec in meta["sections"]:
        assert "beat_index" in sec
        assert sec["start_s"] >= 0.0


def test_single_stem_regeneration():
    composer = StemComposer(sample_rate=48000)
    stems1, gains1, meta1 = composer.compose(
        prompt="lo-fi hip-hop chill study beats",
        duration_s=8.0,
        seed=100
    )

    # Regenerate only drums stem with a different seed
    stems2, gains2, meta2 = composer.compose(
        prompt="lo-fi hip-hop chill study beats",
        duration_s=8.0,
        seed=200,
        regenerate_only_stem="drums",
        existing_stems=stems1
    )

    # Drums must be different
    assert not np.array_equal(stems1["drums"], stems2["drums"]), "Regenerated drums should differ"

    # Bass, chords, melody must be identical
    np.testing.assert_array_equal(stems1["bass"], stems2["bass"])
    np.testing.assert_array_equal(stems1["chords"], stems2["chords"])
    np.testing.assert_array_equal(stems1["melody"], stems2["melody"])


def test_prompt_sanitization_and_safety():
    prompt = "hans zimmer epic orchestral with female vocals and singing"
    sanitized, warnings = sanitize_prompt(prompt)

    assert "hans zimmer" not in sanitized
    assert len(warnings) >= 2
    assert any("artist" in w.lower() for w in warnings)
    assert any("instrumental" in w.lower() for w in warnings)


def test_style_classification():
    assert detect_style("relaxing chill lo-fi beats") == "lo-fi"
    assert detect_style("intense action tense dramatic movie scene") in ["tense", "cinematic"]
    assert detect_style("inspiring corporate pitch presentation") == "corporate"
    assert detect_style("acoustic folk guitar song") == "acoustic"
    assert detect_style("fun playful cartoon animation") == "playful"
