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

        mscore_cmd = self._find_mscore()
        if not mscore_cmd:
            raise UnsupportedFormatError(
                "Conversion .mscz impossible : MuseScore n'est pas installé. "
                "Installez MuseScore 4 (flatpak install flathub org.musescore.MuseScore) "
                "ou exportez votre fichier en MusicXML depuis MuseScore avant d'uploader."
            )
        dest = (self.tmp_dir / (src.stem + ".musicxml")).resolve()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        cmd = mscore_cmd + ["-o", str(dest), str(src.resolve())]
        result = subprocess.run(cmd, capture_output=True, env=env)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            # Detect version incompatibility (file saved with newer MuseScore)
            if "version" in stderr.lower() and ("récente" in stderr or "newer" in stderr.lower()):
                raise UnsupportedFormatError(
                    "Ce fichier .mscz a été créé avec MuseScore 4 mais votre système "
                    "n'a que MuseScore 3. Solutions :\n"
                    "• Installez MuseScore 4 : flatpak install flathub org.musescore.MuseScore\n"
                    "• Ou ouvrez le fichier dans MuseScore 4 et exportez-le en MusicXML (.musicxml)"
                )
            raise UnsupportedFormatError(
                f"Échec conversion MuseScore (code {result.returncode}) :\n{stderr}"
            )
        return dest

    @staticmethod
    def _find_mscore() -> list[str] | None:
        """Return the command prefix for the best available MuseScore, or None."""
        import subprocess

        # Prefer MuseScore 4 (supports newer .mscz files)
        for name in ("mscore4", "musescore4", "mscore", "musescore", "mscore3", "musescore3"):
            found = shutil.which(name)
            if found:
                return [found]

        # Try MuseScore 4 via Flatpak
        flatpak = shutil.which("flatpak")
        if flatpak:
            check = subprocess.run(
                [flatpak, "info", "org.musescore.MuseScore"],
                capture_output=True,
            )
            if check.returncode == 0:
                return [flatpak, "run", "org.musescore.MuseScore"]

        return None
