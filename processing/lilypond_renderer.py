import subprocess
from pathlib import Path
from processing.models import AssignedNote

NOTE_NAMES = ['c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b']

DURATION_MAP = {
    4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4",
    0.75: "8.", 0.5: "8", 0.375: "16.", 0.25: "16", 0.125: "32",
}

TUNING_4 = "\\set TabStaff.stringTunings = #bass-tuning"
TUNING_5 = "\\set TabStaff.stringTunings = #bass-five-string-tuning"


def midi_to_lily_pitch(midi: int) -> str:
    note_name = NOTE_NAMES[midi % 12]
    octave = midi // 12 - 1   # MIDI octave (C4=oct4)
    lily_octave = octave - 3  # C3 is the reference (no marks)
    if lily_octave >= 0:
        return note_name + "'" * lily_octave
    else:
        return note_name + "," * (-lily_octave)


def ql_to_lily_duration(ql: float) -> str:
    rounded = round(ql * 8) / 8
    if rounded in DURATION_MAP:
        return DURATION_MAP[rounded]
    # Fallback: nearest common value
    nearest = min(DURATION_MAP.keys(), key=lambda k: abs(k - ql))
    return DURATION_MAP[nearest]


class LilyPondRenderer:
    def __init__(self, tmp_dir: Path, num_strings: int = 4):
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.num_strings = num_strings
        self.tuning_cmd = TUNING_5 if num_strings == 5 else TUNING_4

    def _lily_string_num(self, string_idx: int) -> int:
        """Convert our 0-based (lowest) idx to LilyPond 1-based (highest=1)."""
        return self.num_strings - string_idx

    def _note_to_lily(self, note: AssignedNote, prev_duration: str | None) -> str:
        if note.is_rest:
            dur = ql_to_lily_duration(note.quarter_length)
            return f"r{dur}"
        pitch = midi_to_lily_pitch(note.midi)
        dur = ql_to_lily_duration(note.quarter_length)
        # Omit duration if same as previous (LilyPond convention)
        dur_str = dur if dur != prev_duration else ""
        string_mark = f"\\{self._lily_string_num(note.string_idx)}"
        tie = "~" if note.tied else ""
        out_of_range = "^\\markup { \\small \"?\" }" if note.fret < 0 else ""
        return f"{pitch}{dur_str}{string_mark}{tie}{out_of_range}"

    def generate_ly(self, notes: list[AssignedNote], title: str = "") -> str:
        tokens = []
        prev_dur = None
        for note in notes:
            tokens.append(self._note_to_lily(note, prev_dur))
            if not note.is_rest:
                prev_dur = ql_to_lily_duration(note.quarter_length)

        music_body = " ".join(tokens)
        escaped_title = title.replace('"', '\\"')

        return f"""\\version "2.24.0"
\\paper {{
  #(set-paper-size "a4")
}}
\\header {{
  title = "{escaped_title}"
  tagline = ##f
}}
bassMusic = {{
  \\clef bass
  {music_body}
}}
\\score {{
  <<
    \\new Staff {{ \\bassMusic }}
    \\new TabStaff {{
      {self.tuning_cmd}
      \\bassMusic
    }}
  >>
  \\layout {{}}
}}
"""

    def render(self, notes: list[AssignedNote], title: str = "Bass Tab") -> Path:
        """Generate .ly file and render to PDF. Returns PDF path."""
        ly_content = self.generate_ly(notes, title)
        ly_path = self.tmp_dir / "output.ly"
        ly_path.write_text(ly_content, encoding="utf-8")

        result = subprocess.run(
            ["lilypond", "--pdf", "-o", str(self.tmp_dir / "output"), str(ly_path)],
            capture_output=True, text=True, cwd=str(self.tmp_dir)
        )
        if result.returncode != 0:
            raise RuntimeError(f"LilyPond error:\n{result.stderr}")

        pdf_path = self.tmp_dir / "output.pdf"
        if not pdf_path.exists():
            raise RuntimeError("LilyPond ran but produced no PDF")
        return pdf_path
