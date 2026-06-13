# PDF2BassTab

Convertit des partitions (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF.

## Prérequis

```bash
# Python 3.11+
pip install -r requirements.txt

# LilyPond
sudo apt install lilypond   # Linux
brew install lilypond       # macOS

# Java 17+ (pour Audiveris OMR sur PDF)
sudo apt install default-jre

# Audiveris JAR → placer dans tools/audiveris.jar
# https://github.com/Audiveris/audiveris/releases
```

## Lancer l'application

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Ouvrir http://localhost:8000

## Tests

```bash
python -m pytest                          # tests rapides
python -m pytest -m slow                  # tests complets (LilyPond, OMR)
```

## Formats supportés

| Format | Extension |
|--------|-----------|
| Partition PDF (OMR) | `.pdf` |
| MIDI | `.mid` `.midi` |
| MusicXML | `.musicxml` `.xml` |
| MusicXML compressé | `.mxl` |
| MuseScore | `.mscz` |

## Architecture

```
PDF/MIDI/MusicXML/MSCZ
        │
   InputRouter ──► Audiveris OMR (PDF only)
        │
   MusicXML (pivot)
        │
   BassExtractor (music21)
        │
   FretAssigner (DP algorithm)
        │
   LilyPondRenderer ──► tablature.pdf
   MuseScoreExporter ──► score.mscz (optional)
```
