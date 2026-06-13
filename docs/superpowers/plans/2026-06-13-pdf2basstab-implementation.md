# PDF2BassTab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire une application web FastAPI+HTMX qui convertit des partitions (PDF/MIDI/MusicXML/MSCZ) en tablatures basse 4 ou 5 cordes au format PDF via Audiveris OMR, music21 et LilyPond.

**Architecture:** InputRouter normalise tout input vers MusicXML ; BassExtractor identifie la partie basse via music21 ; FretAssigner calcule les positions de frettes par programmation dynamique ; LilyPondRenderer génère le PDF tablature ; FastAPI+HTMX sert l'interface drag-and-drop.

**Tech Stack:** Python 3.11+, FastAPI, music21, LilyPond, Audiveris (JAR Java), HTMX, Jinja2

---

## Fichiers créés par ce plan

```
PDF2BassTab/
├── api/
│   ├── main.py              # FastAPI app + routes
│   └── pipeline.py          # Orchestrateur + gestion jobs
├── processing/
│   ├── models.py            # Dataclasses partagées
│   ├── input_router.py      # Détection format → MusicXML
│   ├── omr.py               # Wrapper Audiveris (subprocess)
│   ├── music_parser.py      # Parsing music21 + listing parts
│   ├── bass_extractor.py    # Identification partie basse
│   ├── fret_assigner.py     # Algorithme DP frettes
│   ├── lilypond_renderer.py # Génération .ly + appel lilypond
│   └── musescore_exporter.py# Export .mscz ou MusicXML fallback
├── web/
│   ├── templates/
│   │   ├── index.html       # Page principale HTMX
│   │   └── result.html      # Fragment résultat (polling)
│   └── static/
│       └── style.css
├── tests/
│   ├── test_fret_assigner.py
│   ├── test_input_router.py
│   ├── test_bass_extractor.py
│   ├── test_lilypond_renderer.py
│   └── test_integration.py
├── tools/                   # Audiveris JAR (gitignored)
├── tmp/                     # Jobs temporaires (gitignored)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Task 1 : Scaffolding du projet

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `processing/__init__.py`, `api/__init__.py`, `tests/__init__.py`

- [ ] **Créer requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
jinja2==3.1.4
music21==9.3.0
aiofiles==24.1.0
pytest==8.3.0
pytest-asyncio==0.23.8
httpx==0.27.0
```

- [ ] **Créer .gitignore**

```
__pycache__/
*.pyc
.env
tmp/
tools/audiveris*.jar
*.pdf
!Exemples/*.pdf
*.mscz
!Exemples/*.mscz
.venv/
dist/
*.egg-info/
```

- [ ] **Créer les `__init__.py` vides**

```bash
mkdir -p api processing web/templates web/static tests tools tmp
touch api/__init__.py processing/__init__.py tests/__init__.py
```

- [ ] **Installer les dépendances**

```bash
pip install -r requirements.txt
```

Expected: installation sans erreur, `python -c "import music21, fastapi"` ne lève pas d'exception.

- [ ] **Vérifier LilyPond installé**

```bash
lilypond --version
```

Si absent : `sudo apt install lilypond` (ou `brew install lilypond` sur Mac).

- [ ] **Vérifier Java 17+ disponible (pour Audiveris)**

```bash
java -version
```

Si absent : `sudo apt install default-jre`

- [ ] **Commit**

```bash
git add requirements.txt .gitignore api/ processing/ web/ tests/ tools/ tmp/
git commit -m "chore: project scaffolding"
```

---

## Task 2 : Modèle de données partagé

**Files:**
- Create: `processing/models.py`
- Create: `tests/test_models.py`

- [ ] **Écrire le test**

```python
# tests/test_models.py
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
```

- [ ] **Faire échouer le test**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'BassNote'`

- [ ] **Implémenter models.py**

```python
# processing/models.py
from dataclasses import dataclass, field

@dataclass
class BassNote:
    midi: int           # MIDI note number (0 if is_rest)
    quarter_length: float
    is_rest: bool
    tied: bool = False

@dataclass
class AssignedNote(BassNote):
    string_idx: int = 0  # 0 = lowest string
    fret: int = 0
```

- [ ] **Faire passer le test**

```bash
pytest tests/test_models.py -v
```

Expected: 3 passed.

- [ ] **Commit**

```bash
git add processing/models.py tests/test_models.py
git commit -m "feat: add BassNote and AssignedNote dataclasses"
```

---

## Task 3 : FretAssigner — algorithme DP

**Files:**
- Create: `processing/fret_assigner.py`
- Create: `tests/test_fret_assigner.py`

**Accordages (MIDI) :**
- 4 cordes : `[40, 45, 50, 55]` (E2, A2, D3, G3)
- 5 cordes : `[35, 40, 45, 50, 55]` (B1, E2, A2, D3, G3)

- [ ] **Écrire les tests**

```python
# tests/test_fret_assigner.py
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
```

- [ ] **Faire échouer les tests**

```bash
pytest tests/test_fret_assigner.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Implémenter fret_assigner.py**

```python
# processing/fret_assigner.py
from dataclasses import replace
from processing.models import BassNote, AssignedNote

TUNING_4 = [40, 45, 50, 55]   # E2, A2, D3, G3
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
```

- [ ] **Faire passer les tests**

```bash
pytest tests/test_fret_assigner.py -v
```

Expected: 8 passed.

- [ ] **Commit**

```bash
git add processing/fret_assigner.py tests/test_fret_assigner.py
git commit -m "feat: FretAssigner with DP algorithm (4/5 strings)"
```

---

## Task 4 : InputRouter — détection de format

**Files:**
- Create: `processing/input_router.py`
- Create: `tests/test_input_router.py`

L'InputRouter reçoit un chemin de fichier et retourne un chemin vers un fichier MusicXML temporaire. Pour PDF, il délègue à `omr.py` (Task 5). Pour .mscz, il appelle MuseScore CLI si disponible, sinon lève `UnsupportedFormatError`.

- [ ] **Écrire les tests**

```python
# tests/test_input_router.py
import shutil, tempfile
from pathlib import Path
import pytest
from processing.input_router import InputRouter, UnsupportedFormatError

EXAMPLES = Path("Exemples")

def test_musicxml_passthrough(tmp_path):
    src = EXAMPLES / "michael_bublefeeling_good.musicxml"
    router = InputRouter(tmp_dir=tmp_path)
    result = router.route(src)
    assert result.suffix in (".xml", ".musicxml")
    assert result.exists()

def test_mxl_extraction(tmp_path):
    src = EXAMPLES / "michael_bublefeeling_good.mxl"
    router = InputRouter(tmp_dir=tmp_path)
    result = router.route(src)
    assert result.suffix in (".xml", ".musicxml")
    assert result.exists()

def test_midi_conversion(tmp_path):
    src = EXAMPLES / "michael_bublefeeling_good.mid"
    router = InputRouter(tmp_dir=tmp_path)
    result = router.route(src)
    assert result.suffix in (".xml", ".musicxml")
    assert result.exists()

def test_unsupported_format(tmp_path):
    fake = tmp_path / "file.xyz"
    fake.write_text("garbage")
    router = InputRouter(tmp_dir=tmp_path)
    with pytest.raises(UnsupportedFormatError):
        router.route(fake)
```

- [ ] **Faire échouer les tests**

```bash
pytest tests/test_input_router.py -v
```

Expected: `ImportError`

- [ ] **Implémenter input_router.py**

```python
# processing/input_router.py
import shutil
import zipfile
from pathlib import Path
import music21


class UnsupportedFormatError(Exception):
    pass


class InputRouter:
    def __init__(self, tmp_dir: Path):
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def route(self, src: Path) -> Path:
        """Convert any supported input to a MusicXML file path."""
        src = Path(src)
        suffix = src.suffix.lower()

        if suffix in (".musicxml", ".xml"):
            dest = self.tmp_dir / src.name
            shutil.copy2(src, dest)
            return dest

        if suffix == ".mxl":
            return self._extract_mxl(src)

        if suffix in (".mid", ".midi"):
            return self._convert_midi(src)

        if suffix == ".mscz":
            return self._convert_mscz(src)

        if suffix == ".pdf":
            # Delegated to omr.py — caller must use omr.run() before routing
            raise UnsupportedFormatError(
                "PDF requires OMR preprocessing. Use omr.run() first."
            )

        raise UnsupportedFormatError(f"Unsupported format: {suffix}")

    def _extract_mxl(self, src: Path) -> Path:
        """Unzip .mxl and return the inner .xml file."""
        with zipfile.ZipFile(src) as z:
            xml_names = [n for n in z.namelist()
                         if n.endswith(".xml") and not n.startswith("__")]
            if not xml_names:
                raise UnsupportedFormatError("No .xml found inside .mxl archive")
            dest = self.tmp_dir / xml_names[0]
            z.extract(xml_names[0], self.tmp_dir)
            return dest

    def _convert_midi(self, src: Path) -> Path:
        """Convert MIDI to MusicXML using music21."""
        score = music21.converter.parse(str(src))
        dest = self.tmp_dir / (src.stem + ".musicxml")
        score.write("musicxml", fp=str(dest))
        return dest

    def _convert_mscz(self, src: Path) -> Path:
        """Convert .mscz to MusicXML via MuseScore CLI."""
        import shutil as _shutil
        import subprocess

        mscore = _shutil.which("mscore") or _shutil.which("musescore") \
                 or _shutil.which("mscore3") or _shutil.which("musescore3")
        if not mscore:
            raise UnsupportedFormatError(
                ".mscz requires MuseScore CLI. Install MuseScore and ensure "
                "'mscore' or 'musescore' is in PATH."
            )
        dest = self.tmp_dir / (src.stem + ".musicxml")
        subprocess.run(
            [mscore, "-o", str(dest), str(src)],
            check=True, capture_output=True
        )
        return dest
```

- [ ] **Faire passer les tests**

```bash
pytest tests/test_input_router.py -v
```

Expected: 4 passed. (Le test midi peut être lent ~5s, c'est normal.)

- [ ] **Commit**

```bash
git add processing/input_router.py tests/test_input_router.py
git commit -m "feat: InputRouter handles MusicXML/MXL/MIDI/MSCZ"
```

---

## Task 5 : OMR wrapper (Audiveris)

**Files:**
- Create: `processing/omr.py`
- Create: `tests/test_omr.py`

Audiveris doit être téléchargé manuellement dans `tools/`. Ce module est un wrapper subprocess.

- [ ] **Télécharger Audiveris**

Aller sur https://github.com/Audiveris/audiveris/releases et télécharger le dernier `.jar` (ex: `Audiveris-5.x.jar`). Le placer dans `tools/audiveris.jar`.

```bash
ls tools/audiveris.jar  # vérifier qu'il est là
```

- [ ] **Écrire le test**

```python
# tests/test_omr.py
from pathlib import Path
import pytest
from processing.omr import AudiverisOMR, OMRError

TOOLS = Path("tools")
EXAMPLES = Path("Exemples")

def test_omr_jar_present():
    """L'utilisateur doit avoir placé audiveris.jar dans tools/."""
    assert (TOOLS / "audiveris.jar").exists(), \
        "Télécharger Audiveris JAR dans tools/audiveris.jar"

@pytest.mark.slow
def test_omr_single_part_pdf(tmp_path):
    """Test OMR sur la partition basse (2 pages)."""
    omr = AudiverisOMR(jar_path=TOOLS / "audiveris.jar", tmp_dir=tmp_path)
    result = omr.run(EXAMPLES / "reujb_feeling-good-full-big-band-amy-michael-buble-Basse.pdf")
    assert result.exists()
    assert result.suffix in (".xml", ".musicxml", ".mxl")
```

- [ ] **Faire échouer les tests non-lents**

```bash
pytest tests/test_omr.py -v -k "not slow"
```

- [ ] **Implémenter omr.py**

```python
# processing/omr.py
import subprocess
import zipfile
from pathlib import Path


class OMRError(Exception):
    pass


class AudiverisOMR:
    def __init__(self, jar_path: Path, tmp_dir: Path):
        self.jar = Path(jar_path)
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        if not self.jar.exists():
            raise OMRError(f"Audiveris JAR not found: {self.jar}")

    def run(self, pdf_path: Path) -> Path:
        """Run Audiveris OMR on a PDF. Returns path to MusicXML output."""
        pdf_path = Path(pdf_path)
        out_dir = self.tmp_dir / "audiveris_out"
        out_dir.mkdir(exist_ok=True)

        cmd = [
            "java", "-jar", str(self.jar),
            "-batch", "-export",
            "-output", str(out_dir),
            str(pdf_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise OMRError(f"Audiveris failed:\n{proc.stderr}")

        # Audiveris outputs .mxl files
        mxl_files = list(out_dir.glob("**/*.mxl"))
        xml_files = list(out_dir.glob("**/*.xml"))

        candidates = mxl_files or xml_files
        if not candidates:
            raise OMRError("Audiveris produced no output files")

        return candidates[0]
```

- [ ] **Vérifier que le test JAR passe**

```bash
pytest tests/test_omr.py::test_omr_jar_present -v
```

- [ ] **Commit**

```bash
git add processing/omr.py tests/test_omr.py
git commit -m "feat: Audiveris OMR wrapper"
```

---

## Task 6 : MusicParser + BassExtractor

**Files:**
- Create: `processing/music_parser.py`
- Create: `processing/bass_extractor.py`
- Create: `tests/test_bass_extractor.py`

- [ ] **Écrire les tests**

```python
# tests/test_bass_extractor.py
from pathlib import Path
import pytest
from processing.music_parser import MusicParser
from processing.bass_extractor import BassExtractor, NoBassPartError
from processing.models import BassNote

EXAMPLES = Path("Exemples")
MUSICXML = EXAMPLES / "michael_bublefeeling_good.musicxml"

def test_list_parts():
    parser = MusicParser()
    score = parser.parse(MUSICXML)
    parts = parser.list_parts(score)
    assert len(parts) >= 1
    assert all(isinstance(name, str) for name in parts)

def test_extract_bass_auto():
    parser = MusicParser()
    score = parser.parse(MUSICXML)
    extractor = BassExtractor()
    notes = extractor.extract(score)
    assert len(notes) > 0
    assert all(isinstance(n, BassNote) for n in notes)

def test_extract_bass_by_name():
    parser = MusicParser()
    score = parser.parse(MUSICXML)
    parts = parser.list_parts(score)
    extractor = BassExtractor()
    notes = extractor.extract(score, part_name=parts[0])
    assert len(notes) > 0

def test_notes_contain_rests_and_pitched():
    parser = MusicParser()
    score = parser.parse(MUSICXML)
    extractor = BassExtractor()
    notes = extractor.extract(score)
    has_rest = any(n.is_rest for n in notes)
    has_pitched = any(not n.is_rest for n in notes)
    assert has_rest and has_pitched

def test_no_bass_raises():
    """Partition sans partie basse → exception."""
    import music21
    score = music21.stream.Score()
    p = music21.stream.Part()
    p.partName = "Violon"
    score.append(p)
    extractor = BassExtractor()
    with pytest.raises(NoBassPartError):
        extractor.extract(score)
```

- [ ] **Faire échouer les tests**

```bash
pytest tests/test_bass_extractor.py -v
```

- [ ] **Implémenter music_parser.py**

```python
# processing/music_parser.py
from pathlib import Path
import music21


class MusicParser:
    def parse(self, musicxml_path: Path) -> music21.stream.Score:
        return music21.converter.parse(str(musicxml_path))

    def list_parts(self, score: music21.stream.Score) -> list[str]:
        """Return part names (or IDs if names are absent)."""
        names = []
        for part in score.parts:
            name = part.partName or part.id or f"Part {len(names)+1}"
            names.append(name)
        return names
```

- [ ] **Implémenter bass_extractor.py**

```python
# processing/bass_extractor.py
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
            name = (part.partName or part.id or "").lower()
            if any(kw in name for kw in BASS_KEYWORDS):
                candidates.append(part)

        if not candidates:
            raise NoBassPartError("No bass part found in score")
        if len(candidates) > 1:
            names = [p.partName or p.id for p in candidates]
            raise AmbiguousBassError(names)
        return candidates[0]

    def _part_to_notes(self, part: music21.stream.Part) -> list[BassNote]:
        notes: list[BassNote] = []
        flat = part.flat.notesAndRests
        elements = list(flat)
        for i, el in enumerate(elements):
            tied = (
                isinstance(el, music21.note.Note)
                and el.tie is not None
                and el.tie.type in ("start", "continue")
            )
            if isinstance(el, music21.note.Rest):
                notes.append(BassNote(
                    midi=0,
                    quarter_length=float(el.quarterLength),
                    is_rest=True,
                    tied=False,
                ))
            elif isinstance(el, music21.note.Note):
                notes.append(BassNote(
                    midi=el.pitch.midi,
                    quarter_length=float(el.quarterLength),
                    is_rest=False,
                    tied=tied,
                ))
            elif isinstance(el, music21.chord.Chord):
                # For chords, take the lowest note
                lowest = min(el.pitches, key=lambda p: p.midi)
                notes.append(BassNote(
                    midi=lowest.midi,
                    quarter_length=float(el.quarterLength),
                    is_rest=False,
                    tied=tied,
                ))
        return notes
```

- [ ] **Faire passer les tests**

```bash
pytest tests/test_bass_extractor.py -v
```

Expected: 5 passed.

- [ ] **Commit**

```bash
git add processing/music_parser.py processing/bass_extractor.py tests/test_bass_extractor.py
git commit -m "feat: MusicParser and BassExtractor with music21"
```

---

## Task 7 : LilyPondRenderer

**Files:**
- Create: `processing/lilypond_renderer.py`
- Create: `tests/test_lilypond_renderer.py`

- [ ] **Écrire les tests**

```python
# tests/test_lilypond_renderer.py
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
```

- [ ] **Faire échouer les tests non-lents**

```bash
pytest tests/test_lilypond_renderer.py -v -k "not slow"
```

- [ ] **Implémenter lilypond_renderer.py**

```python
# processing/lilypond_renderer.py
import subprocess
from pathlib import Path
from processing.models import AssignedNote

NOTE_NAMES = ['c', 'cis', 'd', 'dis', 'e', 'f', 'fis', 'g', 'gis', 'a', 'ais', 'b']

DURATION_MAP = {
    4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4",
    0.75: "8.", 0.5: "8", 0.375: "16.", 0.25: "16", 0.125: "32",
}

TUNING_4 = "\\set TabStaff.stringTunings = #'(40 45 50 55)"
TUNING_5 = "\\set TabStaff.stringTunings = #'(35 40 45 50 55)"


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
```

- [ ] **Faire passer tous les tests (y compris slow)**

```bash
pytest tests/test_lilypond_renderer.py -v
```

Expected: 4 passed. (Le test slow appelle LilyPond, prend ~5s.)

- [ ] **Commit**

```bash
git add processing/lilypond_renderer.py tests/test_lilypond_renderer.py
git commit -m "feat: LilyPondRenderer generates .ly and renders PDF"
```

---

## Task 8 : MuseScoreExporter

**Files:**
- Create: `processing/musescore_exporter.py`
- Create: `tests/test_musescore_exporter.py`

- [ ] **Écrire les tests**

```python
# tests/test_musescore_exporter.py
from pathlib import Path
import music21
from processing.musescore_exporter import MuseScoreExporter

EXAMPLES = Path("Exemples")

def make_simple_score() -> music21.stream.Score:
    score = music21.stream.Score()
    part = music21.stream.Part()
    part.partName = "Basse"
    m = music21.stream.Measure()
    m.append(music21.note.Note("E2", quarterLength=1.0))
    m.append(music21.note.Note("A2", quarterLength=1.0))
    part.append(m)
    score.append(part)
    return score

def test_export_musicxml_fallback(tmp_path):
    """Sans MuseScore CLI, exporte en MusicXML."""
    exporter = MuseScoreExporter(tmp_dir=tmp_path)
    score = make_simple_score()
    result = exporter.export(score)
    assert result.exists()
    assert result.suffix in (".musicxml", ".xml", ".mscz")
```

- [ ] **Faire échouer le test**

```bash
pytest tests/test_musescore_exporter.py -v
```

- [ ] **Implémenter musescore_exporter.py**

```python
# processing/musescore_exporter.py
import shutil
import subprocess
from pathlib import Path
import music21


class MuseScoreExporter:
    def __init__(self, tmp_dir: Path):
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self._mscore = (
            shutil.which("mscore")
            or shutil.which("musescore")
            or shutil.which("mscore3")
            or shutil.which("musescore3")
        )

    @property
    def musescore_available(self) -> bool:
        return self._mscore is not None

    def export(self, score: music21.stream.Score) -> Path:
        """Export to .mscz if MuseScore available, else fallback to MusicXML."""
        xml_path = self.tmp_dir / "score.musicxml"
        score.write("musicxml", fp=str(xml_path))

        if not self.musescore_available:
            return xml_path

        mscz_path = self.tmp_dir / "score.mscz"
        result = subprocess.run(
            [self._mscore, "-o", str(mscz_path), str(xml_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and mscz_path.exists():
            return mscz_path
        # Fallback silently on failure
        return xml_path
```

- [ ] **Faire passer le test**

```bash
pytest tests/test_musescore_exporter.py -v
```

- [ ] **Commit**

```bash
git add processing/musescore_exporter.py tests/test_musescore_exporter.py
git commit -m "feat: MuseScoreExporter with MusicXML fallback"
```

---

## Task 9 : Pipeline orchestrateur

**Files:**
- Create: `api/pipeline.py`

Le pipeline gère les jobs en mémoire. Chaque job a un UUID, un statut, et les chemins de sortie.

- [ ] **Implémenter api/pipeline.py**

```python
# api/pipeline.py
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import music21

from processing.bass_extractor import BassExtractor, AmbiguousBassError, NoBassPartError
from processing.fret_assigner import FretAssigner, detect_string_count
from processing.input_router import InputRouter, UnsupportedFormatError
from processing.lilypond_renderer import LilyPondRenderer
from processing.music_parser import MusicParser
from processing.musescore_exporter import MuseScoreExporter
from processing.omr import AudiverisOMR


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_PART_SELECTION = "awaiting_part"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    error: str = ""
    pdf_path: Path | None = None
    score_path: Path | None = None
    part_candidates: list[str] = field(default_factory=list)
    musicxml_path: Path | None = None  # cached for part re-selection
    title: str = ""
    num_strings: int | None = None
    export_musescore: bool = True


# In-memory job store (keyed by job_id)
JOBS: dict[str, Job] = {}

TMP_ROOT = Path("tmp")
TOOLS_DIR = Path("tools")


def new_job() -> Job:
    job_id = str(uuid.uuid4())
    job = Job(job_id=job_id)
    JOBS[job_id] = job
    return job


def run_pipeline(
    job_id: str,
    input_path: Path,
    num_strings: int | None,
    export_musescore: bool,
    part_name: str | None = None,
) -> None:
    """Execute full pipeline. Called from background task."""
    job = JOBS[job_id]
    job.status = JobStatus.RUNNING
    job.num_strings = num_strings
    job.export_musescore = export_musescore

    tmp_dir = TMP_ROOT / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Normalize to MusicXML
        if job.musicxml_path is None:
            suffix = input_path.suffix.lower()
            if suffix == ".pdf":
                jar = TOOLS_DIR / "audiveris.jar"
                omr = AudiverisOMR(jar_path=jar, tmp_dir=tmp_dir / "omr")
                mxl_path = omr.run(input_path)
                # Route the OMR output (mxl or xml) to get a proper MusicXML
                router = InputRouter(tmp_dir=tmp_dir / "routed")
                musicxml_path = router.route(mxl_path)
            else:
                router = InputRouter(tmp_dir=tmp_dir / "routed")
                musicxml_path = router.route(input_path)
            job.musicxml_path = musicxml_path

        # Step 2: Parse + extract bass part
        parser = MusicParser()
        score = parser.parse(job.musicxml_path)
        job.title = str(score.metadata.title or input_path.stem) if score.metadata else input_path.stem

        extractor = BassExtractor()
        try:
            notes = extractor.extract(score, part_name=part_name)
        except NoBassPartError:
            # Fallback: if only one part (e.g. MIDI), use it directly
            parts = parser.list_parts(score)
            if len(parts) == 1:
                notes = extractor.extract(score, part_name=parts[0])
            elif len(parts) > 1:
                job.status = JobStatus.AWAITING_PART_SELECTION
                job.part_candidates = parts
                return
            else:
                raise
        except AmbiguousBassError as e:
            job.status = JobStatus.AWAITING_PART_SELECTION
            job.part_candidates = e.candidates
            return

        # Step 3: Assign frets
        strings = num_strings or detect_string_count(notes)
        fa = FretAssigner(num_strings=strings)
        assigned = fa.assign(notes)

        # Step 4: Render PDF
        renderer = LilyPondRenderer(tmp_dir=tmp_dir / "lily", num_strings=strings)
        pdf_path = renderer.render(assigned, title=job.title)
        job.pdf_path = pdf_path

        # Step 5: Export MuseScore (optional)
        if export_musescore:
            exporter = MuseScoreExporter(tmp_dir=tmp_dir / "musescore")
            job.score_path = exporter.export(score)

        job.status = JobStatus.DONE

    except (UnsupportedFormatError, NoBassPartError, RuntimeError, Exception) as e:
        job.status = JobStatus.ERROR
        job.error = str(e)
```

- [ ] **Vérifier que l'import fonctionne**

```bash
python -c "from api.pipeline import new_job, JOBS; print('OK')"
```

Expected: `OK`

- [ ] **Commit**

```bash
git add api/pipeline.py
git commit -m "feat: Pipeline orchestrator with job state management"
```

---

## Task 10 : FastAPI app

**Files:**
- Create: `api/main.py`

- [ ] **Implémenter api/main.py**

```python
# api/main.py
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from api.pipeline import (
    JOBS, JobStatus, new_job, run_pipeline
)

app = FastAPI(title="PDF2BassTab")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

TMP_ROOT = Path("tmp")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    strings: int = Form(default=0),      # 0 = auto
    export_musescore: bool = Form(default=True),
):
    job = new_job()
    input_dir = TMP_ROOT / job.job_id / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    input_path = input_dir / file.filename

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    num_strings = strings if strings in (4, 5) else None
    background_tasks.add_task(
        run_pipeline, job.job_id, input_path, num_strings, export_musescore
    )

    return templates.TemplateResponse(
        "result.html",
        {"request": request, "job": job},
    )


@app.get("/status/{job_id}", response_class=HTMLResponse)
async def status(request: Request, job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("<p>Job inconnu</p>", status_code=404)
    return templates.TemplateResponse(
        "result.html", {"request": request, "job": job}
    )


@app.post("/select-part/{job_id}", response_class=HTMLResponse)
async def select_part(
    request: Request,
    job_id: str,
    background_tasks: BackgroundTasks,
    part_name: str = Form(...),
):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("<p>Job inconnu</p>", status_code=404)

    input_dir = TMP_ROOT / job_id / "input"
    input_files = list(input_dir.iterdir())
    if not input_files:
        return HTMLResponse("<p>Fichier introuvable</p>", status_code=404)

    job.status = JobStatus.RUNNING
    job.part_candidates = []
    background_tasks.add_task(
        run_pipeline, job_id, input_files[0],
        job.num_strings, job.export_musescore, part_name
    )
    return templates.TemplateResponse(
        "result.html", {"request": request, "job": job}
    )


@app.get("/download/{job_id}/{filename}")
async def download(job_id: str, filename: str):
    job = JOBS.get(job_id)
    if job is None:
        return HTMLResponse("Job inconnu", status_code=404)

    if filename == "tab.pdf" and job.pdf_path and job.pdf_path.exists():
        return FileResponse(job.pdf_path, filename="tablature.pdf")

    if filename == "score" and job.score_path and job.score_path.exists():
        ext = job.score_path.suffix
        return FileResponse(job.score_path, filename=f"score{ext}")

    return HTMLResponse("Fichier non disponible", status_code=404)
```

- [ ] **Vérifier que l'app démarre**

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Ouvrir http://localhost:8000 dans un navigateur. Expected: page blanche ou erreur de template (normal, templates pas encore créés).

Arrêter avec Ctrl+C.

- [ ] **Commit**

```bash
git add api/main.py
git commit -m "feat: FastAPI routes upload/status/download/select-part"
```

---

## Task 11 : Templates HTMX

**Files:**
- Create: `web/templates/index.html`
- Create: `web/templates/result.html`
- Create: `web/static/style.css`

- [ ] **Créer index.html**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>PDF2BassTab</title>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <h1>PDF2BassTab</h1>
  <p>Convertissez une partition en tablature basse PDF.</p>

  <form hx-post="/upload"
        hx-encoding="multipart/form-data"
        hx-target="#result"
        hx-swap="innerHTML">

    <div id="drop-zone">
      <input type="file" name="file" id="file-input" accept=".pdf,.mid,.midi,.musicxml,.xml,.mxl,.mscz" required>
      <label for="file-input">Glissez un fichier ici ou cliquez pour choisir<br>
        <small>PDF · MIDI · MusicXML · MXL · MSCZ</small>
      </label>
    </div>

    <fieldset>
      <legend>Cordes</legend>
      <label><input type="radio" name="strings" value="0" checked> Auto</label>
      <label><input type="radio" name="strings" value="4"> 4 cordes</label>
      <label><input type="radio" name="strings" value="5"> 5 cordes</label>
    </fieldset>

    <label>
      <input type="checkbox" name="export_musescore" value="true" checked>
      Export MuseScore (.mscz ou .musicxml)
    </label>

    <button type="submit">Convertir</button>
  </form>

  <div id="result"></div>
</body>
</html>
```

- [ ] **Créer result.html**

```html
{% set status = job.status.value %}

<div id="result"
  {% if status in ('pending', 'running') %}
    hx-get="/status/{{ job.job_id }}"
    hx-trigger="every 2s"
    hx-swap="outerHTML"
  {% endif %}
>

{% if status == 'pending' or status == 'running' %}
  <p>⏳ Traitement en cours…</p>

{% elif status == 'awaiting_part' %}
  <p>⚠ Plusieurs parties basse détectées. Choisissez :</p>
  <form hx-post="/select-part/{{ job.job_id }}"
        hx-target="#result"
        hx-swap="outerHTML">
    <select name="part_name">
      {% for name in job.part_candidates %}
        <option value="{{ name }}">{{ name }}</option>
      {% endfor %}
    </select>
    <button type="submit">Confirmer</button>
  </form>

{% elif status == 'done' %}
  <p>✅ Conversion terminée !</p>
  <ul>
    {% if job.pdf_path %}
      <li><a href="/download/{{ job.job_id }}/tab.pdf">📄 Télécharger la tablature PDF</a></li>
    {% endif %}
    {% if job.score_path %}
      <li><a href="/download/{{ job.job_id }}/score">🎼 Télécharger le fichier éditable</a></li>
    {% endif %}
  </ul>

{% elif status == 'error' %}
  <p>❌ Erreur : {{ job.error }}</p>

{% endif %}
</div>
```

- [ ] **Créer style.css**

```css
body { font-family: sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }
h1 { font-size: 1.8rem; }
#drop-zone { border: 2px dashed #aaa; border-radius: 8px; padding: 2rem; text-align: center; margin-bottom: 1rem; }
#drop-zone label { cursor: pointer; display: block; }
#drop-zone input[type="file"] { display: none; }
fieldset { border: none; margin: 1rem 0; padding: 0; }
fieldset label { margin-right: 1rem; }
button { margin-top: 1rem; padding: 0.6rem 1.4rem; font-size: 1rem; cursor: pointer; }
#result { margin-top: 2rem; }
#result ul { padding-left: 1.2rem; }
#result a { color: #0066cc; }
```

- [ ] **Redémarrer et tester l'interface**

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Ouvrir http://localhost:8000. Vérifier que la page s'affiche correctement avec zone de dépôt et options.

- [ ] **Commit**

```bash
git add web/templates/ web/static/
git commit -m "feat: HTMX web UI with drag-and-drop and polling"
```

---

## Task 12 : Test d'intégration end-to-end

**Files:**
- Create: `tests/test_integration.py`

Ce test utilise les fichiers d'exemple réels et vérifie la chaîne complète pour MusicXML (sans OMR).

- [ ] **Écrire le test**

```python
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
    assert all(a.fret >= 0 for a in assigned if not a.is_rest)

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
```

- [ ] **Lancer les tests d'intégration**

```bash
pytest tests/test_integration.py -v -s
```

Expected: 2 passed. Si le test MIDI échoue sur `NoBassPartError`, c'est normal (MIDI n'a pas de noms de parts) — le test ajuste avec `part_name=parts[0]`.

- [ ] **Commit**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration tests MusicXML and MIDI"
```

---

## Task 13 : README + remote GitHub

**Files:**
- Create: `README.md`

- [ ] **Créer README.md**

````markdown
# PDF2BassTab

Convertit des partitions (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF.

## Prérequis

```bash
# Python 3.11+
pip install -r requirements.txt

# LilyPond
sudo apt install lilypond   # Linux
brew install lilypond       # macOS

# Java 17+ (pour Audiveris OMR sur PDF)
sudo apt install default-jre

# Audiveris JAR → placer dans tools/audiveris.jar
# https://github.com/Audiveris/audiveris/releases
```

## Lancer l'application

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Ouvrir http://localhost:8000

## Tests

```bash
pytest                          # tests rapides
pytest -m slow                  # tests complets (LilyPond, OMR)
```

## Formats supportés

| Format | Extension |
|--------|-----------|
| Partition PDF (OMR) | `.pdf` |
| MIDI | `.mid` `.midi` |
| MusicXML | `.musicxml` `.xml` |
| MusicXML compressé | `.mxl` |
| MuseScore | `.mscz` |
````

- [ ] **Ajouter le remote GitHub et pousser**

```bash
git remote add origin https://github.com/virgosfredianilorenzo-cyber/PDF2BassTab.git
git branch -M main
git push -u origin main
```

- [ ] **Vérifier sur GitHub** que tous les fichiers sont présents (hors `tmp/`, `tools/audiveris.jar`).

---

## Récapitulatif des commandes de test

```bash
# Tests unitaires rapides
pytest tests/ -v -k "not slow"

# Tests complets (LilyPond requis)
pytest tests/ -v

# Lancer le serveur
python -m uvicorn api.main:app --reload --port 8000
```
