import shutil
import subprocess
from pathlib import Path

_INSTALL_HELP = (
    "Audiveris introuvable. Installez-le avec :\n"
    "  wget https://github.com/Audiveris/audiveris/releases/download/5.10.2/"
    "Audiveris-5.10.2-ubuntu22.04-x86_64.deb\n"
    "  sudo dpkg -i Audiveris-5.10.2-ubuntu22.04-x86_64.deb\n"
    "  sudo apt-get install -f   # résout les dépendances si nécessaire"
)

_FALLBACK_JAVA_PATHS = [
    "/usr/bin/java",
    "/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
    "/run/host/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
]

# JAR locations checked when the `audiveris` command is not in PATH
_JAR_SEARCH_PATHS = [
    Path("/usr/share/audiveris/lib/Audiveris.jar"),
    Path("/opt/audiveris/lib/Audiveris.jar"),
]


class OMRError(Exception):
    pass


def _find_audiveris_cmd(tools_dir: Path) -> list[str]:
    """Return a command list to invoke Audiveris CLI.

    Search order:
    1. `audiveris` in PATH (installed via .deb)
    2. Known system JAR locations
    3. tools/ directory (manual JAR placement)
    """
    # 1. Command in PATH
    found = shutil.which("audiveris")
    if found:
        return [found]

    java = shutil.which("java")
    if not java:
        for p in _FALLBACK_JAVA_PATHS:
            if Path(p).exists():
                java = p
                break
    if not java:
        raise OMRError(
            "Java introuvable. Installez Java 17+ :\n  sudo apt install default-jre"
        )

    # 2. Known system paths
    for jar in _JAR_SEARCH_PATHS:
        if jar.exists():
            return [java, "-jar", str(jar)]

    # 3. tools/ directory: tools/audiveris.jar or tools/Audiveris-*/lib/Audiveris.jar
    single = tools_dir / "audiveris.jar"
    if single.exists():
        return [java, "-jar", str(single)]
    for candidate in sorted(tools_dir.glob("Audiveris*/lib/Audiveris.jar")):
        return [java, "-jar", str(candidate)]

    raise OMRError(_INSTALL_HELP)


class AudiverisOMR:
    def __init__(self, jar_path: Path, tmp_dir: Path):
        tools_dir = Path(jar_path).parent
        self.cmd = _find_audiveris_cmd(tools_dir)
        self.tmp_dir = Path(tmp_dir)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def run(self, pdf_path: Path) -> Path:
        """Run Audiveris OMR on a PDF. Returns path to MusicXML output."""
        pdf_path = Path(pdf_path).resolve()
        out_dir = (self.tmp_dir / "audiveris_out").resolve()
        out_dir.mkdir(exist_ok=True)

        proc = subprocess.run(
            self.cmd + ["-batch", "-export", "-output", str(out_dir), str(pdf_path)],
            capture_output=True, text=True, timeout=300,
        )
        if proc.returncode != 0:
            raise OMRError(f"Audiveris a échoué :\n{proc.stderr}")

        mxl_files = list(out_dir.glob("**/*.mxl"))
        xml_files = list(out_dir.glob("**/*.xml"))
        candidates = mxl_files or xml_files
        if not candidates:
            raise OMRError("Audiveris n'a produit aucun fichier de sortie")

        return candidates[0]
