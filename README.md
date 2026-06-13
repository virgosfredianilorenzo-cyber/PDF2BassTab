# PDF2BassTab

Convertit des partitions (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF, avec les noms des notes et les numéros de frettes.

---

## Installation pas à pas (Linux)

> Copiez-collez chaque commande dans un terminal. Après chaque étape, vérifiez que le message attendu s'affiche avant de continuer.

### Étape 1 — Récupérer le projet

```bash
cd ~/Documents          # ou le dossier de votre choix
git clone https://github.com/virgosfredianilorenzo-cyber/PDF2BassTab.git
cd PDF2BassTab
```

> **Résultat attendu :** un dossier `PDF2BassTab` est créé avec tous les fichiers du projet.

---

### Étape 2 — Créer l'environnement Python

Python est déjà installé sur la plupart des Linux. Cette étape crée un espace isolé pour les bibliothèques du projet.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Résultat attendu :** des dizaines de lignes s'affichent pendant l'installation, puis `Successfully installed ...`.  
> Votre terminal affiche désormais `(.venv)` au début de la ligne.

---

### Étape 3 — Installer LilyPond (génération des PDFs)

La version de LilyPond dans les dépôts Linux est trop ancienne. Il faut télécharger le binaire officiel :

```bash
cd ~
wget https://lilypond.org/download/binaries/linux-64/lilypond-2.24.4-linux-64.tar.gz
tar -xzf lilypond-2.24.4-linux-64.tar.gz
mkdir -p ~/.local/bin
ln -sf ~/lilypond-2.24.4/bin/lilypond ~/.local/bin/lilypond
```

Vérification :

```bash
lilypond --version
```

> **Résultat attendu :** `GNU LilyPond 2.24.4`  
> Si la commande n'est pas trouvée, fermez et rouvrez votre terminal, puis réessayez.

Retournez dans le dossier du projet :

```bash
cd -   # retour au dossier précédent
```

---

### Étape 4 — Installer Java (requis pour Audiveris)

Java est nécessaire uniquement si vous voulez convertir des fichiers PDF.

```bash
sudo apt update
sudo apt install default-jre
```

Vérification :

```bash
java -version
```

> **Résultat attendu :** `openjdk version "17..."` ou supérieur.

---

### Étape 5 — Installer Audiveris (conversion PDF → tablature)

Audiveris analyse les partitions PDF par reconnaissance optique (OMR).  
**Nécessaire uniquement pour les fichiers `.pdf`.**

```bash
wget https://github.com/Audiveris/audiveris/releases/download/5.10.2/Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo dpkg -i Audiveris-5.10.2-ubuntu22.04-x86_64.deb
sudo apt-get install -f
```

Vérification :

```bash
ls /opt/audiveris/bin/Audiveris
```

> **Résultat attendu :** `/opt/audiveris/bin/Audiveris`  
> L'application détecte automatiquement ce chemin — aucune configuration supplémentaire n'est nécessaire.  
> Le binaire n'est pas dans le PATH système, ce qui est normal.

---

### Étape 6 — Installer MuseScore 4 (conversion .mscz)

**Nécessaire uniquement pour les fichiers `.mscz`.**  
Si vous n'avez pas Flatpak, installez-le d'abord :

```bash
sudo apt install flatpak
sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

Puis installez MuseScore :

```bash
flatpak install flathub org.musescore.MuseScore
```

> **Résultat attendu :** MuseScore 4 s'installe (plusieurs centaines de Mo).  
> Tapez `y` pour confirmer si demandé.

> **Note :** MuseScore 3 (déjà présent sur certaines distributions) ne peut pas ouvrir les fichiers créés avec MuseScore 4. L'application détecte automatiquement la bonne version.

---

### Étape 7 — Lancer l'application

```bash
cd /chemin/vers/PDF2BassTab   # remplacez par votre chemin réel
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

> **Résultat attendu :**
> ```
> INFO:     Uvicorn running on http://127.0.0.1:8000
> INFO:     Application startup complete.
> ```

Ouvrez votre navigateur et allez sur **http://localhost:8000**

Glissez-déposez votre fichier, choisissez 4 ou 5 cordes, cliquez sur **Convertir** — le PDF de tablature se télécharge automatiquement.

---

### Récapitulatif — formats supportés

| Format | Extension | Prérequis supplémentaire |
|--------|-----------|--------------------------|
| Partition PDF (OMR) | `.pdf` | Java + Audiveris (étapes 4 et 5) |
| MIDI | `.mid` `.midi` | — |
| MusicXML | `.musicxml` `.xml` | — |
| MusicXML compressé | `.mxl` | — |
| MuseScore | `.mscz` | MuseScore 4 Flatpak (étape 6) |

Les formats MusicXML et MIDI fonctionnent sans aucun prérequis supplémentaire.

---

## Tests

```bash
source .venv/bin/activate
pytest                    # tests rapides
pytest -m slow            # tests complets (nécessite LilyPond et Audiveris)
```

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
   FretAssigner (algorithme de programmation dynamique)
        │
   LilyPondRenderer ──► tablature.pdf
   MuseScoreExporter ──► score.mscz (optionnel)
```
