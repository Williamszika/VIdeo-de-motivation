#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — feuilles de prompts par theme

Ecrit, pour chaque theme, une serie de prompts d'image prets a executer
dans un generateur (OpenMontage / FLUX / Imagen / GPT Image / Recraft,
Midjourney, Leonardo…).

Les prompts sont en anglais : tous les modeles d'image sont nettement
meilleurs en anglais, meme pour un contenu francais.

Trois contraintes sont imposees a chaque prompt, parce qu'elles decident
si l'image sera utilisable :
  - cadrage vertical 9:16 ;
  - sujet dans les deux tiers superieurs, bas du cadre sombre et vide —
    c'est la que le studio pose les sous-titres et le filigrane ;
  - aucun texte, aucun logo dans l'image : le studio les ajoute lui-meme.
"""
import argparse, json, math, os, sys

# ------------------------------------------------------------------
#  Lumiere, meteo, palette : dicte par l'ambiance du theme
# ------------------------------------------------------------------
AMBIANCES = {
    "aube_froide": dict(
        lumiere="blue hour before sunrise, cold diffused light, low ground fog",
        palette="desaturated teal and slate grey, pale cold highlights",
        air="thin mist, breath visible in cold air",
        heure="early dawn"),
    "braise": dict(
        lumiere="low ember sunset, strong backlight, hard orange rim light on the subject",
        palette="burning orange and deep crushed browns, near-black shadows",
        air="heavy atmospheric haze, embers and dust floating in the light",
        heure="last minutes before dark"),
    "heure_doree": dict(
        lumiere="golden hour, warm low sun raking across the frame, long soft shadows",
        palette="honey gold and warm amber, lifted milky blacks",
        air="hazy warm air, soft lens bloom",
        heure="one hour before sunset"),
    "nuit_neon": dict(
        lumiere="night, neon signage as the only light source, magenta and cyan spill",
        palette="saturated magenta and electric cyan against deep blue-black",
        air="light rain, wet asphalt reflections, out-of-focus city bokeh",
        heure="late night"),
    "orage": dict(
        lumiere="heavy storm light, a single shaft of sun breaking through the cloud deck",
        palette="cold gunmetal grey and bruised blue, one bright highlight",
        air="wind-driven rain, fast low clouds, spray",
        heure="mid-storm"),
    "sommet": dict(
        lumiere="high altitude light above the cloud layer, clean bright rim light",
        palette="pale blue and brilliant white, vast clean tones",
        air="thin cold air, endless cloud sea below",
        heure="mid morning"),
    "vide": dict(
        lumiere="single soft light source in near darkness, everything else falling away",
        palette="near-monochrome charcoal, one faint warm accent",
        air="dense fog, deep negative space",
        heure="undefined, timeless"),
}

# ------------------------------------------------------------------
#  Archetypes de plan — la variete vient de la, pas du hasard
# ------------------------------------------------------------------
ARCHETYPES = [
    dict(nom="plan large",
         sujet="a vast empty landscape with one tiny human silhouette far away, "
               "dwarfed by the scale of the place",
         cadrage="extreme wide shot, subject small in the upper middle third, "
                 "huge empty sky above"),
    dict(nom="silhouette de dos",
         sujet="a lone person seen from behind, standing still, facing the light, "
               "face never visible",
         cadrage="medium wide shot, subject centred in the upper two thirds, "
                 "strongly backlit so the body reads as a pure silhouette"),
    dict(nom="detail",
         sujet="a close macro detail that carries the whole idea — worn hands, "
               "laced running shoes, a clenched fist, sweat on skin, a chipped mug",
         cadrage="tight macro, very shallow depth of field, the rest of the frame "
                 "falling into dark bokeh"),
    dict(nom="contre-plongee",
         sujet="a steep flight of stairs, a tower, or a mountain wall seen from below, "
               "something that has to be climbed",
         cadrage="low angle looking up, strong converging vertical lines, "
                 "sky filling the top of the frame"),
    dict(nom="point de vue",
         sujet="the road, the path or the horizon straight ahead, exactly as the "
               "walker sees it, nobody else in frame",
         cadrage="eye-level point of view, one-point perspective, vanishing point "
                 "in the upper third"),
    dict(nom="texture",
         sujet="pure atmosphere with no human presence — fog rolling over water, "
               "wind through tall grass, rain on a window, light through dust",
         cadrage="abstract texture filling the frame, no clear subject, "
                 "soft and dark toward the bottom"),
    dict(nom="solitude interieure",
         sujet="an empty room with a single window, one chair, one desk lamp — "
               "somebody has just left, or is about to start",
         cadrage="static interior wide shot, one light source, deep shadow, "
                 "lower half of the frame in darkness"),
    dict(nom="mouvement",
         sujet="a body in motion caught mid-effort — running, climbing, pushing — "
               "seen from the side or behind, face not readable",
         cadrage="side view, motion blur on the limbs, subject sharp, "
                 "slow shutter feel, background streaked"),
]

# ------------------------------------------------------------------
#  Sujets suggeres par le vocabulaire du theme
# ------------------------------------------------------------------
LEXIQUE = [
    (("discipline", "habitude", "routine", "matin", "regulier", "repetition", "reveil"),
     "an alarm clock at 5 am, a made bed in a bare room, running shoes by the door, "
     "an empty gym before anyone arrives"),
    (("peur", "echec", "doute", "rater", "tomber", "erreur", "risque"),
     "a person standing at the edge of a drop, a closed door with light under it, "
     "a single figure facing an oncoming storm"),
    (("entourage", "solitude", "seul", "amis", "gens", "imitation", "compagnie"),
     "one sharp figure standing still while a blurred crowd streams past, "
     "an empty bench, a path splitting in two directions"),
    (("effort", "travail", "sacrifice", "sueur", "force", "combat", "grind"),
     "hands gripping a rope, weights on a chalked floor, an uphill road at dawn, "
     "a desk lamp still on at 3 am"),
    (("temps", "patience", "annees", "jour", "attendre", "long"),
     "a worn wristwatch, a tree standing alone through seasons, "
     "a very long straight road disappearing into haze"),
    (("reussite", "victoire", "sommet", "gagner", "objectif", "reve"),
     "a summit ridge above the cloud line, a horizon opening after a climb, "
     "a silhouette arriving at the top of a long stair"),
    (("argent", "pauvre", "riche", "liberte", "travailler"),
     "glass towers seen from street level at dawn, an empty office corridor, "
     "a worn work jacket on a hook"),
    (("mental", "esprit", "pensee", "croire", "confiance"),
     "a figure reflected in dark water, a window with condensation, "
     "a corridor of light in fog"),
]

SUFFIXE = ("vertical 9:16 composition, cinematic film still, shot on 35mm anamorphic, "
           "shallow depth of field, natural film grain, photorealistic, high detail, 8K")

CONTRAINTE = ("IMPORTANT: subject and horizon placed in the upper two thirds; "
              "the bottom third must stay dark, simple and empty — subtitles and a "
              "signature are composited there. No text, no letters, no watermark, "
              "no logo anywhere in the image.")

NEGATIF = ("text, letters, words, watermark, logo, signature, caption, subtitles, "
           "distorted anatomy, extra limbs, extra fingers, deformed face, "
           "oversaturated, cartoon, illustration, 3d render, cgi, plastic skin, "
           "cluttered composition, busy foreground")


def sans_accents(s):
    s = s.lower().replace("œ", "oe").replace("æ", "ae")
    return s.translate(str.maketrans("àâäéèêëîïôöùûüç", "aaaeeeeiioouuuc"))


def sujets_du_theme(mots_cles, titre, resume):
    """Croise le vocabulaire du theme avec le lexique visuel."""
    blob = sans_accents(" ".join(mots_cles) + " " + (titre or "") + " " + (resume or ""))
    trouves = []
    for cles, sujets in LEXIQUE:
        if any(k in blob for k in cles):
            trouves.append(sujets)
    return trouves


def prompts_theme(theme, n):
    amb = AMBIANCES.get(theme.get("ambiance", "aube_froide"), AMBIANCES["aube_froide"])
    specifiques = sujets_du_theme(theme.get("mots_cles", []),
                                  theme.get("titre", ""), theme.get("resume", ""))
    sortie = []
    for i in range(n):
        a = ARCHETYPES[i % len(ARCHETYPES)]
        sujet = a["sujet"]
        # un plan sur deux s'ancre dans le vocabulaire propre du theme
        if specifiques and i % 2 == 1:
            sujet = specifiques[(i // 2) % len(specifiques)]
        texte = (f"{sujet}. {a['cadrage']}. "
                 f"{amp_maj(amb['lumiere'])}, {amb['air']}, {amb['heure']}. "
                 f"Colour: {amb['palette']}. {SUFFIXE}. {CONTRAINTE}")
        sortie.append({
            "fichier": f"{theme['id']}_{i:02d}.png",
            "archetype": a["nom"],
            "prompt": " ".join(texte.split()),
            "negatif": NEGATIF,
            "format": "9:16",
            "definition": "2160x3840",
        })
    return sortie


def amp_maj(s):
    return s[0].upper() + s[1:] if s else s


def main():
    ap = argparse.ArgumentParser(description="Feuilles de prompts d'images par theme")
    ap.add_argument("--themes", default="projet/themes.json")
    ap.add_argument("--outdir", default="projet/prompts")
    ap.add_argument("--n", type=int, default=14, help="prompts par theme")
    ap.add_argument("--theme", default=None, help="ne traiter qu'un identifiant")
    ap.add_argument("--cible", default="projet/03-broll",
                    help="ou les images devront finir")
    a = ap.parse_args()

    if not os.path.isfile(a.themes):
        sys.exit(f"Introuvable : {a.themes}\n  Produis-le d'abord :  ./mz themes")
    d = json.load(open(a.themes, encoding="utf-8"))
    themes = [t for t in d["themes"] if not a.theme or t["id"] == a.theme]
    if not themes:
        sys.exit(f"Aucun theme « {a.theme} »")

    os.makedirs(a.outdir, exist_ok=True)
    total = 0
    index = []

    for t in themes:
        ps = prompts_theme(t, a.n)
        total += len(ps)
        dest = os.path.join(a.cible, t["id"])
        base = os.path.join(a.outdir, t["id"])

        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump({"theme": t["id"], "titre": t.get("titre", ""),
                       "ambiance": t.get("ambiance", ""),
                       "dossier_cible": dest, "images": ps},
                      f, ensure_ascii=False, indent=1)

        with open(base + ".md", "w", encoding="utf-8") as f:
            f.write(f"# {t.get('titre') or t['id']}\n\n")
            f.write(f"**Ambiance** `{t.get('ambiance','')}`  ·  "
                    f"**Étalonnage** `{t.get('look','')}`  ·  "
                    f"**{len(ps)} images**\n\n")
            if t.get("resume"):
                f.write(f"> {t['resume']}\n\n")
            f.write(f"Les images doivent finir dans `{dest}/`\n\n---\n\n")
            for i, p in enumerate(ps, 1):
                f.write(f"### {i:02d} · {p['archetype']} → `{p['fichier']}`\n\n")
                f.write("```\n" + p["prompt"] + "\n```\n\n")
                f.write("<details><summary>prompt négatif</summary>\n\n```\n"
                        + p["negatif"] + "\n```\n</details>\n\n")
            index.append((t["id"], t.get("titre", ""), len(ps), dest))
        print(f"  {t['id']:<24} {len(ps):3d} prompts  →  {base}.md")

    with open(os.path.join(a.outdir, "LISEZ-MOI.md"), "w", encoding="utf-8") as f:
        f.write("# Prompts d'images — MZ STUDIO\n\n")
        f.write(f"{total} images à générer, {len(index)} thème(s).\n\n")
        f.write("| Thème | Titre | Images | Dossier de destination |\n|---|---|---|---|\n")
        for i, ti, n, dest in index:
            f.write(f"| `{i}` | {ti} | {n} | `{dest}/` |\n")
        f.write("""
## Comment les exécuter

**Avec OpenMontage** — ouvre une session dans ton dossier OpenMontage et demande :

> Génère les images décrites dans `<chemin>/projet/prompts/<theme>.json`.
> Pour chaque entrée : utilise le champ `prompt` et le champ `negatif`, format 9:16,
> et écris le fichier sous le nom donné par `fichier`, dans le dossier `dossier_cible`.

**À la main** (Midjourney, Leonardo, Firefly) — ouvre le `.md` du thème et
copie les blocs un par un. Ajoute `--ar 9:16` sur Midjourney.

## Ensuite

```bash
./mz plans projet/03-broll/<theme>    # vérifier définition et cadrage
./mz serie -S                         # monter sans regénérer de fonds
```

L'option `-S` dit au studio de ne pas fabriquer ses propres fonds et
d'utiliser ce que tu as déposé.

## Ce qui est imposé dans chaque prompt

- **9:16 vertical** — sinon l'image sera recadrée et tu perdras les bords.
- **Sujet dans les deux tiers hauts, bas du cadre sombre et vide** — c'est
  là que tombent les sous-titres (65 % de la hauteur) et le filigrane (77 %).
- **Aucun texte ni logo dans l'image** — le studio les compose lui-même, et
  du texte généré ressort toujours déformé.
""")
    print(f"\n{total} prompts écrits dans {a.outdir}/")
    print(f"Commence par  {a.outdir}/LISEZ-MOI.md")


if __name__ == "__main__":
    main()
