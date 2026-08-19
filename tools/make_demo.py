#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — plans de demonstration
Fabrique des images de test (silhouettes, ciels, villes) pour valider
toute la chaine sans rien telecharger.
"""
import argparse, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

CIELS = [
    ((14, 22, 46), (196, 108, 62), (250, 196, 120)),    # aube
    ((6, 10, 24), (58, 96, 148), (176, 214, 240)),      # matin froid
    ((28, 12, 8), (168, 52, 24), (250, 168, 72)),       # coucher braise
    ((10, 16, 20), (24, 66, 78), (120, 186, 190)),      # brume
    ((18, 8, 30), (96, 34, 108), (226, 132, 170)),      # crepuscule
    ((4, 6, 10), (30, 34, 48), (110, 124, 150)),        # nuit claire
]


def ciel(w, h, pal, rng):
    haut, milieu, bas = [np.array(c, np.float32) for c in pal]
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = np.where(t < 0.55,
                   haut + (milieu - haut) * (t / 0.55),
                   milieu + (bas - milieu) * ((t - 0.55) / 0.45))
    img = np.repeat(img[:, None, :], w, axis=1) if img.ndim == 2 else np.repeat(img, w, axis=1)
    # halo solaire
    sx, sy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.45, 0.72) * h
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    halo = np.exp(-(d / (w * rng.uniform(0.16, 0.30))) ** 2)[:, :, None]
    img = img + halo * np.array([160, 118, 66], np.float32)
    # nuages : deux octaves larges, puis flou — sinon ca moucheté
    cl = np.zeros((h, w), np.float32)
    for octave, poids in ((120, 0.65), (55, 0.35)):
        small = rng.random((max(2, h // octave), max(2, w // octave))).astype(np.float32)
        up = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        up = up.filter(ImageFilter.GaussianBlur(w / 90.0))
        cl += np.asarray(up, np.float32) / 255.0 * poids
    cl = np.clip((cl - 0.50) * 1.7, 0, 1)[:, :, None]
    img = img * (1 - cl * 0.26) + cl * np.array([214, 208, 202], np.float32) * 0.26
    return np.clip(img, 0, 255)


def montagnes(dr, w, h, rng, n=3):
    for k in range(n):
        base = h * (0.62 + 0.10 * k)
        amp = h * (0.20 - 0.045 * k)
        pts = [(0, h)]
        ph = rng.uniform(0, 6.28)
        for x in range(0, w + 12, 12):
            u = x / w
            y = base - amp * (0.55 * math.sin(u * (2.4 + k) * math.pi + ph)
                              + 0.45 * math.sin(u * (7 + 2 * k) * math.pi + ph * 1.7))
            pts.append((x, y))
        pts.append((w, h))
        g = int(16 + 20 * k)
        dr.polygon(pts, fill=(g, g + 4, g + 10))


def ville(dr, w, h, rng):
    x = 0
    sol = h * 0.86
    while x < w:
        bw = int(rng.uniform(0.035, 0.10) * w)
        bh = int(rng.uniform(0.14, 0.46) * h)
        dr.rectangle([x, sol - bh, x + bw, h], fill=(10, 12, 18))
        for fy in range(int(sol - bh) + 14, int(sol), 26):
            for fx in range(x + 8, x + bw - 8, 20):
                if rng.random() < 0.34:
                    dr.rectangle([fx, fy, fx + 7, fy + 11],
                                 fill=(238, 196, 120) if rng.random() < 0.8 else (150, 190, 230))
        x += bw + int(rng.uniform(0.004, 0.02) * w)


def coureur(dr, w, h, rng):
    """Silhouette humaine simple, de dos, au centre."""
    cx, sol = w * rng.uniform(0.38, 0.62), h * 0.90
    s = h * 0.30
    c = (8, 9, 12)
    dr.ellipse([cx - s*0.11, sol - s*1.00, cx + s*0.11, sol - s*0.78], fill=c)       # tete
    dr.polygon([(cx - s*0.20, sol - s*0.78), (cx + s*0.20, sol - s*0.78),
                (cx + s*0.15, sol - s*0.34), (cx - s*0.15, sol - s*0.34)], fill=c)   # buste
    dr.line([(cx - s*0.16, sol - s*0.70), (cx - s*0.40, sol - s*0.44)], fill=c, width=int(s*0.085))
    dr.line([(cx + s*0.16, sol - s*0.70), (cx + s*0.38, sol - s*0.52)], fill=c, width=int(s*0.085))
    dr.line([(cx - s*0.09, sol - s*0.34), (cx - s*0.22, sol)], fill=c, width=int(s*0.10))
    dr.line([(cx + s*0.09, sol - s*0.34), (cx + s*0.24, sol - s*0.04)], fill=c, width=int(s*0.10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--w", type=int, default=2160)
    ap.add_argument("--h", type=int, default=3840)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    for i in range(a.n):
        rng = np.random.default_rng(1000 + i * 7)
        pal = CIELS[i % len(CIELS)]
        # un plan sur trois est cadre en paysage : teste le recadrage vertical
        w, h = (a.h, a.w) if i % 3 == 2 else (a.w, a.h)
        img = Image.fromarray(ciel(w, h, pal, rng).astype(np.uint8), "RGB")
        dr = ImageDraw.Draw(img)
        motif = i % 3
        if motif == 0:
            montagnes(dr, w, h, rng, n=3)
            if i % 2 == 0:
                coureur(dr, w, h, rng)
        elif motif == 1:
            ville(dr, w, h, rng)
        else:
            montagnes(dr, w, h, rng, n=2)
            coureur(dr, w, h, rng)
        img = img.filter(ImageFilter.GaussianBlur(0.6))
        p = os.path.join(a.outdir, f"plan_{i:02d}.jpg")
        img.save(p, quality=92)
        print(f"  {os.path.basename(p)}  {w}x{h}")


if __name__ == "__main__":
    main()
