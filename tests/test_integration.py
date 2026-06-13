# tests/test_integration.py
from pathlib import Path
import pytest

EXAMPLES = Path("Exemples")
MUSICXML = EXAMPLES / "michael_bublefeeling_good.musicxml"
MIDI = EXAMPLES / "michael_bublefeeling_good.mid"


@pytest.mark.slow
def test_full_pipeline_musicxml(tmp_path):
    """End-to-end depuis MusicXML → PDF tablature."""
    from processing.input_router import InputRouter
    from processing.music_parser import MusicParser
    from processing.bass_extractor import BassExtractor
    from processing.fret_assigner import FretAssigner, detect_string_count
    from processing.lilypond_renderer import LilyPondRenderer

    # Route
    router = InputRouter(tmp_dir=tmp_path / "routed")
    xml_path = router.route(MUSICXML)
    assert xml_path.exists()

    # Parse + extract
    parser = MusicParser()
    score = parser.parse(xml_path)
    extractor = BassExtractor()
    notes = extractor.extract(score)
    assert len(notes) > 10

    # Assign frets
    num_strings = detect_string_count(notes)
    fa = FretAssigner(num_strings=num_strings)
    assigned = fa.assign(notes)
    # fret=-1 means out-of-range note (not an error), so allow -1 and above
    assert all(a.fret >= -1 for a in assigned if not a.is_rest)

    # Render PDF
    renderer = LilyPondRenderer(tmp_dir=tmp_path / "lily", num_strings=num_strings)
    pdf = renderer.render(assigned, title="Feeling Good")
    assert pdf.exists()
    assert pdf.stat().st_size > 5000
    print(f"PDF généré : {pdf} ({pdf.stat().st_size} octets)")


@pytest.mark.slow
def test_full_pipeline_midi(tmp_path):
    """End-to-end depuis MIDI → PDF tablature."""
    from processing.input_router import InputRouter
    from processing.music_parser import MusicParser
    from processing.bass_extractor import BassExtractor
    from processing.fret_assigner import FretAssigner, detect_string_count
    from processing.lilypond_renderer import LilyPondRenderer

    router = InputRouter(tmp_dir=tmp_path / "routed")
    xml_path = router.route(MIDI)

    parser = MusicParser()
    score = parser.parse(xml_path)
    parts = parser.list_parts(score)
    assert len(parts) >= 1

    extractor = BassExtractor()
    # MIDI may not have a named bass part — pick first part
    notes = extractor.extract(score, part_name=parts[0])
    assert len(notes) > 0

    fa = FretAssigner(num_strings=4)
    assigned = fa.assign(notes)
    renderer = LilyPondRenderer(tmp_dir=tmp_path / "lily", num_strings=4)
    pdf = renderer.render(assigned, title="Feeling Good (MIDI)")
    assert pdf.exists()
