from processing.fret_assigner import FretAssigner, detect_string_count
from processing.models import BassNote


def make_note(midi, ql=1.0):
    return BassNote(midi=midi, quarter_length=ql, is_rest=False)


def test_detect_4_strings():
    notes = [make_note(40), make_note(45), make_note(50)]  # E2, A2, D3
    assert detect_string_count(notes) == 4


def test_detect_5_strings():
    notes = [make_note(35), make_note(40)]  # B1 below E2
    assert detect_string_count(notes) == 5


def test_open_e_string_4():
    fa = FretAssigner(num_strings=4)
    notes = [make_note(40)]  # E2 = open E string
    result = fa.assign(notes)
    # E2 on string 0 (E), fret 0
    assert result[0].string_idx == 0
    assert result[0].fret == 0


def test_open_g_string_4():
    fa = FretAssigner(num_strings=4)
    notes = [make_note(55)]  # G3 = open G string
    result = fa.assign(notes)
    assert result[0].string_idx == 3
    assert result[0].fret == 0


def test_fret_range_valid():
    fa = FretAssigner(num_strings=4)
    # All notes E2 to G#4 should be assignable
    for midi in range(40, 68):
        notes = [make_note(midi)]
        result = fa.assign(notes)
        assert result[0].fret >= 0
        assert result[0].fret <= 12


def test_rest_passthrough():
    fa = FretAssigner(num_strings=4)
    rest = BassNote(midi=0, quarter_length=1.0, is_rest=True)
    result = fa.assign([rest])
    assert result[0].is_rest
    assert result[0].string_idx == 0
    assert result[0].fret == 0


def test_consecutive_prefer_position():
    fa = FretAssigner(num_strings=4)
    # E2 then F2 — should stay on E string rather than jumping to A string
    notes = [make_note(40), make_note(41)]
    result = fa.assign(notes)
    # Both notes on string 0 (E string): frets 0 and 1
    assert result[0].string_idx == 0 and result[0].fret == 0
    assert result[1].string_idx == 0 and result[1].fret == 1


def test_5_string_low_b():
    fa = FretAssigner(num_strings=5)
    notes = [make_note(35)]  # B1 = open B string
    result = fa.assign(notes)
    assert result[0].string_idx == 0
    assert result[0].fret == 0
