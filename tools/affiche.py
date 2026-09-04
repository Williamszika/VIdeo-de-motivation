#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — affiche

Transforme une photo en visuel vertical 1080x1920 pret a publier :
recadrage, etalonnage, voile degrade, phrase, signature Mr ZIKA.

  python3 tools/affiche.py photo.jpg --haut "ILS VERRONT LE RESULTAT" \
                                     --bas "PAS LES NUITS" --look ice
"""
import argparse, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bash(cmd):
    return subprocess.run(cmd, shell=True, executable="/bin/bash",
                          capture_output=True, text=True).stdout.strip()


def police(nom, taille):
    for f in (nom, os.path.join(RACINE, "assets/fonts", nom),
              os.path.join(RACINE, "assets/fonts/Anton-Regular.ttf"),
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if f and os.path.isfile(f):
            return ImageFont.truetype(f, taille)
    sys.exit("Aucune police trouvee.")


def largeur_espacee(dr, texte, f, espace):
    if not texte:
        return 0
    return sum(dr.textlength(c, font=f) for c in texte) + espace * (len(texte) - 1)


def ecrire_espace(dr, xy, texte, f, espace, fill, contour=0, c_contour=(0, 0, 0)):
    x, y = xy
    for ch in texte:
        if contour:
            dr.text((x, y), ch, font=f, fill=c_contour,
                    stroke_width=contour, stroke_fill=c_contour)
        dr.text((x, y), ch, font=f, fill=fill)
        x += dr.textlength(ch, font=f) + espace


def voile(W, H, jusqu_a, force, depuis_le_haut=True):
    """Degrade sombre : rend le texte lisible sans cacher l'image."""
    g = np.zeros((H, W), np.float32)
    n = max(1, int(H * jusqu_a))
    rampe = np.linspace(force, 0.0, n) ** 1.5
    if depuis_le_haut:
        g[:n] = rampe[:, None]
    else:
        g[H - n:] = rampe[::-1][:, None]
    a = Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8), "L")
    v = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    v.putalpha(a)
    return v


def etalonner(entree, sortie, look, W, H, niveaux, balance, vignettage):
    """Passe par ffmpeg pour reutiliser les etalonnages de lib/grades.sh."""
    grade = bash(f'cd "{RACINE}" && source lib/common.sh && source lib/grades.sh '
                 f'&& mz_grade "{look}"')
    if not grade:
        sys.exit(f"Etalonnage inconnu : {look}")
    chaine = [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
              f"crop={W}:{H}"]
    if niveaux:
        chaine.append(niveaux)
    if balance:
        chaine.append(balance)
    chaine.append(grade)
    if vignettage > 0:
        chaine.append(f"vignette=PI/{vignettage}")
    chaine.append("unsharp=5:5:0.5:5:5:0.0")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", entree,
                        "-vf", ",".join(chaine), "-frames:v", "1", sortie],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Etalonnage impossible :\n" + r.stderr[-400:])


def main():
    ap = argparse.ArgumentParser(description="Photo -> affiche verticale signee")
    ap.add_argument("photo")
    ap.add_argument("--haut", default="", help="petite ligne du dessus")
    ap.add_argument("--bas", default="", help="grande ligne")
    ap.add_argument("--look", default="ice")
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--W", type=int, default=1080)
    ap.add_argument("--H", type=int, default=1920)
    ap.add_argument("--y-haut", type=float, default=0.165, help="hauteur de la petite ligne")
    ap.add_argument("--y-bas", type=float, default=0.225, help="hauteur de la grande ligne")
    ap.add_argument("--taille-haut", type=int, default=46)
    ap.add_argument("--taille-bas", type=int, default=118)
    ap.add_argument("--accent", default="#FFC845")
    ap.add_argument("--voile", type=float, default=0.62, help="force du voile du haut")
    ap.add_argument("--voile-jusqu", type=float, default=0.46)
    ap.add_argument("--voile-bas", type=float, default=0.45)
    ap.add_argument("--vignettage", type=float, default=4.6, help="0 pour aucun")
    ap.add_argument("--niveaux", default="0.043,0.749",
                    help="noir,blanc de la source (0-1) pour etendre les niveaux")
    ap.add_argument("--balance", default="-0.05,0.09",
                    help="correction rouge,bleu de la dominante")
    ap.add_argument("--signature", default="auto")
    ap.add_argument("--grille", action="store_true", help="afficher une grille de reperage")
    a = ap.parse_args()

    if not os.path.isfile(a.photo):
        sys.exit("Photo introuvable : " + a.photo)
    sortie = a.sortie or os.path.splitext(a.photo)[0] + "_affiche.jpg"

    niveaux = ""
    if a.niveaux:
        n, b = [float(x) for x in a.niveaux.split(",")]
        niveaux = f"curves=all='0/0 {n}/0.0 0.40/0.40 {b}/0.955 1/1'"
    balance = ""
    if a.balance:
        r, bl = [float(x) for x in a.balance.split(",")]
        balance = (f"colorbalance=rs={r}:bs={bl}:rm={r*0.9:.3f}:bm={bl*0.6:.3f}"
                   f":rh={r*0.4:.3f}:bh={bl*0.35:.3f}")

    tmp = sortie + ".etalonnee.png"
    etalonner(a.photo, tmp, a.look, a.W, a.H, niveaux, balance, a.vignettage)
    im = Image.open(tmp).convert("RGBA")
    os.remove(tmp)

    W, H = im.size
    im = Image.alpha_composite(im, voile(W, H, a.voile_jusqu, a.voile, True))
    if a.voile_bas > 0:
        im = Image.alpha_composite(im, voile(W, H, 0.22, a.voile_bas, False))

    calque = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(calque)

    # --- petite ligne, largement espacee : ca pose le ton
    if a.haut:
        f = police("Archivo-Variable.ttf", a.taille_haut)
        esp = a.taille_haut * 0.28
        w = largeur_espacee(dr, a.haut, f, esp)
        y = int(H * a.y_haut)
        ecrire_espace(dr, ((W - w) / 2, y), a.haut, f, esp, (236, 240, 246, 236))
        # filet dore sous la ligne
        ry = y + int(a.taille_haut * 1.55)
        acc = tuple(int(a.accent.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        dr.rectangle([W/2 - 46, ry, W/2 + 46, ry + 3], fill=acc + (230,))

    # --- grande ligne, avec mots dores entre *asterisques*
    if a.bas:
        import re
        f = police("Anton-Regular.ttf", a.taille_bas)
        acc = tuple(int(a.accent.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        y = int(H * a.y_bas)
        for ligne in a.bas.split("|"):
            morceaux = []
            for bout in re.split(r"(\*[^*]+\*)", ligne):
                if not bout:
                    continue
                if bout.startswith("*") and bout.endswith("*"):
                    morceaux.append((bout[1:-1], acc + (252,)))
                else:
                    morceaux.append((bout, (255, 255, 255, 252)))
            total = sum(dr.textlength(t, font=f) for t, _ in morceaux)
            x = (W - total) / 2
            for t, couleur in morceaux:
                dr.text((x, y), t, font=f, fill=couleur,
                        stroke_width=max(2, a.taille_bas // 34),
                        stroke_fill=(8, 9, 12, 190))
                x += dr.textlength(t, font=f)
            y += int(a.taille_bas * 1.08)

    im = Image.alpha_composite(im, calque)

    # --- signature
    if a.signature != "non":
        sig = os.path.join(RACINE, "assets/brand/signature_mark.png")
        if os.path.isfile(sig):
            s = Image.open(sig).convert("RGBA")
            lw = int(W * 0.30)
            s = s.resize((lw, int(lw * s.height / s.width)), Image.LANCZOS)
            couche = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            couche.paste(s, ((W - lw) // 2, int(H * 0.855) - s.height // 2), s)
            im = Image.alpha_composite(im, couche)

    if a.grille:
        d2 = ImageDraw.Draw(im)
        for p in range(1, 10):
            d2.line([(0, H * p / 10), (W, H * p / 10)], fill=(255, 0, 0, 150), width=2)
            d2.text((8, H * p / 10 + 4), f"{p*10}%", fill=(255, 60, 60, 255),
                    font=police("Archivo-Variable.ttf", 30))

    im.convert("RGB").save(sortie, quality=95, subsampling=0)
    print(f"affiche : {sortie}")
    print(f"  {W}x{H}  ·  etalonnage {a.look}  ·  {os.path.getsize(sortie)/1e6:.1f} Mo")


if __name__ == "__main__":
    main()
