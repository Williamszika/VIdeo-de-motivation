# Une longue vidéo → une série de vidéos de 5 minutes

Tu m'envoies une conférence, un sermon, un podcast, une interview. Le studio
l'écoute, la découpe en sujets, et produit une vidéo TikTok par sujet — avec
des images fabriquées pour chaque ambiance et des sous-titres calés au mot.

---

## Le principe

Une vidéo de 40 minutes contient rarement un seul message. Elle en contient
cinq ou six, séparés par des transitions du type « bon, deuxième chose »,
« maintenant je voudrais vous parler de… ». Chacun de ces blocs est une vidéo
à lui tout seul.

Un thème long donne **plusieurs vidéos de 5 minutes**, découpées sur des
silences pour ne jamais couper une phrase en deux.

---

## Le déroulé complet

```bash
./mz ecoute ma-conference.mp4     # 1. transcrire
./mz themes                       # 2. proposer un découpage
#                                   3. TU CORRIGES projet/themes.json
./mz decouper                     # 4. tailler en parties de 5 min
./mz serie                        # 5. tout produire
```

---

## 1. `mz ecoute` — la transcription

```bash
./mz ecoute ma-conference.mp4
```

Whisper transcrit avec un horodatage **mot par mot**. C'est ce qui permet
d'avoir des sous-titres parfaitement synchronisés, sans réglage manuel.

| Modèle | Vitesse | Quand |
|---|---|---|
| `small` | ~2× le temps réel | Brouillon rapide |
| `large-v3-turbo` | ~2× le temps réel | **Par défaut.** Meilleure qualité |
| `large-v3` | ~0,7× le temps réel | Son difficile, accent marqué |

```bash
./mz ecoute ma-video.mp4 -m large-v3      # qualité maximale
./mz ecoute ma-video.mp4 -l auto          # laisser détecter la langue
```

Une conférence d'une heure prend environ 30 minutes. Le premier lancement
télécharge le modèle (~1,5 Go).

**Trois fichiers en sortie :**

| Fichier | À quoi il sert |
|---|---|
| `transcription.json` | Lu par les outils. Ne le modifie pas |
| `transcription.srt` | Sous-titres standard |
| `transcription.txt` | **À relire.** Le texte minuté, ligne par ligne |

---

## 2. `mz themes` — la proposition de découpage

```bash
./mz themes
```

Le studio compare le vocabulaire de deux fenêtres qui se suivent. Quand il
change franchement, il pose une frontière. Puis il sort les mots les plus
fréquents de chaque bloc.

```
01-a-nommer  00:00 → 12:14  (12.2 min, 3 vidéos de 5 min)
  mots frequents : discipline, habitude, matin, repetition
02-a-nommer  12:14 → 21:03  (8.8 min, 2 vidéos de 5 min)
  mots frequents : peur, echec, tenter, regard
```

**Cette méthode suit le vocabulaire, pas le sens.** Elle place bien les
frontières nettes et se trompe sur les transitions douces. C'est un point de
départ, pas un résultat.

---

## 3. Tu corriges `projet/themes.json`

C'est l'étape qui fait la différence entre une série correcte et une bonne
série. Ouvre `transcription.txt` à côté et ajuste.

```json
{
  "id": "01-discipline",
  "titre": "La discipline bat la motivation",
  "debut": 0.0,
  "fin": 734.5,
  "resume": "La motivation est un invité qui repart tôt. L'habitude reste.",
  "mots_cles": ["discipline", "habitude", "répétition"],
  "ambiance": "aube_froide",
  "look": "ice",
  "palette": "argent",
  "plan_sec": 6,
  "texture": "normal",
  "transition": "fondu"
}
```

| Champ | Rôle |
|---|---|
| `id` | Nom des fichiers produits. Lettres, chiffres, tirets |
| `titre` | Pour toi, et pour la description TikTok |
| `debut` / `fin` | Bornes en secondes. **C'est ce que tu corriges le plus** |
| `ambiance` | Le type d'images fabriquées (`./mz ambiances`) |
| `look` | L'étalonnage (`./mz looks`) |
| `palette` | Couleur de la signature Mr ZIKA |
| `plan_sec` | Durée d'un plan. `4` nerveux, `6` équilibré, `9` posé |
| `texture` | `aucun` `doux` `normal` `fort` |
| `transition` | `coupe` `flash` `noir` `fondu` |

Contrôle ta copie :

```bash
./mz themes -v
```

Signale les identifiants en double, les bornes qui se chevauchent, les
ambiances inconnues, et les parties qui finiraient trop courtes.

### Accorder l'ambiance au propos

| Le sujet parle de… | Ambiance | Étalonnage |
|---|---|---|
| Discipline, habitudes, se lever tôt | `aube_froide` | `ice` |
| Effort, colère, urgence, se battre | `braise` | `fire` |
| Gratitude, apaisement, ce qu'on a gagné | `heure_doree` | `gold` |
| Ambition, ville, jeunesse, insomnie | `nuit_neon` | `cyber` |
| Épreuve, adversité, traverser | `orage` | `ice` |
| Réussite, recul, vue d'ensemble | `sommet` | `orange_teal` |
| Solitude, gravité, silence | `vide` | `noir` |

Alterner les ambiances d'un thème à l'autre évite que ta chaîne se ressemble.

---

## 4. `mz decouper` — tailler en parties de 5 minutes

```bash
./mz decouper
```

Pour chaque thème, le studio calcule d'abord **combien** de vidéos sont
nécessaires, puis vise des parties de longueur égale. Un thème de 11 minutes
donne trois parties de 3 min 40 — pas deux de 5 min et une de 1 minute.

Chaque frontière glisse ensuite sur le **silence le plus large** à proximité :
on ne coupe jamais une phrase.

Résultat, dans `projet/parties/` :

```
01-discipline/partie-01.srt    sous-titres recalés sur zéro
01-discipline/partie-01.txt    le texte de la partie
plan.tsv                       la feuille de route
```

Les sous-titres viennent de la transcription : ils tombent juste, sans
réglage.

---

## 5. `mz serie` — tout produire

```bash
./mz serie -e      # voir le programme sans rien calculer
./mz serie         # produire
```

Pour chaque partie, le studio :

1. **coupe la voix** dans le fichier d'origine et lui applique le mastering
   complet (nettoyage, égalisation, −14 LUFS) ;
2. **fabrique les images** de l'ambiance du thème, avec un tirage différent
   par thème — deux thèmes n'auront jamais les mêmes fonds ;
3. **monte la vidéo** avec l'étalonnage, la texture et le rythme du thème,
   les sous-titres, la signature et le filigrane.

| Option | Rôle |
|---|---|
| `-t <id>` | Ne traiter qu'un thème |
| `-n <n>` | Nombre de fonds par thème (défaut 18) |
| `-r 2k\|4k\|8k` | Définition des fonds (défaut `4k`) |
| `-F` | Refaire les fonds |
| `-S` | Ne pas générer de fonds : tu fournis tes images |
| `-q <crf>` | Qualité d'encodage (défaut 19) |
| `-e` | Essai à blanc |

Compte **environ 20 minutes de calcul par vidéo** sur 4 cœurs. Une
conférence d'une heure donnant 12 vidéos représente donc une nuit de rendu.
Lance-la avant de dormir.

Le travail est repris là où il s'est arrêté : les voix déjà découpées, les
fonds déjà générés et les plans déjà étalonnés sont conservés. Tu peux
interrompre et relancer sans tout refaire.

---

## Fournir tes propres images

Dépose-les dans `projet/03-broll/<id-du-theme>/` puis :

```bash
./mz serie -S
```

Tu peux aussi mélanger : garde les fonds générés et ajoute tes photos dans le
même dossier. Ils seront alternés.

---

## Que faire des vidéos produites

Un thème de 15 minutes donne 3 vidéos. Ne les publie pas le même jour :
étale-les, et numérote-les dans le titre (« 1/3 », « 2/3 »). Les gens qui
accrochent sur la première cherchent la suite — c'est ce qui construit un
compte, plus que les vues d'une vidéo isolée.

Détails de publication : [03-TIKTOK.md](03-TIKTOK.md)
