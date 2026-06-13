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
