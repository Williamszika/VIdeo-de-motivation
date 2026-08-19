#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — decoupage en themes

Deux usages :

  --proposer   analyse la transcription et propose des ruptures de sujet.
               La methode : on compare le vocabulaire de deux fenetres qui
               se suivent ; quand il change franchement, c'est un nouveau
               theme. C'est un point de depart automatique.

  --verifier   controle un themes.json ecrit ou corrige a la main.

Le fichier themes.json pilote ensuite toute la production (mz serie).
"""
import argparse, json, math, os, re, sys
from collections import Counter

# mots trop frequents pour porter du sens
VIDES = set("""
a ai aie ait alors apres as au aucun aussi autre aux avait avant avec avoir
bien c car ce cela ces cet cette ceux chaque chez ci comme comment d dans de
des deja depuis des deux doit donc dont du elle elles en encore es est et eta
etaient etais etait etant ete etre eu eux fait faire fais fait faut il ils j
je jusqu l la le les leur leurs lui m ma mais me meme mes moi mon n ne ni non
nos notre nous on ont ou ou par parce pas peu peut plus pour pourquoi quand
que quel quelle quels qui quoi s sa sans se sera seront ses si sien soit son
sont sous suis sur t ta te tes toi ton tous tout toute toutes tu un une vos
votre vous y etais serait aurait avais avait vais vas va vont fais font
oui deja tres trop bien juste plutot vraiment aussi enfin donc alors voila
ca ça c'est j'ai n'est qu'il qu'elle d'un d'une l'on
""".split())

AMBIANCES_CONNUES = ["aube_froide", "braise", "heure_doree", "nuit_neon",
                     "orage", "sommet", "vide"]
LOOKS_CONNUS = ["orange_teal", "ice", "fire", "gold", "noir", "cyber", "raw"]


def mots_utiles(texte):
    m = re.findall(r"[a-zàâäéèêëîïôöùûüçœ']+", texte.lower())
    return [w.strip("'") for w in m if len(w) > 3 and w not in VIDES]


def cosinus(a, b):
    if not a or not b:
        return 0.0
    communs = set(a) & set(b)
    num = sum(a[k] * b[k] for k in communs)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return num / (na * nb) if na and nb else 0.0


def proposer(donnees, mini=150.0, maxi=1500.0, fenetre=14):
    """Renvoie une liste de bornes (en secondes) ou le sujet change."""
    segs = donnees["segments"]
    if len(segs) < fenetre * 2 + 4:
        return []

    sacs = [Counter(mots_utiles(s["texte"])) for s in segs]

    # similarite entre la fenetre qui precede et celle qui suit chaque jointure
    scores = []
    for i in range(fenetre, len(segs) - fenetre):
        g = Counter()
        d = Counter()
        for j in range(i - fenetre, i):
            g.update(sacs[j])
        for j in range(i, i + fenetre):
            d.update(sacs[j])
        scores.append((i, cosinus(g, d)))
    if not scores:
        return []

    # profondeur d'un creux : combien il descend par rapport a ses sommets
    vals = [v for _, v in scores]
    profondeurs = []
    for k, (i, v) in enumerate(scores):
        g = v
        j = k
        while j > 0 and vals[j - 1] >= vals[j]:
            j -= 1
            g = vals[j]
        d = v
        j = k
        while j < len(vals) - 1 and vals[j + 1] >= vals[j]:
            j += 1
            d = vals[j]
        profondeurs.append((i, (g - v) + (d - v)))

    moy = sum(p for _, p in profondeurs) / len(profondeurs)
    ecart = math.sqrt(sum((p - moy) ** 2 for _, p in profondeurs) / len(profondeurs))
    seuil = moy + ecart * 0.55

    bornes = []
    for i, p in sorted(profondeurs, key=lambda x: -x[1]):
        if p < seuil:
            break
        t = segs[i]["debut"]
        if all(abs(t - b) >= mini for b in bornes):
            bornes.append(t)
    bornes.sort()

    # on coupe aussi les blocs trop longs, au silence le plus large
    final = []
    precedent = 0.0
    for b in bornes + [donnees["duree"]]:
        while b - precedent > maxi:
            cible = precedent + maxi * 0.8
            best, bestgap = None, 0
            for k in range(1, len(segs)):
                t = segs[k]["debut"]
                if precedent + mini < t < b - mini:
                    gap = t - segs[k - 1]["fin"]
                    if abs(t - cible) < maxi * 0.35 and gap > bestgap:
                        best, bestgap = t, gap
            if best is None:
                break
            final.append(best)
            precedent = best
        if b < donnees["duree"]:
            final.append(b)
            precedent = b
    return sorted(set(final))


def extrait(donnees, a, b, n=260):
    t = " ".join(s["texte"] for s in donnees["segments"] if a <= s["debut"] < b)
    return (t[:n] + "…") if len(t) > n else t


def mots_cles(donnees, a, b, n=8):
    c = Counter()
    for s in donnees["segments"]:
        if a <= s["debut"] < b:
            c.update(mots_utiles(s["texte"]))
    return [w for w, _ in c.most_common(n)]


def court(t):
    return f"{int(t//60):02d}:{int(t%60):02d}"


def cmd_proposer(args):
    d = json.load(open(args.transcription, encoding="utf-8"))
    bornes = proposer(d, mini=args.mini, maxi=args.maxi)
    coupes = [0.0] + bornes + [d["duree"]]

    themes = []
    for k in range(len(coupes) - 1):
        a, b = coupes[k], coupes[k + 1]
        if b - a < 30:
            continue
        cles = mots_cles(d, a, b)
        themes.append({
            "id": f"{len(themes)+1:02d}-a-nommer",
            "titre": "",
            "debut": round(a, 2),
            "fin": round(b, 2),
            "resume": extrait(d, a, b),
            "mots_cles": cles,
            "ambiance": "aube_froide",
            "look": "ice",
            "palette": "or",
            "plan_sec": 6,
            "texture": "normal",
            "transition": "fondu",
        })

    sortie = {"source": d.get("source", ""), "duree": d["duree"],
              "langue": d.get("langue", "fr"), "themes": themes}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=1)

    print(f"{len(themes)} blocs proposes  ->  {args.out}\n")
    for t in themes:
        n = max(1, math.ceil((t["fin"] - t["debut"]) / 300))
        print(f"  {t['id']}  {court(t['debut'])} → {court(t['fin'])}  "
              f"({(t['fin']-t['debut'])/60:.1f} min, {n} video(s) de 5 min)")
        print(f"    mots frequents : {', '.join(t['mots_cles'][:6])}")
        print(f"    {t['resume'][:110]}…\n")
    print("Ce decoupage est mecanique : il suit le vocabulaire, pas le sens.")
    print("Relis transcription.txt, puis corrige titres, bornes et ambiances")
    print("dans themes.json. Ensuite :  ./mz serie")


def cmd_verifier(args):
    if not os.path.isfile(args.fichier):
        sys.exit(f"Introuvable : {args.fichier}")
    d = json.load(open(args.fichier, encoding="utf-8"))
    themes = d.get("themes", [])
    if not themes:
        sys.exit("Aucun theme dans le fichier.")

    erreurs, avertis = [], []
    vus = set()
    total_videos = 0
    for i, t in enumerate(themes, 1):
        p = f"theme {i}"
        for champ in ("id", "debut", "fin"):
            if champ not in t:
                erreurs.append(f"{p} : champ « {champ} » manquant")
        if "id" in t:
            if t["id"] in vus:
                erreurs.append(f"{p} : identifiant en double « {t['id']} »")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", str(t["id"])):
                erreurs.append(f"{p} : l'identifiant « {t['id']} » doit rester "
                               "en lettres, chiffres, tiret et souligne")
            vus.add(t["id"])
        if "debut" in t and "fin" in t:
            if t["fin"] <= t["debut"]:
                erreurs.append(f"{p} : fin ({t['fin']}) avant debut ({t['debut']})")
            else:
                duree = t["fin"] - t["debut"]
                n = max(1, math.ceil(duree / 300))
                total_videos += n
                if duree < 60:
                    avertis.append(f"{p} : seulement {duree:.0f}s — un peu court")
                reste = duree - (n - 1) * 300
                if n > 1 and reste < 90:
                    avertis.append(f"{p} : la derniere partie ne fera que "
                                   f"{reste:.0f}s. Deplace la borne ou accepte une video courte.")
        if t.get("ambiance") and t["ambiance"] not in AMBIANCES_CONNUES:
            erreurs.append(f"{p} : ambiance inconnue « {t['ambiance'] }» "
                           f"(connues : {', '.join(AMBIANCES_CONNUES)})")
        if t.get("look") and t["look"] not in LOOKS_CONNUS:
            erreurs.append(f"{p} : etalonnage inconnu « {t['look']} »")
        if not t.get("titre"):
            avertis.append(f"{p} : pas de titre")

    ordre = sorted(themes, key=lambda x: x.get("debut", 0))
    for a, b in zip(ordre, ordre[1:]):
        if b.get("debut", 0) < a.get("fin", 0) - 0.01:
            avertis.append(f"« {a.get('id')} » et « {b.get('id')} » se chevauchent")

    for e in erreurs:
        print(f"  ERREUR       {e}")
    for w in avertis:
        print(f"  attention    {w}")
    if not erreurs:
        print(f"\n  {len(themes)} theme(s) valides  ->  {total_videos} video(s) de 5 min a produire")
    else:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Decoupage en themes")
    ap.add_argument("--proposer", action="store_true")
    ap.add_argument("--verifier", action="store_true")
    ap.add_argument("--transcription", default="projet/02-audio/transcription.json")
    ap.add_argument("--fichier", default="projet/themes.json")
    ap.add_argument("--out", default="projet/themes.json")
    ap.add_argument("--mini", type=float, default=150.0, help="duree minimale d'un theme (s)")
    ap.add_argument("--maxi", type=float, default=1500.0, help="duree maximale d'un theme (s)")
    a = ap.parse_args()
    if a.verifier:
        cmd_verifier(a)
    elif a.proposer:
        cmd_proposer(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
