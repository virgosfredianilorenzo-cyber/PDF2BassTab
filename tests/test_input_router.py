import shutil
import tempfile
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
