from dataclasses import dataclass


@dataclass
class BassNote:
    midi: int  # MIDI note number (0 if is_rest)
    quarter_length: float
    is_rest: bool
    tied: bool = False
    bar_start: bool = False  # True for the first note/rest of each measure


@dataclass
class AssignedNote(BassNote):
    string_idx: int = 0  # 0 = lowest string
    fret: int = 0
