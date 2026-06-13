from processing.models import AssignedNote, BassNote


def test_bass_note_creation():
    n = BassNote(midi=40, quarter_length=1.0, is_rest=False)
    assert n.midi == 40
    assert n.quarter_length == 1.0
    assert not n.is_rest


def test_assigned_note_defaults():
    n = AssignedNote(midi=40, quarter_length=1.0, is_rest=False, string_idx=0, fret=0)
    assert n.string_idx == 0
    assert n.fret == 0


def test_rest_note():
    n = BassNote(midi=0, quarter_length=2.0, is_rest=True)
    assert n.is_rest
