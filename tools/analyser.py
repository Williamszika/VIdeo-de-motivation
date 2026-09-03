#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — analyse d'un rush et proposition de montage

Mesure la nettete image par image (variance du laplacien), repere les
passages exploitables, jette le flou de bouge, et propose une liste de
montage editable a la main.

Trouve aussi ou placer le recadrage vertical : la bande de l'image qui
porte le plus de detail, c'est en general le sujet.

  python3 tools/analyser.py ma-video.mp4
  python3 tools/analyser.py ma-video.mp4 --plan 1.8 --nb 5
"""
import argparse, glob, math, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image


def sonde(v, champ, flux="v:0"):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", flux,
                        "-show_entries", f"stream={champ}", "-of", "csv=p=0", v],
                       capture_output=True, text=True)
    return r.stdout.strip().split("\n")[0]


def duree(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", v], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit("Impossible de lire la duree de " + v)


def nettete(a):
    """Variance du laplacien : plus c'est haut, plus l'image est nette."""
    lap = (-4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1]
           + a[1:-1, :-2] + a[1:-1, 2:])
    return float(lap.var())


def lisse(x, k=3):
    if k < 2 or len(x) < k:
        return x
    noyau = np.ones(k) / k
    return np.convolve(x, noyau, mode="same")


def analyse(video, fps, largeur=240):
    tmp = tempfile.mkdtemp(prefix="mz-analyse-")
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                        "-vf", f"fps={fps},scale={largeur}:-1",
                        os.path.join(tmp, "%05d.png")], check=True)
        fichiers = sorted(glob.glob(os.path.join(tmp, "*.png")))
        if not fichiers:
            sys.exit("Aucune image extraite — le fichier est-il bien une video ?")
        scores, profils = [], []
        for f in fichiers:
            g = np.asarray(Image.open(f).convert("L"), np.float32)
            scores.append(nettete(g))
            # detail par ligne : sert a trouver la bande du sujet
            profils.append(np.abs(np.diff(g, axis=0)).mean(axis=1))
        return np.array(scores), np.array(profils)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bande_du_sujet(profils, h_src, h_cible_ratio):
    """Renvoie le decalage vertical (0..1) ou centrer le recadrage."""
    p = profils.mean(axis=0)
    p = lisse(p, max(3, len(p) // 12))
    n = len(p)
    fen = max(1, int(n * h_cible_ratio))
    if fen >= n:
        return 0.5
    cumul = np.cumsum(np.concatenate([[0.0], p]))
    poids = cumul[fen:] - cumul[:-fen]
    debut = int(np.argmax(poids))
    return (debut + fen / 2) / n


def passages(scores, fps, seuil_ratio, mini_s):
    """Plages contigues au-dessus du seuil, d'au moins mini_s secondes."""
    s = lisse(scores.astype(np.float64), 3)
    s = s / (s.max() or 1.0)
    seuil = max(s.mean() * seuil_ratio, np.percentile(s, 45))
    dedans, plages, debut = False, [], 0
    for i, v in enumerate(s):
        if v >= seuil and not dedans:
            dedans, debut = True, i
        elif v < seuil and dedans:
            dedans = False
            if (i - debut) / fps >= mini_s:
                plages.append((debut / fps, i / fps, float(s[debut:i].mean())))
    if dedans and (len(s) - debut) / fps >= mini_s:
        plages.append((debut / fps, len(s) / fps, float(s[debut:].mean())))
    return plages, s, seuil


def main():
    ap = argparse.ArgumentParser(description="Analyse un rush et propose un montage")
    ap.add_argument("video")
    ap.add_argument("--edl", default=None, help="fichier de montage a ecrire")
    ap.add_argument("--fps", type=float, default=8.0, help="finesse de l'analyse")
    ap.add_argument("--plan", type=float, default=1.7, help="duree visee d'un plan (s)")
    ap.add_argument("--nb", type=int, default=6, help="nombre de plans maximum")
    ap.add_argument("--mini", type=float, default=0.45, help="plage nette minimale (s)")
    ap.add_argument("--seuil", type=float, default=1.0,
                    help="exigence de nettete : 1.0 = la moyenne, 1.3 = severe")
    ap.add_argument("--vitesse-min", type=float, default=0.45)
    ap.add_argument("--vitesse-max", type=float, default=1.15)
    ap.add_argument("--W", type=int, default=1080)
    ap.add_argument("--H", type=int, default=1920)
    ap.add_argument("--muet", action="store_true", help="ne pas afficher le graphique")
    a = ap.parse_args()

    if not os.path.isfile(a.video):
        sys.exit("Introuvable : " + a.video)

    lw, lh = int(sonde(a.video, "width")), int(sonde(a.video, "height"))
    d = duree(a.video)
    scores, profils = analyse(a.video, a.fps)

    print(f"source   : {os.path.basename(a.video)}")
    print(f"format   : {lw}x{lh}  ·  {d:.2f}s  ·  {len(scores)} images analysees")

    # --- definition : previent si l'agrandissement va couter cher
    ratio_src, ratio_cible = lw / lh, a.W / a.H
    if ratio_src <= ratio_cible:
        facteur = a.W / lw
        sens = "largeur"
    else:
        facteur = a.H / lh
        sens = "hauteur"
    print(f"cible    : {a.W}x{a.H}  ->  agrandissement x{facteur:.2f} en {sens}")
    if facteur > 1.6:
        print(f"           ATTENTION : x{facteur:.2f}, l'image sera molle. "
              "C'est la limite de la source, pas du montage.")

    # --- ou recadrer
    if ratio_src <= ratio_cible:          # source plus etroite : on rogne en hauteur
        h_apres = a.W * lh / lw
        garde = a.H / h_apres
        centre = bande_du_sujet(profils, lh, garde)
        # On vise le sujet aux deux cinquiemes de l'image, pas au milieu :
        # en dessous de 65 % de la hauteur il passerait sous les sous-titres.
        y = int(max(0, min(h_apres - a.H, centre * h_apres - a.H * 0.42)))
        pos = (centre * h_apres - y) / a.H
        print(f"recadrage: hauteur {int(h_apres)} -> {a.H}, decalage y={y} "
              f"(sujet a {centre*100:.0f}% de la source, {pos*100:.0f}% du cadre final)")
    else:
        y = 0
        print("recadrage: rognage horizontal, centre")

    # --- passages nets
    plages, s, seuil = passages(scores, a.fps, a.seuil, a.mini)
    if not a.muet:
        print("\n  nettete (# = net, . = flou)")
        for i, v in enumerate(s):
            t = i / a.fps
            if i % max(1, int(a.fps / 4)) == 0:
                marque = "#" * int(v * 40) if v >= seuil else "." * max(1, int(v * 40))
                print(f"  {t:6.2f}s  {marque}")

    if not plages:
        print("\nAucun passage net trouve. Baisse l'exigence :  --seuil 0.8")
        sys.exit(1)

    print(f"\n{len(plages)} passage(s) exploitable(s) :")
    for x, yy, q in plages:
        print(f"  {x:5.2f}s -> {yy:5.2f}s   ({yy-x:4.2f}s, qualite {q:.2f})")

    # --- proposition : on ouvre sur le meilleur passage et on FERME sur le
    #     deuxieme meilleur. Finir sur le plan le plus faible gache la fin.
    tri = sorted(plages, key=lambda p: -p[2])[:a.nb]
    if len(tri) >= 3:
        ordonne = [tri[0]] + sorted(tri[2:], key=lambda p: p[0]) + [tri[1]]
    else:
        ordonne = tri

    lignes = []
    for i, (x, yy, q) in enumerate(ordonne):
        brut = yy - x
        v = brut / a.plan                      # vitesse pour atteindre la duree visee
        v = max(a.vitesse_min, min(a.vitesse_max, v))
        role = ("accroche — le passage le plus net" if i == 0
                else "fermeture" if i == len(ordonne) - 1 else "corps")
        lignes.append((x, brut, v, f"{role} (qualite {q:.2f})"))

    total = sum(b / v for _, b, v, _ in lignes)
    edl = a.edl or os.path.splitext(a.video)[0] + ".edl.tsv"
    with open(edl, "w", encoding="utf-8") as f:
        f.write("# Liste de montage — MZ STUDIO\n")
        f.write(f"# source : {os.path.abspath(a.video)}\n")
        f.write(f"# recadrage vertical conseille : y={y}\n")
        f.write("# vitesse < 1 = ralenti.  Modifie librement, une ligne = un plan.\n")
        f.write("#debut\tduree\tvitesse\tcommentaire\n")
        for x, b, v, c in lignes:
            f.write(f"{x:.2f}\t{b:.2f}\t{v:.2f}\t{c}\n")

    print(f"\nmontage propose : {len(lignes)} plans, {total:.2f}s a l'ecran")
    for x, b, v, c in lignes:
        print(f"  {x:5.2f}s +{b:4.2f}s  x{v:.2f}  ->  {b/v:4.2f}s   {c}")
    print(f"\necrit dans : {edl}")
    print(f"Monte-le :  ./mz montage -i {a.video} -y {y}")


if __name__ == "__main__":
    main()
