# Catalogue des effets

Chaque effet du studio correspond à un outil réel de DaVinci Resolve ou
d'After Effects. Ce document dit **ce que c'est**, **quand l'utiliser**, et
**où le régler** si tu veux aller plus loin.

---

## 1. Étalonnage — option `-l`

L'équivalent de la page Color de DaVinci Resolve : une courbe en S pour le
contraste, puis les roues chromatiques (ombres / tons moyens / hautes
lumières) pour la teinte.

| Look | Effet | Pour quel propos |
|---|---|---|
| `orange_teal` | Ombres cyan, peaux et lumières orange | Valeur sûre, marche sur tout |
| `ice` | Froid, acier, désaturé, contraste élevé | Discipline, rigueur, hiver, sport |
| `fire` | Orange brûlant, noirs écrasés, très punchy | Le grind, la colère, l'urgence |
| `gold` | Chaud, doux, noirs levés façon pellicule | Gratitude, souvenir, apaisement |
| `noir` | Noir et blanc contrasté | Gravité, sobriété, texte fort |
| `cyber` | Magenta / cyan saturés | Nuit, ville, futur, jeunesse |
| `raw` | Contraste léger, couleurs fidèles | Quand tes images sont déjà étalonnées |

```bash
./mz build -l fire
./mz looks          # la liste avec les descriptions
```

Comparer trois looks sur 20 secondes :

```bash
for L in orange_teal ice fire; do
  ./mz build -R -l $L -d 20 -o essai_$L.mp4
done
```

**Où c'est réglé** : `lib/grades.sh`, fonction `mz_grade`. Chaque look est
une chaîne de filtres `curves` + `colorbalance` + `eq`. Les points de la
courbe se lisent `entrée/sortie` de 0 à 1 : `0.22/0.16` assombrit les
ombres, `0.78/0.84` éclaircit les hautes lumières. C'est la courbe en S.

---

## 2. Halo lumineux (halation) — automatique

L'effet **Glow** de Resolve. C'est lui qui fait la moitié du rendu cinéma.

Le principe : on isole les hautes lumières de l'image, on les floute
fortement, on les teinte légèrement chaud, puis on les rajoute en mode
*Screen*. Résultat : les sources lumineuses débordent doucement sur ce qui
les entoure, comme sur une vraie pellicule.

**Où c'est réglé** : `lib/grades.sh`, fonction `mz_fx_halation`. Le
troisième paramètre est l'intensité (0.36 par défaut). Monte à 0.5 pour un
rendu rêveur, descends à 0.2 pour rester net.

---

## 3. Texture — option `-x`

Trois effets groupés, appliqués après l'étalonnage :

- **Grain argentique** (`noise`) — casse le côté « numérique propre » et
  masque les aplats de couleur.
- **Aberration chromatique** (`rgbashift`) — décale le rouge et le bleu
  d'un ou deux pixels, comme une lentille bon marché. Détail subtil, mais
  c'est ce qui « sent le film ».
- **Vignettage** (`vignette`) — assombrit les bords, ramène l'œil au centre.
- **Micro-netteté** (`unsharp`) — récupère le piqué perdu au floutage.

| Valeur | Rendu |
|---|---|
| `aucun` | Aucune texture. Pour des images déjà granuleuses |
| `doux` | Discret. Pour les visages et les plans clairs |
| `normal` | Le réglage par défaut |
| `fort` | Marqué, façon pellicule poussée. Va bien avec `fire` et `noir` |

```bash
./mz build -x fort
```

---

## 4. Mouvement de caméra — automatique

Aucune image n'est jamais figée. Le studio alterne **quatre mouvements**
d'un plan au suivant :

1. Zoom avant lent (11 %)
2. Zoom arrière lent
3. Zoom + panoramique vers la droite
4. Zoom + panoramique vers la gauche

C'est le procédé « Ken Burns ». Les images sont d'abord agrandies au double
de la résolution finale : le déplacement se fait donc en sous-pixel, sans
saccade.

S'y ajoute un **coup de zoom** de 3,5 % sur les trois premiers dixièmes de
chaque plan — l'image « se pose ». C'est ce qui donne le rythme, même sur
des photos fixes.

**Où c'est réglé** : `bin/mz-build.sh`, bloc `DIRZ` et variable `PUNCH`.

---

## 5. Transitions — option `-T`

| Valeur | Effet | Quand |
|---|---|---|
| `coupe` | Coupe franche, aucun fondu | **Par défaut.** C'est ce que fait le format court : maximum d'énergie, zéro clignotement |
| `flash` | Éclair blanc de 0,09 s | Percussif. Cale-le sur la musique |
| `fondu` | Passage au noir de 0,16 s | Adoucit sans casser le rythme |
| `noir` | Passage au noir de 0,24 s | Marque une respiration entre deux idées |

> `fondu` et `noir` passent réellement **par le noir** à chaque raccord.
> Avec des plans courts (`-p 4`), ça finit par clignoter : reste sur `coupe`.
> Plus les plans sont longs (`-p 8` et plus), plus le fondu se justifie.

```bash
./mz build -T flash -p 4.5     # nerveux
./mz build -T fondu -p 9       # contemplatif
```

---

## 6. Sous-titres animés

Une reprise du style TikTok : gros caractères, contour noir épais, ombre
portée, apparition élastique.

- **Le « pop »** : le texte entre à 58 % de sa taille, dépasse à 106 %,
  puis se pose à 100 %. En 170 millisecondes. C'est l'équivalent d'une
  courbe *ease-out-back* d'After Effects.
- **Le mot doré** : entoure un mot d'astérisques dans `script.txt` et il
  s'affiche en `#FFC845`.
- **Le calage** : la détection de silences (`silencedetect`) repère les
  plages où tu parles et y répartit les groupes de mots. Pas besoin de
  synchroniser à la main.

```bash
./mz build -f 130 -w 2      # gros caractères, 2 mots par groupe : très frappé
./mz build -f 96  -w 5      # plus discret, phrases plus longues
```

**Où c'est réglé** : `tools/make_captions.py`. Le dictionnaire `ENTRIES`
contient les animations d'entrée (`pop`, `punch`, `montee`, `aucune`).
Les couleurs, la taille du contour et la hauteur du texte sont des options
en ligne de commande.

---

## 7. La signature Mr ZIKA

### Le logo

Généré par `tools/make_signature.py` (Pillow), avec quatre calques
superposés comme dans Photoshop ou After Effects :

1. **Ombre portée** — le masque du texte, flouté, décalé vers le bas.
2. **Halo externe** (*Outer Glow*) — deux passes, une large et douce, une
   serrée et intense, teintées dans la couleur de la palette.
3. **Contour sombre** — détache le logo de n'importe quel fond.
4. **Corps métallique** — un dégradé vertical à 7 points d'arrêt (or sombre
   → or vif → blanc chaud → or → or sombre) découpé par le texte, plus un
   **biseau** : liseré clair en haut, liseré sombre en bas.

Cinq palettes : `or`, `argent`, `feu`, `glace`, `blanc`.

```bash
./mz brand -c argent
./mz brand -n "ZIKA" -p "Mr" -c feu
```

### Le balayage de lumière (*Light Sweep*)

L'animation de logo la plus utilisée en motion design, et celle qui fait
« logo professionnel » d'un coup.

Comment elle est construite ici :

1. Une bande lumineuse diagonale est générée en niveaux de gris (NumPy,
   deux gaussiennes : un cœur net et un halo large).
2. Elle traverse le cadre du logo de gauche à droite en 0,85 s.
3. Elle est **multipliée par le masque alpha des lettres** — la lumière
   n'existe donc que sur le métal, jamais autour.
4. Le résultat devient le canal alpha d'un calque blanc, superposé au logo.

L'animation est rendue une fois en `.mov` avec transparence
(codec `qtrle`), puis simplement superposée au montage.

### Les trois usages

| Élément | Où | Durée |
|---|---|---|
| Révélation d'intro | plein cadre, centré | 3,5 s au début |
| Carte de fin | plein cadre + phrase d'appel | 5 s à la fin |
| Filigrane permanent | bas de l'image, 72 % d'opacité | toute la vidéo |

```bash
./mz brand -i 4 -o 6                     # intro 4 s, fin 6 s
./mz brand -a "ABONNE-TOI, ON MONTE"     # change la phrase de fin
./mz build -k 0                          # enlève le filigrane permanent
./mz build -I                            # ni intro ni carte de fin
```

---

## 8. Le son

### Traitement de la voix — `mz audio -v`

| Niveau | Traitement |
|---|---|
| `0` | Aucun |
| `1` | Coupe-bas 70 Hz, présence légère, compression douce |
| `2` | Coupe-bas 85 Hz, réduction de bruit, égalisation complète, compression *(défaut)* |
| `3` | Réduction de bruit renforcée, deux compresseurs en série. Pour les sources difficiles |

La chaîne du niveau 2 : coupe-bas 85 Hz (élimine grondements et plosives),
`afftdn` (réduction de bruit spectrale), −2,5 dB à 200 Hz (dégage la
boue), +3 dB à 3 kHz (intelligibilité), +2 dB à 9 kHz (l'air), puis un
compresseur à 3:1.

### Calibration du volume

Deux passes : la première **mesure** le niveau réel du fichier, la seconde
**applique** la correction avec ces valeurs. C'est la méthode broadcast —
bien plus juste qu'une normalisation aveugle.

Cible : **−14 LUFS**, crête maximale −1,5 dBTP. C'est ce que visent TikTok,
YouTube et Instagram. Une vidéo calibrée ne sera ni écrasée ni remontée par
la plateforme.

```bash
./mz audio source.mp4 -l -16     # plus doux
./mz audio source.mp4 -v 3 -g 4  # source faible : +4 dB avant traitement
```

### La musique qui s'efface sous la voix

Compression *sidechain* : la voix pilote le volume de la musique. Dès que
tu parles, la musique descend ; dans les silences, elle remonte. C'est la
technique de la radio, et elle évite le mixage manuel.

```bash
./mz build -m musique.mp3 -v -22   # musique plus discrète
```

---

## 9. Aller plus loin

Effets disponibles dans `lib/grades.sh`, non activés par défaut :

- `mz_fx_shake <amplitude> <vitesse>` — tremblement caméra « tenue à la
  main ». Rend vivant un plan totalement fixe.
- `mz_fx_breathe <amplitude>` — respiration lente du cadre, zoom
  sinusoïdal sur 9 secondes.

Pour les activer, ajoute-les à la chaîne de filtres dans
`bin/mz-build.sh`, juste après `${PUNCH}`.
