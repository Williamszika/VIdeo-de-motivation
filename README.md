# MZ STUDIO — vidéos de motivation · **Mr ZIKA**

Chaîne de production complète pour fabriquer des vidéos de motivation
**verticales 1080×1920, 5 minutes, prêtes pour TikTok**, avec étalonnage
cinéma, grain argentique, halo lumineux, sous-titres animés et la signature
**Mr ZIKA** en or animé.

Tu peux aussi lui donner **une conférence d'une heure** : il l'écoute, la
découpe en thèmes, fabrique les images de chaque ambiance, et ressort **une
série de vidéos de 5 minutes**, une par sujet.

Tout tourne avec **ffmpeg** et **Python**. Pas d'abonnement, pas de logiciel
propriétaire, pas de filigrane imposé. Les effets reproduisent ce que tu
ferais à la main dans DaVinci Resolve (Color Warper, Glow, Film Grain) et
After Effects (Light Sweep, Scale Pop, Outer Glow).

---

## 1. Installation — une seule fois

```bash
./install.sh
```

Installe ffmpeg, yt-dlp, Pillow, NumPy et les 4 polices d'affichage
(licence OFL, utilisables commercialement). Fonctionne sur Ubuntu/Debian,
Fedora, Arch, macOS (Homebrew) et Termux (Android).

Pour vérifier à tout moment :

```bash
./mz doctor
```

---

## 2. Les commandes

### A. Une vidéo, tu sais déjà ce que tu veux

| Commande | Ce qu'elle fait |
|---|---|
| `./mz init` | Prépare les dossiers du projet |
| `./mz audio <url ou fichier>` | Récupère la voix, la nettoie, la calibre |
| `./mz fonds` | Fabrique des images de fond cinématographiques |
| `./mz brand` | Fabrique la signature **Mr ZIKA** et ses animations |
| `./mz build` | Assemble la vidéo finale |

### B. Une longue vidéo à découper en série

| Commande | Ce qu'elle fait |
|---|---|
| `./mz ecoute <fichier>` | Transcrit tout, mot par mot (Whisper) |
| `./mz themes` | Propose un découpage en sujets |
| *(tu corriges `projet/themes.json`)* | Titres, bornes, ambiances |
| `./mz images` | Génère les images IA de chaque thème |
| `./mz decouper` | Taille chaque thème en parties de 5 minutes |
| `./mz serie` | Produit toutes les vidéos d'un coup |

Détail complet : **[docs/04-SERIE.md](docs/04-SERIE.md)** ·
images IA : **[docs/05-IMAGES-IA.md](docs/05-IMAGES-IA.md)**

### Outils

| Commande | Ce qu'elle fait |
|---|---|
| `./mz analyser <video>` | Repère les passages nets d'un rush |
| `./mz montage -i <video>` | Monte un rush court : recadre, étalonne, signe |
| `./mz plans` | Vérifie tes images / clips et te dit ce qui manque |
| `./mz looks` | Liste les étalonnages |
| `./mz ambiances` | Liste les ambiances de fond |
| `./mz demo` | Vidéo de démonstration, sans rien télécharger |
| `./mz doctor` | Vérifie l'installation |

Chaque commande accepte `-h` pour son aide détaillée.

---

## 3. Faire ta première vidéo

### Étape 1 — préparer le projet

```bash
./mz init
```

### Étape 2 — la voix

```bash
./mz audio "https://www.youtube.com/watch?v=XXXXXXXXXXX" -d 00:01:12 -t 300
```

- `-d 00:01:12` → commence à 1 min 12 s (saute l'intro de la vidéo source)
- `-t 300` → garde 5 minutes
- `-v 3` → nettoyage renforcé si la source est bruyante

Ce que fait la commande, dans l'ordre : téléchargement de la piste audio,
coupe, coupe-bas anti-grondement, réduction de bruit, égalisation
(présence à 3 kHz pour l'intelligibilité, air à 9 kHz), compression, puis
**calibration du volume en deux passes à −14 LUFS** — la norme des
plateformes. C'est ce dernier point qui fait qu'une vidéo sonne « pro » et
non « amateur ».

Résultat : `projet/02-audio/voix.wav`

### Étape 3 — les images

Deux possibilités, et tu peux les mélanger.

**Les faire générer par une IA**, à partir du sujet et de l'ambiance de
chaque thème :

```bash
export FAL_KEY="ta-cle"      # ou REPLICATE_API_TOKEN, OPENAI_API_KEY…
./mz images -T               # une image, pour vérifier la clé
./mz images -n 16
```

Environ 0,04 $ l'image. Sans clé, ou avec OpenMontage, voir
**[docs/05-IMAGES-IA.md](docs/05-IMAGES-IA.md)**.

**Ou les faire calculer par le studio**, gratuitement et sans réseau :

```bash
./mz fonds -a braise -n 20 -r 4k
```

Sept ambiances (`./mz ambiances`) : ciels volumétriques, brume en couches,
rayons de lumière, crêtes de montagne, villes, silhouettes, poussière dans la
lumière. Tout est calculé — donc **original, sans aucun droit à vérifier**, et
disponible jusqu'en 4320×7680. Ce ne sont pas des photos : c'est de l'image
cinématographique abstraite, et ça tient très bien derrière du texte.

**Ou déposer les tiennes** : 15 à 25 fichiers dans `projet/03-broll/`
(JPG, PNG, MP4, MOV…).

**Comment les obtenir et comment filmer les tiens :
→ [docs/01-GUIDE-TOURNAGE.md](docs/01-GUIDE-TOURNAGE.md)**

Puis contrôle :

```bash
./mz plans
```

La commande te dit la définition de chaque fichier, t'avertit si un plan
est trop petit pour du vertical, et calcule combien de minutes tu couvres
avant de reboucler.

### Étape 4 — le texte à l'écran

Écris tes phrases dans `projet/script.txt`, une idée par ligne.
Un mot **entre astérisques** s'affiche en doré :

```
Personne ne viendra te sauver.
C'est *toi* qui décides, maintenant.
La *discipline* pèse des grammes. Le regret pèse des tonnes.
```

Le calage se fait tout seul : la détection des silences repère où tu
parles et distribue les groupes de mots sur la parole réelle.

Tu as déjà des sous-titres Whisper ou YouTube ? Passe-les en `.srt` :

```bash
python3 tools/make_captions.py --srt mes-soustitres.srt --out projet/.cache/soustitres.ass
```

### Étape 5 — ta signature

```bash
./mz brand
```

Fabrique le logo **Mr ZIKA** en or métallique (dégradé, biseau, halo,
ombre portée), sa révélation d'intro avec balayage de lumière, la carte de
fin et le filigrane permanent.

Pour changer le nom ou la couleur :

```bash
./mz brand -n ZIKA -p "Mr" -c or        # or · argent · feu · glace · blanc
./mz brand -a "ABONNE-TOI, ON MONTE"    # phrase de fin
```

### Étape 6 — l'assemblage

```bash
./mz build
```

Ou avec un caractère plus affirmé :

```bash
./mz build -l fire -x fort -T flash -p 4.5
```

Résultat : `projet/04-rendu/MrZIKA_AAAAMMJJ-HHMM.mp4`

---

## 4. Réglages de `mz build`

| Option | Rôle | Valeurs |
|---|---|---|
| `-l` | étalonnage | `orange_teal` `ice` `fire` `gold` `noir` `cyber` `raw` |
| `-x` | texture (grain, vignette) | `aucun` `doux` `normal` `fort` |
| `-T` | transition entre plans | `coupe` `flash` `noir` `fondu` |
| `-p` | durée d'un plan en secondes | `4` nerveux · `6` équilibré · `9` contemplatif |
| `-d` | durée totale | `300` (5 min) ou `auto` |
| `-f` | taille des sous-titres | `112` par défaut |
| `-w` | mots par groupe | `1` frappé · `3` équilibré · `5` posé |
| `-m` | musique de fond | chemin du fichier |
| `-v` | volume de la musique | `-19` dB par défaut |
| `-k 0` | enlève le filigrane permanent | |
| `-N` | sans sous-titres | |
| `-I` | sans intro ni carte de fin | |
| `-R` | refait tous les plans (ignore le cache) | |

Voir tous les rendus disponibles :

```bash
./mz looks
```

Détail de chaque effet : **[docs/02-EFFETS.md](docs/02-EFFETS.md)**

---

## 5. Musique de fond

Dépose un fichier nommé `musique.mp3` (ou `.wav`, `.m4a`) dans
`projet/02-audio/`. Il est détecté automatiquement.

La musique **baisse toute seule dès que la voix parle** (compression
sidechain, comme en radio) et remonte dans les silences. Tu n'as rien à
automatiser à la main.

---

## 6. Essayer sans rien télécharger

```bash
./mz demo
./mz build -b projet-demo/03-broll -a projet-demo/02-audio/voix.wav \
           -s projet-demo/script.txt -d 30 -p 5
```

Fabrique 12 plans de synthèse et une voix de test, puis monte une vidéo de
30 secondes. Utile pour comparer les étalonnages avant d'attaquer un vrai
projet.

---

## 7. Temps de rendu

Sur 4 cœurs, pour une vidéo de 5 minutes :

| Étape | Durée approximative |
|---|---|
| `mz audio` | 1 à 3 min (selon le téléchargement) |
| `mz brand` | 1 à 2 min (une seule fois) |
| `mz build` — les plans | 6 à 10 min (en parallèle, mis en cache) |
| `mz build` — export final | 9 à 12 min |

Les plans sont mis en cache : si tu changes seulement les sous-titres ou
la musique, le second `mz build` ne refait que l'export. Utilise `-R`
quand tu changes l'étalonnage ou les images.

Pour un aperçu rapide pendant les essais : `-d 30 -q 26`.

---

## 8. Publication

Format, titres, hashtags, rythme de publication :
**[docs/03-TIKTOK.md](docs/03-TIKTOK.md)**

Produire une série entière depuis une longue vidéo :
**[docs/04-SERIE.md](docs/04-SERIE.md)**

Générer les images par IA :
**[docs/05-IMAGES-IA.md](docs/05-IMAGES-IA.md)**

Monter un rush court filmé au téléphone :
**[docs/06-MONTAGE.md](docs/06-MONTAGE.md)**

---

## 9. Droits sur les vidéos sources

Extraire l'audio d'une vidéo YouTube ne te donne pas le droit de le
republier. Avant de publier, assure-toi d'être dans un de ces cas :

- c'est **ta propre voix** (le plus sûr, et le plus rentable à terme) ;
- l'auteur t'a **donné son accord**, ou sa licence l'autorise
  (Creative Commons, domaine public) ;
- tu utilises un discours **libre de droits**.

TikTok retire les vidéos signalées et sanctionne les comptes récidivistes :
un compte construit sur la voix d'autrui reste fragile. Le studio marche
exactement pareil avec ta voix enregistrée au téléphone — et c'est ce qui
fera la différence sur la durée.

---

## 10. Organisation des fichiers

```
mz                    la commande principale
install.sh            installation
lib/
  common.sh           réglages communs, sondes média, polices
  grades.sh           étalonnages et effets (le cœur du rendu)
bin/
  mz-audio.sh         extraction + mastering de la voix
  mz-ecoute.sh        transcription Whisper mot à mot
  mz-fonds.sh         génération des images de fond
  mz-brand.sh         signature Mr ZIKA et ses animations
  mz-build.sh         assemblage d'une vidéo
  mz-serie.sh         production de toute une série
bin/
  mz-images.sh        images IA par thème
  mz-montage.sh       montage d'un rush court
tools/
  make_signature.py   logo or métallique (Pillow)
  make_backdrop.py    fonds cinématographiques jusqu'en 8K
  analyser.py         netteté d'un rush, proposition de montage
  make_prompts.py     rédaction des prompts par thème
  generer_images.py   génération IA (fal · Replicate · OpenAI · Stability · ComfyUI)
  make_captions.py    sous-titres animés .ass
  transcrire.py       Whisper, horodatage mot à mot
  themes.py           détection et contrôle des thèmes
  decouper.py         découpe en parties de 5 minutes
  make_demo.py        plans de démonstration
assets/
  fonts/              Anton, Bebas Neue, Oswald, Archivo (OFL)
  brand/              logo et animations générés
projet/
  01-source/          vidéos sources
  02-audio/           voix.wav, musique.*, transcription.*
  03-broll/           images et clips (un dossier par thème en mode série)
  04-rendu/           les vidéos finies
  parties/            sous-titres découpés + plan.tsv
  themes.json         le découpage en sujets
  script.txt          le texte affiché à l'écran
docs/                 les guides
```
