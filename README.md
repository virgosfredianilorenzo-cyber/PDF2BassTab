# PDF2BassTab

Convertit des partitions (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF, avec les noms des notes et les numéros de frettes.

Interface web drag-and-drop — déposez votre fichier, récupérez votre tablature.

---

## Démarrage rapide — Docker

La façon la plus simple de lancer l'application sans installer les dépendances système manuellement.

**Prérequis :** [Docker](https://docs.docker.com/get-docker/) installé.

```bash
git clone https://github.com/virgosfredianilorenzo-cyber/PDF2BassTab.git
cd PDF2BassTab
docker compose up --build
```

Puis ouvrez **http://localhost:8000** dans votre navigateur.

> La première construction télécharge LilyPond et Audiveris (~400 Mo). Les suivantes sont instantanées.

---

## Installation manuelle (Linux)

> Copiez-collez chaque commande dans un terminal. Après chaque étape, vérifiez que le message attendu s'affiche avant de continuer.

### Étape 1 — Récupérer le projet

```bash
git clone https://github.com/virgosfredianilorenzo-cyber/PDF2BassTab.git
cd PDF2BassTab
```

### Étape 2 — Environnement Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Résultat attendu :** `Successfully installed ...` et `(.venv)` au début du terminal.

### Étape 3 — LilyPond 2.24 (génération des PDFs)

La version dans les dépôts Linux est trop ancienne — il faut le binaire officiel :

```bash
wget https://lilypond.org/download/binaries/linux-64/lilypond-2.24.4-linux-64.tar.gz
tar -xzf lilypond-2.24.4-linux-64.tar.gz
mkdir -p ~/.local/bin
ln -sf ~/lilypond-2.24.4/bin/lilypond ~/.local/bin/lilypond
lilypond --version   # doit afficher "GNU LilyPond 2.24.4"
```

### Étape 4 — Java (requis pour Audiveris / PDF uniquement)

```bash
sudo apt install default-jre
java -version   # doit afficher "openjdk version 17..." ou supérieur
```

### Étape 5 — Audiveris (PDF → MusicXML, optionnel)

```bash
wget https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo dpkg -i Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo apt-get install -f
ls /opt/audiveris/bin/Audiveris   # doit afficher le chemin
```

### Étape 6 — MuseScore 4 (.mscz uniquement, optionnel)

```bash
sudo apt install flatpak
sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.musescore.MuseScore
```

### Étape 7 — Lancer l'application

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Ouvrez **http://localhost:8000**, glissez votre fichier et cliquez sur **Convertir**.

---

## Formats supportés

| Format | Extension | Prérequis supplémentaire |
|--------|-----------|--------------------------|
| Partition PDF (OMR) | `.pdf` | Java + Audiveris (étapes 4–5) |
| MIDI | `.mid` `.midi` | — |
| MusicXML | `.musicxml` `.xml` `.mxl` | — |
| MuseScore | `.mscz` | MuseScore 4 Flatpak (étape 6) |

---

## Architecture

```
PDF/MIDI/MusicXML/MSCZ
        │
   InputRouter ──► Audiveris OMR (PDF uniquement)
        │
   MusicXML (format pivot)
        │
   BassExtractor (music21)
        │
   FretAssigner (programmation dynamique)
        │
   LilyPondRenderer ──► tablature.pdf
   MuseScoreExporter ──► score.mscz (optionnel)
```

**Stack :** Python 3.11 · FastAPI · HTMX · music21 · LilyPond 2.24 · Audiveris 5.10

---

## Tests

```bash
source .venv/bin/activate
pytest                  # tests unitaires rapides
pytest -m slow          # tests complets (nécessite LilyPond et Audiveris)
```

---

## Déploiement en production

Pour exposer l'application sur internet, utilisez Docker avec un reverse proxy HTTPS :

```bash
# Sur votre VPS
git clone https://github.com/virgosfredianilorenzo-cyber/PDF2BassTab.git
cd PDF2BassTab
docker compose up -d
# Puis configurez Caddy ou Nginx devant le port 8000
```
