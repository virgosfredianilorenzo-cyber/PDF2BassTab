import shutil
import subprocess
from pathlib import Path
from processing.models import AssignedNote


def _find_lilypond() -> str:
    """Locate the lilypond binary, checking ~/.local/bin first."""
    local_bin = Path.home() / ".local" / "bin" / "lilypond"
    if local_bin.exists():
        return str(local_bin)
    found = shutil.which("lilypond")
    if found:
        return found
    raise RuntimeError(
        "LilyPond not found. Install it or place the binary at ~/.local/bin/lilypond"
    )

NOTE_NAMES = ['c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b']

DURATION_MAP = {
    4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4",
    0.75: "8.", 0.5: "8", 0.375: "16.", 0.25: "16", 0.125: "32",
}

# Custom tunings matching fret_assigner.py TUNING_4/5 (E2 A2 D3 G3 = MIDI 40 45 50 55).
# LilyPond's built-in #bass-tuning uses E1/A1/D2/G2 (MIDI 28/33/38/43) — one octave lower —
# which causes every fret number to appear 12 positions too high.
TUNING_4 = (
    "\\set TabStaff.stringTunings = "
    "#`(,(ly:make-pitch -1 4 0)"   # G3 = MIDI 55
    " ,(ly:make-pitch -1 1 0)"     # D3 = MIDI 50
    " ,(ly:make-pitch -2 5 0)"     # A2 = MIDI 45
    " ,(ly:make-pitch -2 2 0))"    # E2 = MIDI 40
)
TUNING_5 = (
    "\\set TabStaff.stringTunings = "
    "#`(,(ly:make-pitch -1 4 0)"   # G3 = MIDI 55
    " ,(ly:make-pitch -1 1 0)"     # D3 = MIDI 50
    " ,(ly:make-pitch -2 5 0)"     # A2 = MIDI 45
    " ,(ly:make-pitch -2 2 0)"     # E2 = MIDI 40
    " ,(ly:make-pitch -3 6 0))"    # B1 = MIDI 35
)


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

    def _note_to_lily(self, note: AssignedNote, prev_duration: str | None, skip_bar: bool = False) -> str:
        bar = "" if skip_bar else ("| " if note.bar_start else "")
        if note.is_rest:
            dur = ql_to_lily_duration(note.quarter_length)
            return f"{bar}r{dur}"
        pitch = midi_to_lily_pitch(note.midi)
        dur = ql_to_lily_duration(note.quarter_length)
        dur_str = dur if dur != prev_duration else ""
        string_mark = f"\\{self._lily_string_num(note.string_idx)}"
        tie = "~" if note.tied else ""
        out_of_range = "^\\markup { \\small \"?\" }" if note.fret < 0 else ""
        return f"{bar}{pitch}{dur_str}{string_mark}{tie}{out_of_range}"

    def generate_ly(self, notes: list[AssignedNote], title: str = "") -> str:
        tokens = []
        prev_dur = None
        first = True
        for note in notes:
            tokens.append(self._note_to_lily(note, prev_dur, skip_bar=first))
            first = False
            if not note.is_rest:
                prev_dur = ql_to_lily_duration(note.quarter_length)

        music_body = "\n  ".join(tokens)
        escaped_title = title.replace('"', '\\"')

        return f"""\\version "2.24.0"
\\paper {{
  #(set-paper-size "a4")
  ragged-last-bottom = ##f
  ragged-last = ##f
}}
\\header {{
  title = "{escaped_title}"
  tagline = ##f
}}
% Custom note-head stencil: open circle (white fill) with English note letter.
% Uses grob-interpret-markup so the text font is resolved correctly in the grob
% context (interpret-markup alone omits font props → nan extents → crash).
#(define (open-circle-note-head grob)
  (let* ((event  (ly:grob-property grob 'cause))
         (pitch  (ly:event-property event 'pitch))
         (idx    (ly:pitch-notename pitch))
         (names  #("C" "D" "E" "F" "G" "A" "B"))
         (letter (vector-ref names idx))
         (m      (markup #:bold #:fontsize -1 letter))
         (stil   (grob-interpret-markup grob m))
         (x-ext  (ly:stencil-extent stil X))
         (y-ext  (ly:stencil-extent stil Y))
         (r      (+ (max (/ (- (cdr x-ext) (car x-ext)) 2)
                         (/ (- (cdr y-ext) (car y-ext)) 2))
                    0.3))
         (circ   (make-circle-stencil r 0.1 #f))
         (cx     (/ (+ (car x-ext) (cdr x-ext)) 2))
         (cy     (/ (+ (car y-ext) (cdr y-ext)) 2)))
    (ly:stencil-add circ
                    (ly:stencil-translate stil (cons (- cx) (- cy))))))
bassMusic = {{
  \\clef bass
  {music_body}
}}
\\score {{
  <<
    \\new Staff {{
      \\override NoteHead.stencil = #open-circle-note-head
      \\override StringNumber.stencil = ##f
      \\bassMusic
    }}
    \\new TabStaff {{
      {self.tuning_cmd}
      \\bassMusic
    }}
  >>
  \\layout {{
    indent = 0\\mm
    short-indent = 0\\mm
  }}
}}
"""

    def render(self, notes: list[AssignedNote], title: str = "Bass Tab") -> Path:
        """Generate .ly file and render to PDF. Returns PDF path."""
        ly_content = self.generate_ly(notes, title)
        tmp_abs = self.tmp_dir.resolve()
        ly_path = tmp_abs / "output.ly"
        ly_path.write_text(ly_content, encoding="utf-8")

        lilypond_bin = _find_lilypond()
        result = subprocess.run(
            [lilypond_bin, "--pdf", "-o", str(tmp_abs / "output"), str(ly_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LilyPond error:\n{result.stderr}")

        pdf_path = tmp_abs / "output.pdf"
        if not pdf_path.exists():
            raise RuntimeError("LilyPond ran but produced no PDF")
        return pdf_path
