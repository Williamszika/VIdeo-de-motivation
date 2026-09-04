# Publier sur TikTok

---

## 1. Le fichier produit

| Caractéristique | Valeur |
|---|---|
| Résolution | 1080 × 1920 (9:16) |
| Cadence | 30 images / seconde |
| Codec vidéo | H.264 High, `yuv420p` |
| Codec audio | AAC 192 kb/s, 48 kHz, stéréo |
| Volume | −14 LUFS, crête −1,5 dBTP |
| Durée | exactement 5 min 00 |
| `faststart` | activé (lecture immédiate) |

C'est ce que TikTok, YouTube Shorts et Instagram Reels attendent. Aucune
conversion n'est nécessaire.

**Transfère toujours le fichier d'origine** (câble, AirDrop, Google Drive,
Telegram en « fichier »). Envoyer la vidéo par WhatsApp en pièce jointe
normale la recompresse et la dégrade.

---

## 2. Zones à ne pas encombrer

L'interface de TikTok recouvre une partie de l'image :

| Zone | Ce qu'il y a dessus |
|---|---|
| Bas, sur 15 % de la hauteur | Pseudo, description, musique |
| Droite, sur 20 % de la largeur | Boutons j'aime, commentaires, partage |
| Haut, sur 8 % | Recherche, onglets |

Le studio place déjà les sous-titres à **65 %** de la hauteur et le
filigrane à **77,5 %** — hors de ces zones. Si tu changes ces valeurs,
vérifie le résultat sur ton téléphone avant de publier.

---

## 3. Les trois premières secondes

C'est là que tout se joue. Une vidéo de 5 minutes ne survit que si le début
retient.

- **Ta phrase la plus forte en premier.** Pas d'introduction, pas de
  « salut à tous ». On entre directement dans le sujet.
- **L'intro Mr ZIKA dure 3,5 secondes** et se superpose à la première
  image : elle ne coûte pas de temps de visionnage. Si tu veux quand même
  gagner ces secondes : `./mz brand -i 2`.
- **Ton plan le plus fort en ouverture.** Nomme-le `01-` dans
  `projet/03-broll/`.

---

## 4. Titre, description, hashtags

**Le titre** — une question ou une affirmation qui dérange, moins de 60
caractères :

> Personne ne te le dira, alors je le fais.
> Ce que j'aurais voulu entendre à 20 ans.
> La discipline pèse des grammes.

**Les hashtags** — 4 à 6, jamais plus. Trop de hashtags dilue le
classement. Mélange les échelles :

```
#motivation #discipline #mindset #developpementpersonnel #mrzika
```

Garde **un hashtag qui t'appartient** (`#mrzika`) sur toutes tes vidéos :
il rassemble ton catalogue et permet aux gens de remonter le fil.

**La description** — reprends la phrase la plus marquante de la vidéo. Ça
alimente la recherche et donne envie de commenter.

---

## 5. Rythme de publication

- **Une vidéo par jour** pendant les 30 premiers jours. Le volume compte
  plus que la perfection au départ.
- **Toujours aux mêmes horaires**. Regarde ton onglet Analyses → *Abonnés*
  → *Heures d'activité*.
- **Ne supprime pas une vidéo qui ne marche pas.** Certaines repartent
  plusieurs semaines après. Une suppression, elle, est définitive.

---

## 6. Décliner une vidéo

Le format 5 minutes est fait pour être découpé.

```bash
# 3 extraits courts pris dans la même voix
./mz audio source.mp4 -d 00:00:30 -t 60 -o projet/02-audio/extrait1.wav
./mz build -a projet/02-audio/extrait1.wav -d 60 -p 4 -T flash \
           -o projet/04-rendu/court1.mp4
```

Une session d'écriture peut donc donner : 1 vidéo longue + 3 extraits
courts + 1 version en `noir` pour un autre compte. Cinq publications pour
un seul enregistrement.

---

## 7. Ce qui fait retirer une vidéo

- **Voix ou musique sous droits.** Voir la section 9 du README.
- **Musique commerciale** ajoutée dans le fichier. Utilise la bibliothèque
  de sons TikTok, ou de la musique libre de droits.
- **Images de banques d'images sans vérifier la licence.** Elle change
  parfois d'un fichier à l'autre sur un même site.
- **Flashs trop rapides.** L'option `-T flash` avec `-p` en dessous de 2
  secondes crée un clignotement dangereux pour les personnes
  photosensibles, et TikTok peut restreindre la diffusion. Reste au-dessus
  de 3 secondes par plan avec `flash`.

---

## 8. Liste de contrôle avant publication

- [ ] Regardée en entier **sur un téléphone**, pas sur un écran d'ordinateur
- [ ] Son audible à faible volume, sans saturer au maximum
- [ ] Sous-titres lisibles et bien synchronisés
- [ ] Aucun texte caché derrière l'interface TikTok
- [ ] Les trois premières secondes donnent envie de rester
- [ ] Signature Mr ZIKA visible à la fin
- [ ] Droits vérifiés sur la voix, la musique et les images

---

## 9. Vérifier un fichier avant de le publier

Aucune clé, aucun réseau, aucun coût : le studio lit ton fichier et le
compare aux exigences de la plateforme.

```bash
./mz verifier ma-video.mp4                 # TikTok par défaut
./mz verifier ma-video.mp4 --pour shorts   # YouTube Shorts
./mz specs                                 # toutes les références
./mz specs tiktok                          # une seule plateforme
```

```
  ✔ definition             1080x1920
  ✔ espace couleur         yuv420p                    yuv420p obligatoire
  ✔ faststart              actif                      lecture immediate
  ✔ volume                 -13.8 LUFS                 cible -14
  ✔ crete vraie            -9.2 dBTP                  sous -1,0 dBTP : marge contre AAC

  Conforme. Publiable tel quel sur TikTok.
```

Il renvoie **1** en cas de problème bloquant : tu peux l'enchaîner dans un
script.

### Les trois pièges qu'il attrape

**`yuv444p` au lieu de `yuv420p`.** Le fichier se lit chez toi et reste noir
chez la moitié des gens. C'est l'erreur la plus coûteuse parce qu'elle ne se
voit pas sur ta machine.

**`faststart` absent.** L'index est écrit en fin de fichier : la lecture ne
démarre qu'une fois tout téléchargé. Sur un format où l'on juge en une
seconde, c'est fatal.

**Volume hors cible.** Les plateformes **renormalisent**. Livrer à −9 LUFS ne
rend pas plus fort : elles baissent. Livrer à −20 et elles montent, en
remontant le bruit de fond avec.

### Pourquoi c'est en dur et hors ligne

Ce sont des chiffres fixes et de la géométrie. Les zones d'interface sont des
**fractions de l'image** — elles ne dépendent ni du téléphone ni de la
définition. Le calcul du LUFS est une norme (EBU R128). Rien de tout ça ne
justifie un appel réseau facturé au token.

Les limites des plateformes, elles, bougent. `mz specs` affiche la date de
dernière vérification et le lien officiel : contrôle à la source avant une
grosse production.
