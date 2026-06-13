from dataclasses import dataclass


@dataclass
class BassNote:
    midi: int  # MIDI note number (0 if is_rest)
    quarter_length: float
    is_rest: bool
    tied: bool = False


@dataclass
class AssignedNote(BassNote):
    string_idx: int = 0  # 0 = lowest string
    fret: int = 0
