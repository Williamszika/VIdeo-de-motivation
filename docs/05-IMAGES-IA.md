# Images IA par thème

Le studio rédige un prompt par image — en tenant compte du **sujet du
thème** et de son **ambiance** — puis les exécute chez le fournisseur que tu
as configuré. Sans clé, il fabrique ses propres fonds, gratuitement.

```bash
./mz images -T          # une image, pour vérifier que ta clé marche
./mz images -n 16       # tout générer
```

---

## 1. Choisir un fournisseur

Il suffit d'exporter **une** variable. Le studio prend la première trouvée,
dans cet ordre.

| Variable | Modèle | Prix approximatif | Où prendre la clé |
|---|---|---|---|
| `FAL_KEY` | FLUX 1.1 Ultra | ~0,04 $/image | fal.ai → Keys |
| `REPLICATE_API_TOKEN` | FLUX 1.1 Pro | ~0,04 $/image | replicate.com → Account → API tokens |
| `OPENAI_API_KEY` | GPT Image | ~0,04 $/image | platform.openai.com → API keys |
| `STABILITY_API_KEY` | Stable Diffusion | ~0,03 $/image | platform.stability.ai |
| `MZ_COMFYUI_URL` | ComfyUI en local | gratuit | ta machine, GPU requis |
| *(aucune)* | fonds calculés | gratuit | rien à installer |

```bash
export FAL_KEY="ta-cle-ici"
./mz images -T
```

Pour que ça survive à la fermeture du terminal :

```bash
echo 'export FAL_KEY="ta-cle-ici"' >> ~/.bashrc && source ~/.bashrc
```

**Coût réel** : 3 thèmes × 16 images ≈ 48 images ≈ **2 $**. Les images sont
réutilisables sur toutes les vidéos du même thème, donc c'est un coût unique
par thème, pas par vidéo.

> Vérifie toujours avec `-T` avant de lancer une grosse série. Une clé
> refusée après 40 images, c'est 40 appels payés pour rien.

---

## 2. Avec OpenMontage

OpenMontage génère les images via son outil `image_selector`, piloté par ton
agent — pas par une commande directe. Le studio lui prépare donc le travail :

```bash
./mz prompts -n 16
```

Ça écrit dans `projet/prompts/` :

- `<theme>.json` — la liste machine, avec pour chaque image le `prompt`, le
  `negatif`, le nom de fichier attendu et le dossier de destination ;
- `<theme>.md` — la même chose, lisible, à copier-coller ailleurs ;
- `LISEZ-MOI.md` — le récapitulatif.

Puis, dans ta session OpenMontage :

> Génère les images décrites dans `projet/prompts/01-discipline.json`.
> Pour chaque entrée : utilise le champ `prompt`, applique `negatif` en
> prompt négatif, format 9:16, et écris le fichier sous le nom donné par
> `fichier` dans le dossier indiqué par `dossier_cible`.

Quand c'est fini :

```bash
./mz plans projet/03-broll/01-discipline    # contrôler définition et cadrage
./mz serie -S                               # monter sans refabriquer de fonds
```

---

## 3. Avec ComfyUI en local

Gratuit, mais il faut un GPU. Sur processeur seul, compte 5 à 15 minutes par
image — inutilisable pour une série.

```bash
export MZ_COMFYUI_URL="http://127.0.0.1:8188"
export MZ_COMFYUI_WORKFLOW="$HOME/mon-workflow-api.json"
./mz images -f comfyui -T
```

Dans ComfyUI : **Workflow → Export (API)**. Puis, dans le fichier exporté,
remplace les valeurs à piloter par ces marqueurs :

| Marqueur | Remplacé par |
|---|---|
| `{PROMPT}` | le prompt de l'image |
| `{NEGATIF}` | le prompt négatif |
| `"{W}"` `"{H}"` | la largeur et la hauteur (avec les guillemets) |

---

## 4. Ce que contient chaque prompt

Trois contraintes sont imposées automatiquement, parce qu'elles décident si
l'image sera utilisable sur TikTok :

1. **Cadrage vertical 9:16.** Sinon l'image est recadrée et tu perds les bords.
2. **Sujet dans les deux tiers hauts, bas du cadre sombre et vide.** C'est là
   que tombent les sous-titres (65 % de la hauteur) et le filigrane (77 %).
   Un sujet centré verticalement se retrouve barré par le texte.
3. **Aucun texte ni logo dans l'image.** Le studio compose les siens, et le
   texte généré par un modèle ressort presque toujours déformé.

S'y ajoutent la lumière, la météo et la palette de l'ambiance du thème, plus
un archétype de plan qui tourne d'une image à l'autre : plan large,
silhouette de dos, détail macro, contre-plongée, point de vue, texture,
solitude intérieure, mouvement. C'est cette rotation qui évite que les
seize images d'un thème se ressemblent.

Un plan sur deux s'ancre en plus dans le **vocabulaire propre du thème** :
si tu parles de discipline et de réveil, tu auras un réveil à 5 h et des
chaussures de sport près de la porte.

---

## 5. Mélanger les sources

Rien n'empêche de tout combiner dans le même dossier de thème :

```
projet/03-broll/01-discipline/
  01-discipline_00.jpg      généré par IA
  01-discipline_01.jpg      généré par IA
  aube_froide_00.jpg        fond calculé par le studio
  mes-chaussures.jpg        ta propre photo
  ma-course.mp4             ta propre vidéo
```

Le studio les traite par ordre alphabétique et alterne les mouvements de
caméra. Nomme-les dans l'ordre où tu veux les voir.

---

## 6. Si une image ne va pas

Supprime-la et relance : le studio ne regénère que ce qui manque.

```bash
rm projet/03-broll/01-discipline/01-discipline_04.jpg
./mz images -t 01-discipline
```

Pour tout refaire avec un autre tirage : `./mz images -t 01-discipline -F`

Pour changer la direction artistique d'un thème, modifie son `ambiance` dans
`projet/themes.json`, puis relance avec `-F`. Les prompts sont réécrits.
