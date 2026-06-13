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
