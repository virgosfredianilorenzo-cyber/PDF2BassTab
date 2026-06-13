import music21
from processing.models import BassNote

BASS_KEYWORDS = [
    "bass", "basse", "basso", "tuba", "contrebasse",
    "contrabass", "b. él", "b.él", "electric bass",
]


class NoBassPartError(Exception):
    pass


class AmbiguousBassError(Exception):
    def __init__(self, candidates: list[str]):
        self.candidates = candidates
        super().__init__(f"Multiple bass candidates: {candidates}")


class BassExtractor:
    def extract(
        self,
        score: music21.stream.Score,
        part_name: str | None = None,
    ) -> list[BassNote]:
        """Extract notes from the bass part as a list of BassNote."""
        part = self._find_part(score, part_name)
        return self._part_to_notes(part)

    def _find_part(
        self, score: music21.stream.Score, part_name: str | None
    ) -> music21.stream.Part:
        if part_name is not None:
            for part in score.parts:
                name = part.partName or part.id or ""
                if name == part_name:
                    return part
            raise NoBassPartError(f"Part not found: {part_name!r}")

        candidates = []
        for part in score.parts:
            name = str(part.partName or part.id or "").lower()
            if any(kw in name for kw in BASS_KEYWORDS):
                candidates.append(part)

        if not candidates:
            raise NoBassPartError("No bass part found in score")
        if len(candidates) > 1:
            # Filter out tablature staves (TabClef) — prefer notation staves
            non_tab = [p for p in candidates if not self._is_tab_part(p)]
            if len(non_tab) == 1:
                return non_tab[0]
            if non_tab:
                candidates = non_tab
            # Still ambiguous
            if len(candidates) > 1:
                names = [p.partName or p.id for p in candidates]
                raise AmbiguousBassError(names)
        return candidates[0]

    def _is_tab_part(self, part: music21.stream.Part) -> bool:
        """Return True if the part uses a tablature clef."""
        clefs = list(part.flatten().getElementsByClass("Clef"))
        return any(isinstance(c, music21.clef.TabClef) for c in clefs)

    def _part_to_notes(self, part: music21.stream.Part) -> list[BassNote]:
        """Extract notes measure by measure, preserving barline positions.

        Iterating over Measure objects (rather than a flat list) ensures that
        note durations are normalised to each measure's actual length. This
        prevents LilyPond from receiving durations that don't sum to whole
        measures, which would break automatic line-breaking.
        """
        notes: list[BassNote] = []
        measures = list(part.getElementsByClass(music21.stream.Measure))

        if not measures:
            # Fallback for parts without explicit measures
            return self._flat_to_notes(part.flatten().notesAndRests)

        for measure in measures:
            measure_notes: list[BassNote] = []
            for el in measure.flatten().notesAndRests:
                tied = (
                    isinstance(el, music21.note.Note)
                    and el.tie is not None
                    and el.tie.type in ("start", "continue")
                )
                if isinstance(el, music21.note.Rest):
                    measure_notes.append(BassNote(
                        midi=0,
                        quarter_length=float(el.quarterLength),
                        is_rest=True,
                        tied=False,
                    ))
                elif isinstance(el, music21.note.Note):
                    measure_notes.append(BassNote(
                        midi=el.pitch.midi,
                        quarter_length=float(el.quarterLength),
                        is_rest=False,
                        tied=tied,
                    ))
                elif isinstance(el, music21.chord.Chord):
                    lowest = min(el.pitches, key=lambda p: p.midi)
                    measure_notes.append(BassNote(
                        midi=lowest.midi,
                        quarter_length=float(el.quarterLength),
                        is_rest=False,
                        tied=tied,
                    ))

            if not measure_notes:
                continue

            # Normalise durations so they sum exactly to the measure length,
            # preventing accumulated rounding errors from misaligning barlines.
            expected = float(measure.quarterLength)
            actual = sum(n.quarter_length for n in measure_notes)
            if actual > 0 and abs(actual - expected) > 1e-6:
                # Distribute the rounding error onto the last note
                measure_notes[-1] = BassNote(
                    midi=measure_notes[-1].midi,
                    quarter_length=measure_notes[-1].quarter_length + (expected - actual),
                    is_rest=measure_notes[-1].is_rest,
                    tied=measure_notes[-1].tied,
                )

            measure_notes[0].bar_start = True
            notes.extend(measure_notes)

        return notes

    def _flat_to_notes(self, elements) -> list[BassNote]:
        """Legacy flat extraction used when no Measure objects are present."""
        notes = []
        for el in elements:
            tied = (
                isinstance(el, music21.note.Note)
                and el.tie is not None
                and el.tie.type in ("start", "continue")
            )
            if isinstance(el, music21.note.Rest):
                notes.append(BassNote(midi=0, quarter_length=float(el.quarterLength),
                                      is_rest=True, tied=False))
            elif isinstance(el, music21.note.Note):
                notes.append(BassNote(midi=el.pitch.midi,
                                      quarter_length=float(el.quarterLength),
                                      is_rest=False, tied=tied))
            elif isinstance(el, music21.chord.Chord):
                lowest = min(el.pitches, key=lambda p: p.midi)
                notes.append(BassNote(midi=lowest.midi,
                                      quarter_length=float(el.quarterLength),
                                      is_rest=False, tied=tied))
        return notes
