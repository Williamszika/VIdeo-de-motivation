# Guide de tournage — fabriquer les images de ta vidéo

C'est la partie que tu fais toi. Le studio s'occupe du reste.
Compte **une demi-journée de tournage** pour de quoi alimenter 5 à 8 vidéos.

---

## 1. Ce qu'il te faut

Ton téléphone suffit. Vraiment. Ce qui compte, dans l'ordre :

1. **La lumière** — filme tôt le matin ou en fin d'après-midi. La lumière
   rasante sculpte les visages et les décors. Entre 11 h et 15 h, le soleil
   au zénith aplatit tout et creuse des cernes noirs.
2. **La stabilité** — cale tes coudes contre ton corps, ou pose le téléphone
   sur un muret, un sac, une bouteille. Un plan fixe et net vaut dix plans
   tremblants.
3. **Le mouvement dans le cadre** — de la fumée, du vent dans les arbres, une
   silhouette qui marche, des voitures qui passent. Un plan totalement figé
   fait décrocher le spectateur.

Ce dont tu n'as **pas** besoin : micro (c'est la voix extraite qui porte le
son), stabilisateur, éclairage, drone.

---

## 2. Réglages du téléphone

| Réglage | Valeur | Pourquoi |
|---|---|---|
| Résolution | **4K** si possible, sinon 1080p | Le recadrage vertical coupe dans l'image : il faut de la marge |
| Cadence | **30 i/s** | La vidéo finale est en 30 i/s |
| Ralenti | **60 ou 120 i/s** sur quelques plans | Un ralenti dans un montage rapide crée une respiration |
| Orientation | **verticale** de préférence | Cadrage direct, aucune perte |
| Grille | activée | Aide à placer le sujet |
| Verrouillage AE/AF | **appui long avant de filmer** | Empêche l'image de « pomper » en luminosité |
| HDR | **désactivé** | Les couleurs HDR virent au délavé après étalonnage |

> Si tu filmes en **horizontal**, ce n'est pas grave : le studio recadre
> automatiquement au centre. Mais garde ton sujet **au milieu du cadre**,
> sinon il sera coupé.

---

## 3. Durée et nombre de plans

- Chaque plan est utilisé **6 secondes** par défaut (`-p`).
- Filme **10 à 15 secondes** par plan : ça laisse de quoi choisir.
- Une vidéo de 5 minutes = **50 segments**. Le studio réutilise tes plans en
  changeant à chaque fois le mouvement de caméra et le point de départ.
- **15 à 25 plans différents** suffisent largement pour 5 minutes sans que
  la répétition se voie.

---

## 4. Liste de plans à tourner

Coche au fur et à mesure. Ces 18 plans couvrent la quasi-totalité des sujets
de motivation.

### L'effort
- [ ] Chaussures de sport qu'on lace, en gros plan
- [ ] Course de dos, sur une route ou un stade vide
- [ ] Mains sur une barre, une corde, un sac de frappe
- [ ] Gouttes de sueur, respiration, visage de trois quarts
- [ ] Escalier monté à pied, contre-plongée

### La solitude choisie
- [ ] Silhouette seule face à l'horizon (mer, colline, toit)
- [ ] Marche de dos dans une rue vide, tôt le matin
- [ ] Fenêtre, lumière du matin, personne derrière
- [ ] Chaise, table, carnet ouvert, lumière rasante

### La ville et le temps
- [ ] Trafic accéléré, phares filés à la tombée du jour
- [ ] Passants flous, personnage immobile net
- [ ] Horloge, montre, réveil
- [ ] Vue plongeante sur des immeubles

### La nature et le souffle
- [ ] Lever ou coucher de soleil, plan large
- [ ] Vagues qui frappent des rochers
- [ ] Vent dans les hautes herbes ou les arbres
- [ ] Route droite qui file vers l'horizon
- [ ] Ciel d'orage, nuages rapides

### Trois mouvements à connaître

| Mouvement | Comment | Quand l'utiliser |
|---|---|---|
| **Le fixe** | Téléphone posé, tu ne bouges pas | Le studio ajoute un zoom lent : ça suffit |
| **Le travelling** | Tu marches lentement en avançant, bras tendus | Ouvre une séquence, installe un lieu |
| **La révélation** | Tu pars sur un détail, puis tu relèves vers le sujet | Ponctue une phrase forte |

---

## 5. Si tu ne peux pas filmer

Banques d'images gratuites, utilisables commercialement, sans attribution
obligatoire :

| Site | Ce qu'on y trouve |
|---|---|
| **Pexels** (pexels.com/videos) | Le plus fourni en vidéo verticale |
| **Pixabay** (pixabay.com/videos) | Vidéos et photos, bon fonds nature |
| **Mixkit** (mixkit.co) | Clips courts, bien étalonnés |
| **Videvo** | Vérifie la licence clip par clip |

Mots-clés qui donnent de bons résultats : `silhouette sunset`,
`running motivation`, `city night timelapse`, `ocean waves slow motion`,
`man walking alone`, `gym dark`, `storm clouds`, `mountain fog`.

Sur chaque site, **filtre en « Vertical »** et trie par « Populaire ».
Télécharge en 4K quand c'est proposé.

Prends 20 clips, dépose-les dans `projet/03-broll/`, lance `./mz plans`.

> Vérifie toujours la licence sur la page du fichier. Elle change parfois
> d'un clip à l'autre sur un même site.

---

## 6. Organiser tes fichiers

Le studio traite les fichiers **par ordre alphabétique**. C'est ton outil de
montage : nomme-les dans l'ordre où tu veux les voir.

```
projet/03-broll/
  01-reveil.mp4
  02-chaussures.jpg
  03-course-dos.mp4
  04-escalier.mp4
  05-ville-nuit.mp4
  ...
```

Construis une progression : **descente → bascule → montée**. Commence
sombre et fermé, finis lumineux et ouvert. C'est ce qui donne l'impression
que la vidéo « va quelque part », même si la voix ne change pas de ton.

---

## 7. Les cinq erreurs qui gâchent une vidéo

1. **Filmer à 4 h de l'après-midi en plein soleil.** Contraste violent,
   ombres dures, rien à rattraper à l'étalonnage.
2. **Zoomer avec les doigts.** Le zoom numérique détruit la définition.
   Avance physiquement.
3. **Filmer contre une fenêtre sans compenser.** Ton sujet devient une
   silhouette noire — sauf si c'est justement ce que tu cherches.
4. **Ne pas verrouiller l'exposition.** L'image change de luminosité au
   milieu du plan et ça se voit énormément après étalonnage.
5. **Utiliser des plans en dessous de 1080 px.** `./mz plans` te prévient.
   Un plan basse définition recadré en vertical devient flou.

---

## 8. Enregistrer ta propre voix

C'est ce qui fera la différence à long terme, et ça règle la question des
droits.

**Le matériel** : les écouteurs filaires de ton téléphone. Le micro est à
20 cm de ta bouche, dans l'axe.

**Le lieu** : une pièce avec des rideaux, un lit, un canapé, une armoire
ouverte pleine de vêtements. Ces surfaces absorbent l'écho. Évite salle de
bain, cuisine, cage d'escalier.

**La méthode** :
1. Écris ton texte à voix haute avant de l'enregistrer. Ce qui se lit bien
   ne s'entend pas forcément bien.
2. Enregistre debout. La voix porte mieux.
3. Fais une pause d'une seconde entre chaque phrase — c'est ce silence qui
   permet au calage automatique des sous-titres de fonctionner.
4. Rate une phrase ? Ne recommence pas tout : marque un silence de 3
   secondes et refais la phrase. Tu couperas au montage.
5. Vise **5 min 30** d'enregistrement pour 5 minutes de vidéo.

**Le traitement** — le studio s'en charge :

```bash
./mz audio mon-enregistrement.m4a -v 3
```

Coupe-bas, réduction de bruit, égalisation de présence, compression et
calibration à −14 LUFS. Ta voix de téléphone sonnera comme un podcast.
