#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — decoupe des themes en videos de 5 minutes

Lit themes.json et transcription.json, puis :
  - coupe chaque theme en parties de 5 minutes maximum ;
  - ecrit pour chaque partie un .srt recale sur zero, tire de la
    transcription mot a mot -> les sous-titres tombent juste ;
  - ecrit plan.tsv, la feuille de route que mz serie execute.

Les coupes tombent sur un silence quand c'est possible : on ne coupe
jamais au milieu d'une phrase.
"""
import argparse, json, math, os, sys

MAX = 300.0            # 5 minutes


def hms(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def court(t):
    return f"{int(t//60):02d}:{int(t%60):02d}"


def coupes_theme(segments, a, b, maxi=MAX, marge=0.05):
    """Decoupe [a,b] en parties egales de 5 minutes maximum.

    On calcule d'abord COMBIEN de parties sont necessaires, puis on vise
    des parties de meme longueur. C'est mieux que de remplir gloutonnement :
    un discours de 11 minutes donne deux parties de 5 min 30 plutot qu'une
    de 5 min et une de 1 min. Chaque borne est ensuite glissee sur le
    silence le plus large a proximite, pour ne jamais couper une phrase.
    """
    total = b - a
    # petite tolerance : un discours de 5 min 10 fait une seule video de
    # 5 min 10, pas deux de 2 min 35. On ne coupe que si ca depasse vraiment.
    n = max(1, math.ceil((total - maxi * 0.08) / maxi))
    cible = total / n
    fenetre = cible * marge

    bornes = [a]
    for k in range(1, n):
        ideal = a + cible * k
        meilleur, meilleur_score = None, -1.0
        for i in range(1, len(segments)):
            t = segments[i]["debut"]
            if ideal - fenetre <= t <= ideal + fenetre:
                silence = t - segments[i - 1]["fin"]
                # on veut un grand silence, et proche de la borne ideale
                score = silence - 0.004 * abs(t - ideal)
                if score > meilleur_score:
                    meilleur, meilleur_score = t, score
        candidat = meilleur if meilleur is not None else ideal
        # jamais au point de faire deborder la partie precedente
        if candidat - bornes[-1] > cible * 1.06:
            candidat = ideal
        bornes.append(candidat)
    bornes.append(b)

    # filet de securite : si une partie deborde encore, on revient a l'egal
    tranches = list(zip(bornes, bornes[1:]))
    if any(y - x > cible * 1.06 for x, y in tranches):
        bornes = [a + cible * k for k in range(n)] + [b]
        tranches = list(zip(bornes, bornes[1:]))
    return tranches


def fusionne(mots):
    """Whisper coupe parfois « n'est » en « n » + « 'est », ou separe un
    trait d'union. On recolle avant de grouper, sinon les sous-titres
    affichent des morceaux de mots."""
    net = []
    for w in mots:
        t = w["mot"].strip()
        if not t:
            continue
        colle = False
        if net:
            prec = net[-1]["mot"].rstrip()
            if t[0] in "'\u2019-" or prec.endswith(("'", "\u2019", "-")):
                colle = True
        if colle:
            net[-1] = {"mot": net[-1]["mot"].rstrip() + t,
                       "debut": net[-1]["debut"], "fin": w["fin"]}
        else:
            net.append({"mot": t, "debut": w["debut"], "fin": w["fin"]})
    return net


def groupes_mots(segments, a, b, par_groupe=3, mini=0.42):
    """Regroupe les mots horodates en petits paquets facon TikTok.
    On coupe sur la ponctuation et tous les `par_groupe` mots, en gardant
    l'horodatage reel de chaque mot : les sous-titres tombent au mot pres."""
    sortie = []
    for s in segments:
        if s["fin"] <= a or s["debut"] >= b:
            continue
        mots = fusionne(s.get("mots") or [])
        if not mots:                                  # secours : segment entier
            sortie.append((s["texte"].strip(), max(s["debut"], a), min(s["fin"], b)))
            continue
        courant = []
        for w in mots:
            if w["fin"] <= a or w["debut"] >= b:
                continue
            courant.append(w)
            ponctue = w["mot"].rstrip().endswith((".", "!", "?", "…", ":", ";"))
            if len(courant) >= par_groupe or ponctue:
                sortie.append((" ".join(x["mot"] for x in courant),
                               courant[0]["debut"], courant[-1]["fin"]))
                courant = []
        if courant:
            sortie.append((" ".join(x["mot"] for x in courant),
                           courant[0]["debut"], courant[-1]["fin"]))

    # duree minimale, et jamais deux groupes qui se chevauchent
    net = []
    for txt, d, f in sortie:
        d = max(d, a); f = min(max(f, d + mini), b)
        if net and d < net[-1][2]:
            d = net[-1][2]
            f = max(f, d + mini)
        if f - d >= 0.12 and txt.strip():
            net.append((txt.strip(), d, f))
    return net


def srt_tranche(segments, a, b, chemin, par_groupe=3):
    """Ecrit les sous-titres de [a,b], remis a zero."""
    lignes = []
    for n, (txt, d, f) in enumerate(groupes_mots(segments, a, b, par_groupe), 1):
        lignes.append(f"{n}\n{hms(d - a)} --> {hms(min(f, b) - a)}\n{txt}\n")
    os.makedirs(os.path.dirname(os.path.abspath(chemin)), exist_ok=True)
    open(chemin, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    return len(lignes)


def texte_tranche(segments, a, b, chemin):
    t = " ".join(s["texte"].strip() for s in segments
                 if s["fin"] > a and s["debut"] < b)
    open(chemin, "w", encoding="utf-8").write(t.strip() + "\n")
    return len(t.split())


def main():
    ap = argparse.ArgumentParser(description="Decoupe les themes en videos de 5 min")
    ap.add_argument("--themes", default="projet/themes.json")
    ap.add_argument("--transcription", default="projet/02-audio/transcription.json")
    ap.add_argument("--outdir", default="projet/parties")
    ap.add_argument("--maxi", type=float, default=MAX)
    ap.add_argument("--mots", type=int, default=3,
                    help="mots par groupe de sous-titres (1 a 5)")
    a = ap.parse_args()

    for f in (a.themes, a.transcription):
        if not os.path.isfile(f):
            sys.exit(f"Introuvable : {f}")

    th = json.load(open(a.themes, encoding="utf-8"))
    tr = json.load(open(a.transcription, encoding="utf-8"))
    segs = tr["segments"]
    source = th.get("source") or tr.get("source", "")

    os.makedirs(a.outdir, exist_ok=True)
    plan = []
    print(f"source : {os.path.basename(source)}\n")

    for t in th["themes"]:
        tid = t["id"]
        d0, d1 = float(t["debut"]), float(t["fin"])
        dossier = os.path.join(a.outdir, tid)
        os.makedirs(dossier, exist_ok=True)
        tranches = coupes_theme(segs, d0, d1, a.maxi)

        titre = t.get("titre") or tid
        print(f"{tid} — {titre}")
        print(f"  {court(d0)} → {court(d1)}  ({(d1-d0)/60:.1f} min)  "
              f"→ {len(tranches)} video(s)")

        for k, (x, y) in enumerate(tranches, 1):
            base = os.path.join(dossier, f"partie-{k:02d}")
            n = srt_tranche(segs, x, y, base + ".srt", max(1, min(6, a.mots)))
            mots = texte_tranche(segs, x, y, base + ".txt")
            plan.append([
                tid, f"{k:02d}", f"{x:.2f}", f"{y-x:.2f}", base + ".srt",
                t.get("ambiance", "aube_froide"), t.get("look", "ice"),
                t.get("palette", "or"), str(t.get("plan_sec", 6)),
                t.get("texture", "normal"), t.get("transition", "coupe"),
                titre.replace("\t", " "),
            ])
            marque = "  (courte)" if y - x < 150 else ""
            print(f"    partie {k:02d} : {court(x)} → {court(y)}  "
                  f"{y-x:6.1f}s · {n:3d} sous-titres · {mots:4d} mots{marque}")
        print()

    tsv = os.path.join(a.outdir, "plan.tsv")
    with open(tsv, "w", encoding="utf-8") as f:
        f.write("#id\tpartie\tdebut\tduree\tsrt\tambiance\tlook\tpalette\tplan_sec\ttexture\ttransition\ttitre\n")
        f.write(f"#source\t{source}\n")
        for r in plan:
            f.write("\t".join(r) + "\n")

    total = sum(float(r[3]) for r in plan)
    print(f"{len(plan)} video(s) a produire, {total/60:.0f} min au total")
    print(f"feuille de route : {tsv}")
    print("\nEtape suivante :  ./mz serie")


if __name__ == "__main__":
    main()
