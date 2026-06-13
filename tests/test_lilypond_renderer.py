from pathlib import Path
import pytest
from processing.models import AssignedNote
from processing.lilypond_renderer import LilyPondRenderer


def make_assigned(midi, ql, string_idx, fret, is_rest=False):
    return AssignedNote(
        midi=midi, quarter_length=ql, is_rest=is_rest,
        string_idx=string_idx, fret=fret
    )


def test_midi_to_lily_pitch():
    from processing.lilypond_renderer import midi_to_lily_pitch
    assert midi_to_lily_pitch(40) == "e,"   # E2
    assert midi_to_lily_pitch(45) == "a,"   # A2
    assert midi_to_lily_pitch(50) == "d"    # D3
    assert midi_to_lily_pitch(55) == "g"    # G3
    assert midi_to_lily_pitch(60) == "c'"   # C4


def test_quarter_length_to_lily():
    from processing.lilypond_renderer import ql_to_lily_duration
    assert ql_to_lily_duration(1.0) == "4"
    assert ql_to_lily_duration(2.0) == "2"
    assert ql_to_lily_duration(0.5) == "8"
    assert ql_to_lily_duration(1.5) == "4."
    assert ql_to_lily_duration(4.0) == "1"


def test_generate_ly_string(tmp_path):
    renderer = LilyPondRenderer(tmp_dir=tmp_path, num_strings=4)
    notes = [
        make_assigned(40, 1.0, 0, 0),   # E2, string 0, fret 0
        make_assigned(45, 1.0, 1, 0),   # A2, string 1, fret 0
        make_assigned(0, 1.0, 0, 0, is_rest=True),
    ]
    ly = renderer.generate_ly(notes, title="Test")
    assert "\\version" in ly
    assert "TabStaff" in ly
    assert "e," in ly
    assert "a," in ly


@pytest.mark.slow
def test_render_to_pdf(tmp_path):
    renderer = LilyPondRenderer(tmp_dir=tmp_path, num_strings=4)
    notes = [
        make_assigned(40, 1.0, 0, 0),
        make_assigned(45, 2.0, 1, 0),
        make_assigned(50, 1.0, 2, 0),
    ]
    pdf = renderer.render(notes, title="Test Bass Tab")
    assert pdf.exists()
    assert pdf.suffix == ".pdf"
    assert pdf.stat().st_size > 1000
