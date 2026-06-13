from processing.models import BassNote, AssignedNote

TUNING_4 = [40, 45, 50, 55]      # E2, A2, D3, G3
TUNING_5 = [35, 40, 45, 50, 55]  # B1, E2, A2, D3, G3
MAX_FRET = 12


def detect_string_count(notes: list[BassNote]) -> int:
    """Return 5 if any pitched note is below E2 (MIDI 40), else 4."""
    for n in notes:
        if not n.is_rest and n.midi < 40:
            return 5
    return 4


class FretAssigner:
    def __init__(self, num_strings: int = 4):
        self.tuning = TUNING_5 if num_strings == 5 else TUNING_4
        self.num_strings = num_strings

    def _candidates(self, midi: int) -> list[tuple[int, int]]:
        """Return valid (string_idx, fret) pairs for a MIDI note."""
        result = []
        for idx, open_midi in enumerate(self.tuning):
            fret = midi - open_midi
            if 0 <= fret <= MAX_FRET:
                result.append((idx, fret))
        return result

    def _hand_position(self, string_idx: int, fret: int) -> float:
        """Approximate hand position on the neck."""
        return fret if fret > 0 else 0.0

    def _cost(self, prev: tuple[int, int], curr: tuple[int, int]) -> float:
        pos_shift = abs(self._hand_position(*curr) - self._hand_position(*prev))
        string_shift = abs(curr[0] - prev[0]) * 0.3
        large_jump = 2.0 if pos_shift > 5 else 0.0
        return pos_shift + string_shift + large_jump

    def assign(self, notes: list[BassNote]) -> list[AssignedNote]:
        """Assign (string_idx, fret) to each note via dynamic programming."""
        assigned: list[AssignedNote] = []
        prev_state: tuple[int, int] | None = None

        for note in notes:
            if note.is_rest:
                assigned.append(AssignedNote(
                    midi=note.midi, quarter_length=note.quarter_length,
                    is_rest=True, tied=note.tied, string_idx=0, fret=0
                ))
                continue

            candidates = self._candidates(note.midi)
            if not candidates:
                # Note out of range — place on lowest string, flag with fret -1
                assigned.append(AssignedNote(
                    midi=note.midi, quarter_length=note.quarter_length,
                    is_rest=False, tied=note.tied, string_idx=0, fret=-1
                ))
                continue

            if prev_state is None:
                # First note: prefer open strings (fret 0), then lowest fret
                best = min(candidates, key=lambda c: (c[1], c[0]))
            else:
                best = min(candidates, key=lambda c: self._cost(prev_state, c))

            prev_state = best
            assigned.append(AssignedNote(
                midi=note.midi, quarter_length=note.quarter_length,
                is_rest=False, tied=note.tied,
                string_idx=best[0], fret=best[1]
            ))

        return assigned
