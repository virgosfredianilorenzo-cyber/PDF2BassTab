# PDF2BassTab — Design Spec

**Date:** 2026-06-13  
**Status:** Approuvé

---

## Objectif

Convertir automatiquement des partitions musicales (PDF, MIDI, MusicXML, MSCZ) en tablatures basse 4 ou 5 cordes au format PDF, avec noms des notes. Accessible via une interface web légère (drag-and-drop).

---

## Formats d'entrée supportés

| Format | Extension | Traitement |
|--------|-----------|------------|
| Partition PDF (notation standard) | `.pdf` | Audiveris OMR → MusicXML |
| MIDI | `.mid` / `.midi` | music21 → MusicXML |
| MusicXML | `.musicxml` | pass-through |
| MusicXML compressé | `.mxl` | unzip → MusicXML |
| MuseScore | `.mscz` | unzip → MusicXML |

Le PDF peut contenir :
- **Une seule partie basse** → extraction directe
- **Une partition complète** (orchestre, big band…) → détection automatique de la partie basse par nom de part ; si ambiguïté, l'utilisateur choisit via l'UI

---

## Formats de sortie

- **Tablature PDF** (obligatoire) — rendu LilyPond, basse 4 ou 5 cordes, numéros de frettes + noms des notes
- **MuseScore .mscz** (optionnel) — pour correction manuelle avant re-export

---

## Architecture & flux de données

```
Fichier uploadé
      │
 InputRouter          détecte l'extension, dispatch
      │
      ├── PDF   → omr.py (Audiveris subprocess)     ┐
      ├── MSCZ  → unzip → extraire .mxl / .xml      │
      ├── MXL   → unzip → MusicXML                  ├─→ MusicXML (pivot)
      ├── MIDI  → music21 write MusicXML            │
      └── XML   → pass-through                      ┘
                         │
                  BassExtractor        music21 : identifie partie basse
                         │             • par nom (bass, basse, tuba, contrebasse…)
                         │             • si ambiguïté → UI de sélection + rejeu
                         │
                  FretAssigner         DP : assigne (corde, frette) à chaque note
                         │             • détection auto 4/5 cordes
                         │             • --strings 4|5 pour forcer
                         │
              ┌──────────┴──────────┐
         LilyPondRenderer     MusicScoreExporter
              │                    │
           tab.pdf             score.mscz
```

---

## Structure du projet

```
PDF2BassTab/
├── api/
│   ├── main.py               # FastAPI app : routes upload/status/download
│   └── pipeline.py           # Orchestre les étapes dans l'ordre
├── processing/
│   ├── input_router.py       # Détecte format → retourne MusicXML path
│   ├── omr.py                # Wrapper Audiveris (subprocess Java)
│   ├── music_parser.py       # Wrapper music21 (parse MusicXML)
│   ├── bass_extractor.py     # Identifie et extrait la partie basse
│   ├── fret_assigner.py      # Algorithme DP de placement de frettes
│   ├── lilypond_renderer.py  # Génère .ly → appel lilypond → PDF
│   └── musescore_exporter.py # Génère .mscz (optionnel)
├── web/
│   ├── templates/
│   │   ├── index.html        # Page principale HTMX
│   │   └── result.html       # Fragment HTMX résultat
│   └── static/
│       └── style.css
├── Exemples/                 # Fichiers d'exemple
├── tmp/                      # Jobs temporaires (gitignored), 1 dossier/UUID
├── requirements.txt
└── README.md
```

---

## Algorithme FretAssigner (détail)

### Détection 4/5 cordes

- **4 cordes** : E2 – A2 – D3 – G3 (accordage standard)
- **5 cordes** : B1 – E2 – A2 – D3 – G3
- Si une note < E2 est détectée dans la partition → 5 cordes suggéré automatiquement
- Paramètre `strings: int | None` (None = auto)

### Placement par programmation dynamique

```
candidats(note) = [(corde, frette) pour toute combinaison valide, frette ∈ [0, 12]]

coût(pos_i-1 → pos_i) =
    |position_main[i] - position_main[i-1]|   # saut de main
  + pénalité_corde_extrême                     # évite de rester sur corde 1

position_main = frette - (corde_index * 0.5)  # approximation position du poignet

DP minimise le coût total sur l'ensemble de la séquence
```

La position main est une heuristique permettant de comparer des positions sur des cordes différentes. Les sauts > 5 cases reçoivent une pénalité supplémentaire.

---

## Interface web

### Endpoints FastAPI

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Page principale |
| `POST` | `/upload` | Upload fichier + options → `{job_id}` |
| `GET` | `/status/{job_id}` | Fragment HTMX pooling (2s) |
| `GET` | `/download/{job_id}/{filename}` | Téléchargement PDF ou MSCZ |

### Options utilisateur

- **Cordes** : Auto (défaut) / 4 / 5
- **Export MuseScore** : checkbox (activé par défaut) — si MuseScore CLI absent, fallback vers MusicXML téléchargeable

### Gestion de la sélection de partie

Si la partition contient plusieurs parties basse candidates, `/status/{job_id}` retourne un fragment HTML avec un sélecteur. L'utilisateur choisit, le pipeline reprend depuis `BassExtractor` avec la partie forcée.

---

## Dépendances externes

| Outil | Usage | Installation |
|-------|-------|--------------|
| **Audiveris** | OMR PDF → MusicXML | JAR Java (subprocess) |
| **Java 17+** | Runtime Audiveris | `apt install default-jre` |
| **LilyPond** | Rendu tablature PDF | `apt install lilypond` |
| **music21** | Parse/traitement MusicXML & MIDI | `pip install music21` |
| **MuseScore CLI** (optionnel) | Conversion MusicXML → .mscz | AppImage ou `apt install musescore3` |
| **FastAPI + uvicorn** | Serveur web | `pip install fastapi uvicorn` |
| **python-multipart** | Upload fichiers | `pip install python-multipart` |
| **Jinja2** | Templates HTML | inclus avec FastAPI |

---

## Gestion des erreurs

- **OMR échoue** : message utilisateur clair, suggestion de fournir un MusicXML directement
- **Aucune partie basse trouvée** : liste toutes les parties disponibles pour choix manuel
- **Note hors portée** (> frette 12) : warning dans le résultat, note marquée en rouge dans le LilyPond
- **Fichier corrompu** : HTTP 422 avec message explicite

---

## Ce qui est hors scope

- Reconnaissance de fichiers audio (MP3, WAV)
- Édition en ligne de la tablature
- Comptes utilisateurs / persistance des jobs
- Transposition automatique
