# PDF2BassTab

Convertit des partitions (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF.

## Prérequis

### 1. Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. LilyPond 2.24+

LilyPond génère les PDFs de tablature. La version des dépôts Debian/Ubuntu est trop ancienne — télécharger le binaire officiel :

```bash
# Télécharger LilyPond 2.24.4
wget https://lilypond.org/download/binaries/linux-64/lilypond-2.24.4-linux-64.tar.gz
tar -xzf lilypond-2.24.4-linux-64.tar.gz
mkdir -p ~/.local/bin
ln -sf "$(pwd)/lilypond-2.24.4/bin/lilypond" ~/.local/bin/lilypond

# Vérifier
lilypond --version
```

### 3. Java 17+ (requis par Audiveris pour les PDF)

```bash
sudo apt install default-jre

# Vérifier
java -version
```

### 4. Audiveris 5.10.2 (conversion PDF → MusicXML)

Nécessaire uniquement pour uploader des fichiers `.pdf`.

```bash
wget https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo dpkg -i Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo apt-get install -f   # résout les dépendances manquantes si besoin

# Vérifier
audiveris --version
```

### 5. MuseScore 4 (conversion .mscz)

Nécessaire uniquement pour uploader des fichiers `.mscz`.

```bash
flatpak install flathub org.musescore.MuseScore

# Vérifier
flatpak run org.musescore.MuseScore --version
```

> **Note :** MuseScore 3 (`mscore3`) ne peut pas ouvrir les fichiers créés avec MuseScore 4.
> Si vous n'installez pas MuseScore, exportez vos fichiers en MusicXML depuis l'interface graphique avant d'uploader.

---

## Lancer l'application

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Ouvrir http://localhost:8000

## Tests

```bash
source .venv/bin/activate
pytest                          # tests rapides
pytest -m slow                  # tests complets (LilyPond, OMR)
```

## Formats supportés

| Format | Extension | Prérequis supplémentaire |
|--------|-----------|--------------------------|
| Partition PDF (OMR) | `.pdf` | Java + Audiveris |
| MIDI | `.mid` `.midi` | — |
| MusicXML | `.musicxml` `.xml` | — |
| MusicXML compressé | `.mxl` | — |
| MuseScore | `.mscz` | MuseScore 4 (Flatpak) |

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
