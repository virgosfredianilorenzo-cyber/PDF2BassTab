import shutil
import subprocess
from pathlib import Path

_FALLBACK_JAVA_PATHS = [
    "/usr/bin/java",
    "/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
    "/run/host/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
]


def _find_java() -> str:
    found = shutil.which("java")
    if found:
        return found
    for p in _FALLBACK_JAVA_PATHS:
        if Path(p).exists():
            return p
    raise OMRError(
        "Java introuvable. Installez Java 17+ : sudo apt install default-jre"
    )


def _find_audiveris_jar(tools_dir: Path) -> Path:
    """Locate Audiveris JAR inside tools_dir.

    Supports two layouts:
      tools/audiveris.jar                   (single fat JAR)
      tools/audiveris/lib/Audiveris.jar     (extracted release zip)
    """
    single = tools_dir / "audiveris.jar"
    if single.exists():
        return single
    # Extracted release: tools/audiveris*/lib/Audiveris.jar
    for candidate in sorted(tools_dir.glob("audiveris*/lib/Audiveris.jar")):
        return candidate
    raise OMRError(
        "Audiveris introuvable. Téléchargez la dernière release depuis\n"
        "https://github.com/Audiveris/audiveris/releases\n"
        "et décompressez l'archive dans tools/ :\n"
        "  cd tools && unzip Audiveris-*.zip\n"
        "Résultat attendu : tools/Audiveris-X.Y.Z/lib/Audiveris.jar"
    )


class OMRError(Exception):
    pass


class AudiverisOMR:
    def __init__(self, jar_path: Path, tmp_dir: Path):
        self.java = _find_java()
        tools_dir = Path(jar_path).parent
        self.jar = _find_audiveris_jar(tools_dir)
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def run(self, pdf_path: Path) -> Path:
        """Run Audiveris OMR on a PDF. Returns path to MusicXML output."""
        pdf_path = Path(pdf_path).resolve()
        out_dir = (self.tmp_dir / "audiveris_out").resolve()
        out_dir.mkdir(exist_ok=True)

        cmd = [
            self.java, "-jar", str(self.jar),
            "-batch", "-export",
            "-output", str(out_dir),
            str(pdf_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise OMRError(f"Audiveris failed:\n{proc.stderr}")

        mxl_files = list(out_dir.glob("**/*.mxl"))
        xml_files = list(out_dir.glob("**/*.xml"))
        candidates = mxl_files or xml_files
        if not candidates:
            raise OMRError("Audiveris n'a produit aucun fichier de sortie")

        return candidates[0]
