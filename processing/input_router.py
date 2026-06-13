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
            if src.resolve() != dest.resolve():
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
            xml_names = [
                n for n in z.namelist()
                if n.endswith(".xml") and not n.startswith("__")
                and not n.startswith("META-INF")
            ]
            if not xml_names:
                raise UnsupportedFormatError("No .xml found inside .mxl archive")
            # Prefer root-level XML; fall back to the first found
            root_names = [n for n in xml_names if "/" not in n]
            chosen = root_names[0] if root_names else xml_names[0]
            z.extract(chosen, self.tmp_dir)
            return self.tmp_dir / chosen

    def _convert_midi(self, src: Path) -> Path:
        """Convert MIDI to MusicXML using music21.

        Percussion/unpitched notes are stripped before export because
        music21's MusicXML exporter raises MusicXMLExportException when
        the instrument registry is inconsistent for Unpitched notes
        (common in multi-instrument MIDI files, e.g. MIDI channel 10).
        """
        import copy

        score = music21.converter.parse(str(src))
        score = copy.deepcopy(score)

        for part in score.parts:
            for measure in part.getElementsByClass(music21.stream.Measure):
                # Remove from voices inside the measure
                for voice in measure.getElementsByClass(music21.stream.Voice):
                    for el in list(voice.getElementsByClass(music21.note.Unpitched)):
                        voice.remove(el)
                # Remove directly from the measure (not inside a voice)
                for el in list(measure.getElementsByClass(music21.note.Unpitched)):
                    measure.remove(el)

        dest = self.tmp_dir / (src.stem + ".musicxml")
        score.write("musicxml", fp=str(dest))
        return dest

    def _convert_mscz(self, src: Path) -> Path:
        """Convert .mscz to MusicXML via MuseScore CLI."""
        import os
        import subprocess

        mscore = (
            shutil.which("mscore")
            or shutil.which("musescore")
            or shutil.which("mscore3")
            or shutil.which("musescore3")
        )
        if not mscore:
            raise UnsupportedFormatError(
                ".mscz requires MuseScore CLI. Install MuseScore and ensure "
                "'mscore' or 'musescore' is in PATH."
            )
        dest = (self.tmp_dir / (src.stem + ".musicxml")).resolve()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        result = subprocess.run(
            [mscore, "-o", str(dest), str(src.resolve())],
            capture_output=True,
            env=env,
        )
        if result.returncode != 0:
            raise UnsupportedFormatError(
                f"MuseScore conversion failed (exit {result.returncode}):\n"
                + result.stderr.decode(errors="replace")
            )
        return dest
