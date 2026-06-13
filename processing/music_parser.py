from pathlib import Path
import music21


class MusicParser:
    def parse(self, musicxml_path: Path) -> music21.stream.Score:
        return music21.converter.parse(str(musicxml_path))

    def list_parts(self, score: music21.stream.Score) -> list[str]:
        """Return part names (or IDs if names are absent)."""
        names = []
        for part in score.parts:
            name = str(part.partName or part.id or f"Part {len(names)+1}")
            names.append(name)
        return names
