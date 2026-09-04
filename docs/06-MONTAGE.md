# Monter un rush court

Tu as filmé un plan au téléphone. Le studio repère les passages nets, jette
le flou de bougé, recadre en vertical, étalonne et signe.

```bash
./mz analyser mon-plan.mp4
./mz montage -i mon-plan.mp4
```

---

## 1. `mz analyser` — trouver ce qui est utilisable

```bash
./mz analyser mon-plan.mp4
```

Mesure la netteté image par image (variance du laplacien) et affiche un
graphique en texte. Les creux, c'est du flou de bougé — inutilisable.

Il en tire trois choses :

**Les passages exploitables.** Uniquement les plages nettes assez longues.

**Où recadrer.** Il cherche la bande de l'image qui porte le plus de détail —
en général le sujet — et place le cadre pour que ce sujet tombe aux deux
cinquièmes de la hauteur. Plus bas, il passerait sous les sous-titres.

**Une liste de montage** (`.edl.tsv`), avec le meilleur passage en ouverture
et le deuxième meilleur en fermeture. On n'ouvre pas sur un plan mou et on ne
finit pas sur le plus faible.

| Option | Rôle |
|---|---|
| `--plan <s>` | Durée visée d'un plan monté (défaut 1,7) |
| `--nb <n>` | Nombre de plans maximum (défaut 6) |
| `--seuil <x>` | Exigence de netteté. `1.0` = la moyenne, `1.3` = sévère |
| `--mini <s>` | Plage nette minimale retenue (défaut 0,45) |

---

## 2. Corriger la liste

C'est un fichier texte, une ligne par plan :

```
#debut	duree	vitesse	commentaire
6.38	0.72	0.62	accroche : la montre, ralenti
2.38	1.24	0.58	la conduite
0.50	0.62	0.45	la route qui defile
7.10	1.02	0.42	fermeture : la montre, tres ralenti
```

`vitesse` en dessous de 1 ralentit. `0.50` fait durer un plan deux fois plus
longtemps.

**Ce que l'automatique ne sait pas faire :** couper une bonne plage en deux
pour qu'elle serve à la fois d'ouverture et de fermeture, sans se répéter.
C'est exactement ce que fait l'exemple ci-dessus avec la zone 6,4–8,1 s,
partagée en `6.38 → 7.10` et `7.10 → 8.12`. À toi de le faire.

---

## 3. `mz montage` — produire

```bash
./mz montage -i mon-plan.mp4 -l luxe -y 250 -T flash
```

| Option | Rôle |
|---|---|
| `-e <edl>` | Liste de montage (défaut `<video>.edl.tsv`) |
| `-l <look>` | Étalonnage (`./mz looks`) — défaut `luxe` |
| `-x <texture>` | `aucun` `doux` `normal` `fort` — défaut `doux` |
| `-T <transi>` | `coupe` `flash` `noir` `fondu` — défaut `flash` |
| `-y <px>` | Recadrage vertical, **après** agrandissement |
| `-n <force>` | Netteté rendue après agrandissement (défaut 0,9) |
| `-z <pct>` | Zoom lent sur chaque plan (défaut 3 %) |
| `-H <force>` | Halo cinéma, 0 à 0,6 (défaut 0,30) |
| `-a <son>` | `origine` · `muet` · un fichier audio |
| `-I` | Sans signature de fin |

### La signature s'adapte à la durée

Sur une vidéo assez longue, c'est la carte de fin complète (5 s). Sur un clip
court, elle mangerait la moitié de la vidéo : le studio bascule alors sur une
simple apparition du logo, longue d'un tiers du clip, entre 1,2 s et 2,4 s,
avec un voile sombre en dessous pour que l'or reste lisible.

### L'agrandissement

Le studio te dit le facteur. Au-delà de **×1,6**, l'image sera molle : c'est
la limite de ta source, pas du montage. Un plan filmé en 480 px agrandi en
1080 restera flou quoi qu'on fasse. Filme en 4K quand tu peux — voir
[01-GUIDE-TOURNAGE.md](01-GUIDE-TOURNAGE.md).

---

## 4. Le son

Par défaut le studio reprend le son du rush et le ramène à −14 LUFS.

**Si ton plan a de la musique commerciale**, publie plutôt la version muette
et ajoute la musique depuis la bibliothèque TikTok, qui est sous licence :

```bash
./mz montage -i mon-plan.mp4 -a muet
```

Ou pose ta propre musique libre de droits :

```bash
./mz montage -i mon-plan.mp4 -a musique.mp3
```

---

## 5. Ce qu'un plan court peut porter

Un rush de 8 secondes ne fait pas une vidéo de 5 minutes. Ce qu'il peut être :

- **une accroche** de 7 à 12 s, publiée telle quelle ;
- **un plan parmi d'autres** dans une vidéo longue : dépose-le dans
  `projet/03-broll/<theme>/` à côté des autres images, `mz build` s'en sert
  comme de n'importe quel plan.

Pour tenir 5 minutes sans lasser, il faut 15 à 25 plans différents.

---

## 7. Une photo → une affiche

Même travail, sur une image fixe : recadrage 9:16, étalonnage, voile dégradé
pour que le texte reste lisible, phrase, signature.

```bash
./mz affiche ma-photo.jpg --haut "ILS VERRONT LE RÉSULTAT" \
                          --bas "PAS LES *NUITS*." --look ice
```

| Option | Rôle |
|---|---|
| `--haut` | Petite ligne, largement espacée, avec un filet doré dessous |
| `--bas` | La grande ligne. `\|` sépare deux lignes, `*mot*` le passe en doré |
| `--look` | `./mz looks` |
| `--niveaux noir,blanc` | Étend les niveaux d'une photo plate. `0.043,0.749` = le noir de la source est à 4,3 % et le blanc à 74,9 % |
| `--balance rouge,bleu` | Corrige la dominante. `-0.05,0.09` neutralise du tungstène |
| `--voile` `--voile-bas` | Force des dégradés haut et bas |
| `--y-haut` `--y-bas` | Hauteurs, en fraction de l'image |
| `--grille` | Affiche une grille de repérage pour placer le texte |

**Commence toujours par `--grille`.** Elle montre où tombent les 10 %, 20 %,
30 %… et t'évite de poser du texte sur le visage.

### Lire une photo avant de l'étalonner

Une photo d'intérieur au téléphone est presque toujours plate et jaune.
Regarde ses chiffres avant de choisir :

```bash
python3 -c "
import numpy as np; from PIL import Image
a = np.asarray(Image.open('ma-photo.jpg').convert('RGB'), np.float32)
l = a.mean(axis=2)
print('R-B', a[...,0].mean()-a[...,2].mean(), 'p1', np.percentile(l,1), 'p99', np.percentile(l,99))"
```

- **R−B nettement positif** → dominante tungstène, corrige avec `--balance`.
- **p99 bien en dessous de 250** → il n'y a pas de vrai blanc, étends avec
  `--niveaux`.

Sur la photo de nuit servant d'exemple : R−B passe de +20 à +9, le noir de
11 à 0 et le blanc de 191 à 252. C'est ce redressement — pas le look — qui
fait le gros du travail.
