from pathlib import Path
import music21
from processing.musescore_exporter import MuseScoreExporter


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
