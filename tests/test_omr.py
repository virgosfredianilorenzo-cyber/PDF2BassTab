from pathlib import Path
import pytest
from processing.omr import AudiverisOMR, OMRError

TOOLS = Path("tools")
EXAMPLES = Path("Exemples")


def test_omr_jar_missing_raises():
    """AudiverisOMR raises OMRError if JAR is not found."""
    with pytest.raises(OMRError, match="not found"):
        AudiverisOMR(jar_path=Path("tools/nonexistent.jar"), tmp_dir=Path("/tmp"))


@pytest.mark.slow
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
