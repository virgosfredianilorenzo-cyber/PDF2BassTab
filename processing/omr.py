import subprocess
from pathlib import Path


class OMRError(Exception):
    pass


class AudiverisOMR:
    # Java executable path (not in PATH)
    JAVA_PATH = Path("/run/host/usr/lib/jvm/java-21-openjdk-amd64/bin/java")

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
            str(self.JAVA_PATH), "-jar", str(self.jar),
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
