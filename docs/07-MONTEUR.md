# Le monteur — faire tes vidéos comme tu veux

`mz build`, `mz montage` et `mz serie` sont des raccourcis : ils décident à
ta place. Le **monteur** ne décide rien. Tu écris un fichier de projet, il le
fabrique. Tu changes une ligne, tu relances, seul ce qui dépend de cette
ligne est recalculé.

```bash
./mz projet --depuis projet/03-broll --out projet/ma-video.yml
# tu édites projet/ma-video.yml
./mz projet -f projet/ma-video.yml
```

---

## 1. Créer un projet

**Depuis un dossier d'images** — le plus rapide :

```bash
./mz projet --depuis projet/03-broll --out projet/ma-video.yml \
            --duree 300 --plan 6 \
            --voix projet/02-audio/voix.wav \
            --script projet/script.txt
```

**Ou un modèle vide**, entièrement commenté :

```bash
./mz projet --nouveau projet/ma-video.yml
```

**Vérifier avant de rendre** — ça ne calcule rien et prend une seconde :

```bash
./mz projet -f projet/ma-video.yml --verifier
```

---

## 2. Le fichier de projet

```yaml
sortie: 04-rendu/ma-video.mp4

format:
  largeur: 1080
  hauteur: 1920
  images_par_seconde: 30

duree: auto            # ou un nombre de secondes
qualite: 19            # 16 excellente · 19 équilibrée · 23 légère
```

Tous les chemins sont **relatifs au fichier de projet**, pas au répertoire
d'où tu lances la commande. Le projet reste valable où que tu sois.

### `defaut` — appliqué à tous les plans

```yaml
defaut:
  etalonnage: luxe
  texture: doux
  halo: 0.30
  brume: 0.25
  mouvement: auto
  raccord: enchaine
  raccord_duree: 0.4
  duree_plan: 6
  zoom: 0
```

| Champ | Valeurs |
|---|---|
| `etalonnage` | `./mz looks` |
| `texture` | `aucun` `doux` `normal` `fort` |
| `halo` | 0 à 0,6 — le halo cinéma |
| `brume` | 0 à 0,6 — la nappe dérivante sur le fond |
| `mouvement` | `auto` `zoom_avant` `zoom_arriere` `pano_droite` `pano_gauche` `fixe` |
| `raccord` | voir ci-dessous |
| `duree_plan` | secondes, si le plan n'en précise pas |
| `zoom` | coup de zoom au démarrage, en % |

`auto` fait tourner les quatre mouvements d'un plan au suivant : deux plans
voisins ne bougent jamais pareil.

### `plans` — l'ordre, c'est ton montage

```yaml
plans:
  - source: 03-broll/01.jpg

  - source: 03-broll/02.jpg
    duree: 4
    etalonnage: fire          # surcharge locale
    raccord: flou

  - source: 03-broll/interview.mp4
    debut: 12.5               # où commencer dans le fichier
    duree: 5
    vitesse: 0.6              # < 1 = ralenti
    mouvement: fixe
```

**Chaque champ de `defaut` est surchargeable plan par plan.** Un plan en noir
et blanc au milieu d'une séquence chaude : une ligne.

`raccord` décrit la transition **vers le plan suivant**.

| Sans recouvrement | | Avec recouvrement — les deux plans coexistent | |
|---|---|---|---|
| `coupe` | franche | `enchaine` | fondu enchaîné |
| `flash` | éclair blanc | `flou` | fondu par le flou |
| `noir` | passage au noir | `zoom` | zoom traversant |
| `fondu` | noir plus court | `glisse` | le suivant pousse |
| | | `dissolution` | dissolution granuleuse |
| | | `pixel` | pixellisation |
| | | `lumiere` | passage par le blanc |
| | | `radial` `volet` `rideau` | balayages |

### `soustitres` — automatiques

```yaml
soustitres:
  script: script.txt        # ou bien :  srt: parties/01.srt
  animation: cascade
  mots_par_groupe: 3
  taille: 112
  hauteur: 1240
  bandeau: "#0E0E10"        # enlève la ligne pour un simple contour
  accent: "#FFC845"
```

Onze animations : `python3 tools/make_captions.py --lister`.
Avec un `.srt` venu de `mz ecoute`, le calage est au mot près.

### `textes` — les titres que tu poses

```yaml
textes:
  - a: 0.6                  # instant de départ, en secondes
    duree: 2.4
    contenu: "PERSONNE NE VIENDRA TE *SAUVER*"
    animation: frappe
    taille: 140
    hauteur: 700
    bandeau: "#0E0E10"
```

Ils se superposent aux sous-titres, chacun avec sa taille, sa couleur et son
animation. Un mot entre astérisques passe en doré.

### `son` et `marque`

```yaml
son:
  voix: 02-audio/voix.wav
  musique: 02-audio/musique.mp3   # ~ pour aucune
  volume_musique: -19
  lufs: -14
  fondu_sortie: 1.6

marque:
  filigrane: oui
  intro: oui
  fin: oui
```

La musique baisse toute seule sous la voix. La signature de fin s'adapte :
carte complète si la vidéo est assez longue, sinon simple apparition du logo.

---

## 3. Ce que la vérification attrape

`--verifier` prend une seconde et t'évite une heure de rendu pour rien :

- un fichier source qui n'existe pas ;
- un étalonnage, un raccord ou un mouvement mal orthographié ;
- un plan qui demande 8 secondes à un clip qui n'en fait que 5 ;
- **un titre posé par-dessus l'intro, la carte de fin ou le filigrane** —
  avec la hauteur à laquelle le déplacer.

```
▲ texte 1 « PERSONNE NE VIENDRA » passe sur l'intro Mr ZIKA (vers 0:00).
  Déplace-le : « hauteur: 1308 » ou change son instant.
```

---

## 4. Le cache

Chaque plan est rendu une fois et gardé sous une empreinte de ses réglages :
source, date du fichier, début, durée, vitesse, étalonnage, texture, halo,
brume, mouvement, raccord, format.

Change l'étalonnage d'un seul plan : **lui seul est recalculé**. Sur un
projet de 50 plans, une retouche coûte quelques secondes au lieu de dix
minutes.

```bash
./mz projet -f ma-video.yml --refaire    # tout refaire
./mz projet -f ma-video.yml --jobs 2     # limiter la charge machine
```

---

## 5. Une façon de travailler

1. `./mz projet --depuis` pour dégrossir.
2. `--verifier` — corrige ce qu'il signale.
3. Rends une version courte : mets `duree: 20` et `qualite: 27`.
4. Regarde **sur ton téléphone**.
5. Ajuste : réordonne les plans, change les raccords, déplace les titres.
6. Repasse en `duree: auto` et `qualite: 19`, relance.

Le cache fait que les étapes 3 à 5 coûtent presque rien.

---

## 6. Et les autres commandes ?

Elles restent utiles — ce sont des raccourcis qui décident pour toi :

| | |
|---|---|
| `mz build` | une vidéo depuis un dossier, en une commande |
| `mz montage` | un rush court découpé sur les passages nets |
| `mz serie` | toutes les vidéos d'une longue conférence |

Quand l'une d'elles ne fait pas exactement ce que tu veux, passe au monteur :
`./mz projet --depuis <ton dossier>` te donne un point de départ, et tout
devient modifiable.
