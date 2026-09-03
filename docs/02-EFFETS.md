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
| `luxe` | Hautes lumières repliées, contraste ferme, peaux chaudes | Plein jour brûlant : voiture, montre, intérieur ensoleillé |
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

## 5. Raccords entre plans — option `-T`

Deux familles. La première « cuit » un fondu dans chaque plan ; la seconde
fait **coexister les deux plans** pendant la transition, comme un vrai banc
de montage.

### Fondus cuits — rapides, sans coût

| Valeur | Effet |
|---|---|
| `coupe` | Coupe franche. **Par défaut.** Zéro clignotement, énergie maximale |
| `flash` | Éclair blanc de 0,09 s. Percussif, à caler sur la musique |
| `fondu` | Passage au noir de 0,16 s |
| `noir` | Passage au noir de 0,24 s. Marque une respiration |

> `fondu` et `noir` passent réellement **par le noir**. Avec des plans courts
> (`-p 4`), ça finit par clignoter.

### Raccords à recouvrement — les vrais

Les deux plans se superposent pendant `-D` secondes (0,40 par défaut).

| Valeur | Effet | Équivalent |
|---|---|---|
| `enchaine` | Fondu enchaîné | *Cross Dissolve* |
| `flou` | Fondu par le flou horizontal | *Whip pan* / directional blur |
| `zoom` | Zoom avant qui traverse le raccord | *Zoom transition* |
| `glisse` | Le plan suivant pousse le précédent | *Push* |
| `dissolution` | Dissolution granuleuse | *Film dissolve* |
| `pixel` | Pixellisation | *Glitch* |
| `lumiere` | Passage par le blanc | *Dip to white* |
| `radial` | Balayage circulaire | *Radial wipe* |
| `volet` | Volet latéral adouci | *Smooth wipe* |
| `rideau` | Volet net | *Linear wipe* |

```bash
./mz build -T enchaine -D 0.5      # le plus classique
./mz build -T flou -D 0.35         # très After Effects
./mz build -T zoom -D 0.3 -p 4     # nerveux
```

**Ce que ça coûte.** Un raccord consomme 0,4 s à chaque jointure, donc il faut
plus de plans pour la même durée : le studio le recalcule tout seul. La
mémoire monte à environ 4 Go pour 50 plans enchaînés. Au-delà de 70 plans, le
studio repasse en coupe franche et te le dit — allonge les plans (`-p 9`)
pour garder ton raccord.

Même jeu d'options dans `mz montage`, avec `-d` pour la durée.

## 6. Sous-titres animés — options `-A` et `-B`

Onze animations d'apparition, chacune reprenant un preset d'After Effects.
Elles sont écrites en balises ASS : `\t()` anime une propriété, `\clip()`
masque, `\move()` déplace, `\blur` floute, `\kf` cadence le karaoké.

| Valeur | Effet | Quand |
|---|---|---|
| `pop` | Rebond élastique, dépasse puis se pose | **Par défaut.** Le plus sûr |
| `frappe` | Arrive très grand et net | Phrases coup de poing |
| `montee` | Monte depuis le bas en s'ouvrant | Passages calmes |
| `cascade` | Lettre par lettre en décalé, avec flou | L'« Animate In » d'After Effects |
| `machine` | Machine à écrire | Révélation, suspense |
| `balayage` | Révélé par un masque qui s'ouvre | Titres |
| `flou` | Sort du flou en se posant | Très cinéma |
| `glisse` | Glisse du côté avec une traînée | Rythme rapide |
| `karaoke` | Chaque mot s'allume à son tour | Quand on suit la voix |
| `bloc` | Bandeau qui se déploie puis le texte | Le look TikTok classique |
| `aucune` | Rien | Sous-titres sobres |

```bash
./mz build -A cascade
./mz build -A karaoke -w 5
python3 tools/make_captions.py --lister
```

### Le bandeau — `-B`

Sur une image chargée, un contour ne suffit pas. `-B` pose un bandeau opaque
derrière chaque sous-titre, dimensionné **exactement** au texte.

```bash
./mz build -A pop -B "#0E0E10"
```

Le studio mesure la largeur réelle que libass va rendre — pas celle que
Pillow calcule, qui est 1,7 fois trop grande sur Anton. Le facteur est
mesuré une fois par police, en rendant réellement une image, puis gardé en
cache dans `assets/fonts/.metriques.json`.

> Le bandeau est opaque par défaut. En le rendant transparent
> (`--fond-alpha`), les mots colorés laissent apparaître des raccords :
> libass dessine une boîte par segment de couleur, et les recouvrements se
> voient. C'est une limite de libass, pas un réglage.

### Le mot doré

Entoure un mot d'astérisques dans `script.txt` : `la *discipline*`. Il
s'affiche en `#FFC845`, dans toutes les animations.

### Le calage

Détection des silences dans la voix, ou horodatage mot à mot venu de
`mz ecoute`. Aucun réglage manuel.

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

## 9. La brume dérivante — option `-F`

Un fond fixe, même avec un zoom lent, finit par paraître mort. `-F` fait
dériver une nappe de brume par-dessus l'image, en fusion « lumière douce ».

```bash
./mz build -F 0.30      # 0 désactive, 0.6 est très marqué
```

La nappe est du bruit fractal calculé une fois (`assets/overlays/brume.jpg`),
puis déplacée sur deux périodes premières entre elles — le motif ne se répète
donc jamais à l'identique. C'est l'équivalent d'un calque *fractal noise*
animé dans After Effects, pour une fraction du coût.

## 10. Aller plus loin

Effets disponibles dans `lib/grades.sh`, non activés par défaut :

- `mz_fx_shake <amplitude> <vitesse>` — tremblement caméra « tenue à la
  main ». Rend vivant un plan totalement fixe.
- `mz_fx_breathe <amplitude>` — respiration lente du cadre, zoom
  sinusoïdal sur 9 secondes.

Pour les activer, ajoute-les à la chaîne de filtres dans
`bin/mz-build.sh`, juste après `${PUNCH}`.
