#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — generateur de fonds cinematographiques 8K
Compose des images verticales originales (jusqu'a 4320x7680) a partir de
bruit fractal : ciels volumetriques, brume en couches, rayons de lumiere,
cretes de montagne, villes, silhouettes, particules dans la lumiere.

Aucune photo, aucune banque d'images : tout est calcule. Donc aucun
probleme de droits, et une definition libre.

  python3 tools/make_backdrop.py --liste
  python3 tools/make_backdrop.py --ambiance braise --n 6 --outdir projet/03-broll
"""
import argparse, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ============================================================
#  Ambiances — chacune donne une famille d'images coherente
# ============================================================
AMBIANCES = {
    "aube_froide": dict(
        description="Aube froide, brume basse, cretes lointaines. Discipline, solitude, debut.",
        ciel=[(0.00, (10, 16, 34)), (0.42, (34, 58, 96)), (0.70, (108, 150, 186)),
              (1.00, (196, 216, 226))],
        soleil=(236, 240, 236), force_soleil=0.55, hauteur_soleil=(0.60, 0.74),
        brume=(176, 196, 210), densite_brume=0.52,
        motifs=["cretes", "cretes", "cretes_figure", "route"],
        particules=55, teinte_particules=(210, 226, 236), grade="ice"),

    "braise": dict(
        description="Ciel de braise, contre-jour, cendres en suspension. Le grind, l'urgence.",
        ciel=[(0.00, (18, 8, 10)), (0.34, (86, 22, 14)), (0.62, (206, 78, 24)),
              (0.84, (246, 152, 48)), (1.00, (252, 206, 128))],
        soleil=(255, 214, 140), force_soleil=0.92, hauteur_soleil=(0.62, 0.78),
        brume=(220, 130, 70), densite_brume=0.40,
        motifs=["cretes_figure", "ville", "cretes", "route"],
        particules=130, teinte_particules=(255, 190, 110), grade="fire"),

    "heure_doree": dict(
        description="Heure doree, air chaud, lumiere rasante. Gratitude, apaisement, victoire.",
        ciel=[(0.00, (20, 26, 52)), (0.36, (104, 82, 96)), (0.64, (216, 150, 96)),
              (0.86, (248, 202, 128)), (1.00, (254, 236, 196))],
        soleil=(255, 236, 190), force_soleil=0.80, hauteur_soleil=(0.64, 0.80),
        brume=(232, 190, 146), densite_brume=0.46,
        motifs=["cretes", "cretes_figure", "mer", "route"],
        particules=80, teinte_particules=(255, 224, 168), grade="gold"),

    "nuit_neon": dict(
        description="Ville de nuit, halos magenta et cyan. Jeunesse, insomnie, ambition.",
        ciel=[(0.00, (6, 6, 20)), (0.40, (24, 16, 54)), (0.72, (74, 34, 96)),
              (1.00, (140, 78, 148))],
        soleil=(190, 120, 230), force_soleil=0.42, hauteur_soleil=(0.70, 0.84),
        brume=(96, 70, 140), densite_brume=0.44,
        motifs=["ville", "ville", "ville_figure", "route"],
        particules=120, teinte_particules=(170, 210, 255), grade="cyber"),

    "orage": dict(
        description="Ciel d'orage, masses lourdes, lumiere qui perce. Adversite, colere, epreuve.",
        ciel=[(0.00, (16, 19, 26)), (0.36, (52, 60, 74)), (0.62, (116, 128, 146)),
              (0.82, (176, 186, 200)), (1.00, (206, 214, 224))],
        soleil=(238, 242, 248), force_soleil=0.66, hauteur_soleil=(0.58, 0.72),
        brume=(152, 162, 176), densite_brume=0.62,
        motifs=["cretes", "cretes_figure", "mer", "cretes"],
        particules=45, teinte_particules=(200, 210, 220), grade="ice"),

    "sommet": dict(
        description="Au-dessus des nuages, air rare, horizon degage. Reussite, recul, clarte.",
        ciel=[(0.00, (14, 26, 62)), (0.34, (44, 88, 146)), (0.64, (128, 176, 214)),
              (0.88, (216, 232, 242)), (1.00, (246, 250, 252))],
        soleil=(255, 250, 234), force_soleil=0.70, hauteur_soleil=(0.66, 0.80),
        brume=(226, 238, 246), densite_brume=0.78,
        motifs=["cretes_figure", "cretes", "cretes", "cretes_figure"],
        particules=110, teinte_particules=(240, 248, 255), grade="orange_teal"),

    "vide": dict(
        description="Presque rien : brume, une ligne, du silence. Pour laisser parler le texte.",
        ciel=[(0.00, (12, 13, 16)), (0.50, (28, 30, 36)), (1.00, (58, 62, 70))],
        soleil=(180, 186, 196), force_soleil=0.30, hauteur_soleil=(0.50, 0.66),
        brume=(70, 76, 86), densite_brume=0.62,
        motifs=["vide", "vide_figure", "cretes", "vide"],
        particules=40, teinte_particules=(190, 198, 210), grade="noir"),
}


# ============================================================
#  Bruit fractal — la base de tout ce qui est organique
# ============================================================
def _bruit(h, w, freq, rng):
    """Bruit de valeur interpole : une grille aleatoire agrandie en douceur."""
    f = max(2, int(freq))
    g = (rng.random((f + 1, f + 1)) * 255).astype(np.uint8)
    return np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), np.float32) / 255.0


def fbm(h, w, rng, octaves=5, base=3.0, gain=0.52, lacunarite=2.1):
    """Somme d'octaves : donne des nuages et de la brume credibles."""
    total = np.zeros((h, w), np.float32)
    amp, norme, f = 1.0, 0.0, base
    for _ in range(octaves):
        total += _bruit(h, w, f, rng) * amp
        norme += amp
        amp *= gain
        f *= lacunarite
    return total / norme


def ligne_fbm(n, rng, octaves=6, base=2.0, gain=0.5, ridged=False):
    """fBm a une dimension : sert de ligne d'horizon / de crete.
    ridged=True replie le bruit sur lui-meme : on obtient des sommets
    pointus et des vallees marquees, au lieu de collines molles."""
    total = np.zeros(n, np.float32)
    amp, norme, f = 1.0, 0.0, base
    for _ in range(octaves):
        k = max(2, int(f))
        g = rng.random(k + 1).astype(np.float32)
        x = np.linspace(0, k, n)
        i = np.clip(x.astype(int), 0, k - 1)
        t = x - i
        t = t * t * (3 - 2 * t)                     # lissage
        v = g[i] * (1 - t) + g[i + 1] * t
        if ridged:
            v = 1.0 - np.abs(2.0 * v - 1.0)
        total += v * amp
        norme += amp
        amp *= gain
        f *= 2.0
    return total / norme


# ============================================================
#  Couches de l'image
# ============================================================
def degrade_ciel(h, w, stops):
    t = np.linspace(0, 1, h, dtype=np.float32)
    col = np.zeros((h, 3), np.float32)
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        m = (t >= a) & (t <= b)
        if not m.any():
            continue
        k = ((t[m] - a) / max(1e-6, b - a))[:, None]
        k = k * k * (3 - 2 * k)
        col[m] = np.array(ca, np.float32) * (1 - k) + np.array(cb, np.float32) * k
    return np.repeat(col[:, None, :], w, axis=1)


def halo_soleil(img, sx, sy, couleur, force, rayon):
    h, w = img.shape[:2]
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    coeur = np.exp(-(d / (rayon * 0.30)) ** 2)
    large = np.exp(-(d / rayon) ** 2) * 0.55
    m = np.clip(coeur + large, 0, 1)[:, :, None] * force
    return img + m * np.array(couleur, np.float32)


def rayons_lumiere(img, sx, sy, force):
    """Rayons volumetriques : on etire les zones claires depuis le soleil.
    Calcule en basse definition puis agrandi — les rayons sont doux."""
    h, w = img.shape[:2]
    pw, ph = 360, int(360 * h / w)
    petit = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
                       .resize((pw, ph), Image.BILINEAR), np.float32) / 255.0
    lum = petit.mean(axis=2)
    lum = np.clip((lum - 0.46) / 0.54, 0, 1) ** 1.4
    px, py = sx * pw / w, sy * ph / h

    acc = np.zeros_like(lum)
    poids, decroissance = 1.0, 0.93
    base = Image.fromarray((lum * 255).astype(np.uint8))
    for i in range(1, 22):
        s = 1.0 - i * 0.016
        nw, nh = max(2, int(pw * s)), max(2, int(ph * s))
        ech = np.asarray(base.resize((nw, nh), Image.BILINEAR), np.float32) / 255.0
        ox = int(px - px * s)
        oy = int(py - py * s)
        cible = np.zeros_like(acc)
        x0, y0 = max(0, ox), max(0, oy)
        x1, y1 = min(pw, ox + nw), min(ph, oy + nh)
        if x1 > x0 and y1 > y0:
            cible[y0:y1, x0:x1] = ech[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        acc += cible * poids
        poids *= decroissance
    acc /= max(1e-6, acc.max())
    acc = np.asarray(Image.fromarray((acc * 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(6))
                     .resize((w, h), Image.BICUBIC), np.float32) / 255.0
    return img + acc[:, :, None] * np.array([255, 240, 210], np.float32) * force


def couche_brume(img, rng, couleur, densite, hauteur=0.55):
    h, w = img.shape[:2]
    n = fbm(h // 4, w // 4, rng, octaves=5, base=2.5)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                   np.float32) / 255.0
    # la brume s'accumule vers le bas de l'image
    vert = np.clip((np.linspace(0, 1, h, dtype=np.float32) - hauteur) / (1 - hauteur), 0, 1)
    m = (np.clip((n - 0.34) * 1.7, 0, 1) * vert[:, None] * densite)[:, :, None]
    return img * (1 - m) + m * np.array(couleur, np.float32)


def dessine_cretes(img, rng, n_couches, base_couleur, sol=0.90):
    """Cretes en couches, du plus loin au plus proche. Entre chaque plan on
    passe un voile de brume : c'est ce voile — pas la couleur — qui cree la
    sensation de distance. C'est la perspective atmospherique des peintres."""
    h, w = img.shape[:2]
    brume = np.array(base_couleur, np.float32)
    for k in range(n_couches):
        prof = k / max(1, n_couches - 1)                 # 0 = loin, 1 = proche
        if k > 0:
            # tout ce qui est deja peint recule d'un cran
            voile = 0.30 * (1.0 - prof) + 0.07
            img = img * (1 - voile) + voile * brume
        ligne = ligne_fbm(w, rng, octaves=8, base=1.4 + k * 1.1,
                          gain=0.56, ridged=True)
        hauteur = (sol - 0.32) + 0.17 * prof
        amp = 0.19 - 0.060 * prof
        y = (hauteur - ligne * amp) * h
        yy = np.arange(h, dtype=np.float32)[:, None]
        masque = (yy >= y[None, :]).astype(np.float32)
        masque = np.asarray(Image.fromarray((masque * 255).astype(np.uint8))
                            .filter(ImageFilter.GaussianBlur(max(0.6, h / 2400))),
                            np.float32) / 255.0
        obscurite = 0.34 + 0.54 * prof
        couche = brume * (1 - obscurite)
        # un peu de matiere dans les masses sombres : sans ca le bas de
        # l'image devient un aplat noir mort
        if prof > 0.5:
            grain = fbm(max(8, h // 12), max(8, w // 12), rng, octaves=4, base=3.0)
            grain = np.asarray(Image.fromarray((grain * 255).astype(np.uint8))
                               .resize((w, h), Image.BICUBIC), np.float32) / 255.0
            couche = couche[None, None, :] * (0.86 + 0.28 * grain[:, :, None])
            m = masque[:, :, None]
            img = img * (1 - m) + m * couche
        else:
            m = masque[:, :, None]
            img = img * (1 - m) + m * couche
    return img


def dessine_ville(img, rng, sol=0.88):
    h, w = img.shape[:2]
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for couche, (obsc, ech) in enumerate(((0.55, 0.34), (0.78, 0.46), (0.94, 0.62))):
        x = -int(w * 0.05)
        base = h * (sol - 0.03 + 0.02 * couche)
        c = int(255 * (1 - obsc))
        while x < w:
            bw = int(rng.uniform(0.03, 0.085) * w)
            bh = int(rng.uniform(0.16, 0.52) * ech * h)
            dr.rectangle([x, base - bh, x + bw, h], fill=(c, c + 3, c + 9, 255))
            if couche >= 1:                       # fenetres allumees
                pas_y = max(10, int(h * 0.011))
                pas_x = max(8, int(w * 0.011))
                for fy in range(int(base - bh) + pas_y, int(base), pas_y * 2):
                    for fx in range(x + pas_x, x + bw - pas_x, pas_x * 2):
                        if rng.random() < 0.30:
                            t = (250, 206, 130) if rng.random() < 0.78 else (150, 196, 240)
                            dr.rectangle([fx, fy, fx + pas_x // 2, fy + pas_y], fill=t + (255,))
            x += bw + int(rng.uniform(0.002, 0.012) * w)
    a = np.asarray(ov, np.float32) / 255.0
    return img * (1 - a[:, :, 3:4]) + a[:, :, :3] * 255.0 * a[:, :, 3:4]


def dessine_figure(img, rng, sol=0.90):
    """Silhouette humaine, de dos, petite dans le cadre. Donne l'echelle."""
    h, w = img.shape[:2]
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    cx = w * rng.uniform(0.34, 0.66)
    base = h * sol
    s = h * rng.uniform(0.085, 0.125)
    c = (6, 7, 10, 255)
    lw = max(2, int(s * 0.10))
    dr.ellipse([cx - s*0.115, base - s*1.00, cx + s*0.115, base - s*0.775], fill=c)
    dr.polygon([(cx - s*0.185, base - s*0.775), (cx + s*0.185, base - s*0.775),
                (cx + s*0.140, base - s*0.345), (cx - s*0.140, base - s*0.345)], fill=c)
    dr.line([(cx - s*0.155, base - s*0.70), (cx - s*0.355, base - s*0.40)], fill=c, width=lw)
    dr.line([(cx + s*0.155, base - s*0.70), (cx + s*0.335, base - s*0.50)], fill=c, width=lw)
    dr.line([(cx - s*0.085, base - s*0.345), (cx - s*0.195, base)], fill=c, width=int(lw*1.25))
    dr.line([(cx + s*0.085, base - s*0.345), (cx + s*0.215, base - s*0.03)], fill=c, width=int(lw*1.25))
    ov = ov.filter(ImageFilter.GaussianBlur(max(1, h / 2600)))
    a = np.asarray(ov, np.float32) / 255.0
    return img * (1 - a[:, :, 3:4]) + a[:, :, :3] * 255.0 * a[:, :, 3:4]


def dessine_route(img, rng):
    """Perspective : une route file vers le point de fuite."""
    h, w = img.shape[:2]
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    fy = h * rng.uniform(0.60, 0.68)
    fx = w * rng.uniform(0.42, 0.58)
    demi = w * rng.uniform(0.62, 0.85)
    dr.polygon([(fx, fy), (fx - demi, h), (fx + demi, h)], fill=(12, 13, 16, 255))
    n = 9
    for i in range(n):                       # bandes centrales qui s'espacent
        t0 = (i / n) ** 1.9
        t1 = ((i + 0.42) / n) ** 1.9
        y0, y1 = fy + (h - fy) * t0, fy + (h - fy) * t1
        l0, l1 = w * 0.004 + w * 0.020 * t0, w * 0.004 + w * 0.020 * t1
        x0 = fx + (0) * t0
        dr.polygon([(x0 - l0, y0), (x0 + l0, y0), (x0 + l1, y1), (x0 - l1, y1)],
                   fill=(210, 200, 176, 190))
    ov = ov.filter(ImageFilter.GaussianBlur(max(1, h / 2200)))
    a = np.asarray(ov, np.float32) / 255.0
    return img * (1 - a[:, :, 3:4]) + a[:, :, :3] * 255.0 * a[:, :, 3:4]


def dessine_mer(img, rng, sx, couleur_lumiere, horizon=0.58):
    """Surface d'eau vue de biais. Deux choses la rendent credible :
    des rides tres etirees horizontalement (des lignes, pas des taches),
    resserrees vers l'horizon par la perspective ; et le chemin de lumiere
    qui s'elargit en venant vers l'observateur."""
    h, w = img.shape[:2]
    hy = int(h * horizon)
    hh = h - hy
    eau = img[hy:].copy() * 0.30

    # texture de rides : grille tres anisotrope -> des lignes horizontales
    ht = 512
    def bande(gy, gx):
        g = (rng.random((gy + 1, gx + 1)) * 255).astype(np.uint8)
        return np.asarray(Image.fromarray(g).resize((w, ht), Image.BICUBIC), np.float32) / 255.0
    tex = bande(150, 6) * 0.62 + bande(430, 14) * 0.38

    # perspective : v varie vite pres de l'horizon, lentement au premier plan
    yl = np.linspace(0.0, 1.0, hh, dtype=np.float32)
    v = 1.0 / (yl + 0.045)
    v = (v.max() - v) / (v.max() - v.min())
    idx = np.clip((v * (ht - 1) * 2.4).astype(int) % ht, 0, ht - 1)
    rides = tex[idx]

    amp = (0.30 + 2.8 * yl)[:, None]
    rides = np.clip((rides - 0.53) * amp, 0, 1)

    # chemin de lumiere sous le soleil
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    largeur = (0.028 + 0.27 * yl)[:, None]
    chemin = np.exp(-((xx - sx / w) / largeur) ** 2)

    eclat = (rides * (0.10 + 1.30 * chemin))[:, :, None]
    eau = eau + eclat * np.array(couleur_lumiere, np.float32)
    eau[:max(2, hh // 260)] += 55.0                      # ligne d'horizon nette
    img[hy:] = np.clip(eau, 0, 255)
    return img


def particules(img, rng, n, teinte, sx, sy):
    """Poussiere en suspension qui accroche la lumiere, plus dense pres du soleil."""
    h, w = img.shape[:2]
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    for _ in range(n):
        if rng.random() < 0.88:                             # serrees autour du soleil
            x = np.clip(rng.normal(sx, w * 0.17), 0, w)
            y = np.clip(rng.normal(sy, h * 0.10), 0, h)
        else:
            x, y = rng.uniform(0, w), rng.uniform(0, h * 0.88)
        # la poussiere ne brille que si elle est dans la lumiere
        d = math.hypot(x - sx, y - sy) / (w * 0.55)
        eclat = math.exp(-d * d)
        if eclat < 0.05:
            continue
        r = rng.uniform(h * 0.0004, h * 0.0016)
        a = int(rng.uniform(25, 110) * eclat)
        if a < 8:
            continue
        dr.ellipse([x - r, y - r, x + r, y + r], fill=tuple(teinte) + (a,))
    ov = ov.filter(ImageFilter.GaussianBlur(max(1.2, h / 2000)))
    a = np.asarray(ov, np.float32) / 255.0
    return img + a[:, :, :3] * 255.0 * a[:, :, 3:4]          # ajout lumineux


def finition(img, rng, grain=2.2):
    h, w = img.shape[:2]
    yy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    vig = np.clip(1.0 - 0.34 * (xx ** 2 + yy ** 2 * 0.72), 0, 1)[:, :, None]
    img = img * vig
    if grain > 0:
        img = img + rng.normal(0, grain, (h, w, 1)).astype(np.float32)
    return np.clip(img, 0, 255)


# ============================================================
#  Composition
# ============================================================
def generer(nom_ambiance, seed, w, h, motif=None):
    a = AMBIANCES[nom_ambiance]
    rng = np.random.default_rng(seed)

    sx = w * rng.uniform(0.24, 0.76)
    sy = h * rng.uniform(*a["hauteur_soleil"])

    img = degrade_ciel(h, w, a["ciel"])

    # nuages dans le ciel
    n = fbm(h // 5, w // 5, rng, octaves=6, base=2.0)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                   np.float32) / 255.0
    haut = np.clip(1.0 - np.linspace(0, 1, h, dtype=np.float32) / 0.75, 0, 1)
    nuage = (np.clip((n - 0.46) * 1.9, 0, 1) * haut[:, None] * 0.42)[:, :, None]
    img = img * (1 - nuage) + nuage * np.array(a["brume"], np.float32) * 1.15

    img = halo_soleil(img, sx, sy, a["soleil"], a["force_soleil"], w * 0.42)

    motif = motif or a["motifs"][int(rng.integers(0, len(a["motifs"])))]
    if motif.startswith("cretes"):
        img = dessine_cretes(img, rng, 4, a["brume"])
    elif motif.startswith("ville"):
        img = dessine_ville(img, rng)
    elif motif == "route":
        img = dessine_cretes(img, rng, 2, a["brume"], sol=0.72)
        img = dessine_route(img, rng)
    elif motif == "mer":
        img = dessine_mer(img, rng, sx, a["soleil"])
    # "vide" : rien de plus que le ciel et la brume

    img = couche_brume(img, rng, a["brume"], a["densite_brume"])
    img = rayons_lumiere(img, sx, sy, a["force_soleil"] * 0.72)

    if motif.endswith("figure"):
        sol = 0.955 if motif == "vide_figure" else 0.90
        img = dessine_figure(img, rng, sol=sol)

    img = particules(img, rng, a["particules"], a["teinte_particules"], sx, sy)
    img = finition(img, rng)
    return Image.fromarray(img.astype(np.uint8), "RGB"), motif


def main():
    ap = argparse.ArgumentParser(description="Fonds cinematographiques generes")
    ap.add_argument("--ambiance", default="aube_froide")
    ap.add_argument("--n", type=int, default=6, help="nombre d'images")
    ap.add_argument("--outdir", default="projet/03-broll")
    ap.add_argument("--prefixe", default=None)
    ap.add_argument("--w", type=int, default=2160, help="largeur (4320 = classe 8K)")
    ap.add_argument("--h", type=int, default=3840, help="hauteur")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--motif", default=None,
                    help="cretes, cretes_figure, ville, ville_figure, route, mer, vide, vide_figure")
    ap.add_argument("--qualite", type=int, default=95)
    ap.add_argument("--liste", action="store_true")
    args = ap.parse_args()

    if args.liste:
        print("Ambiances disponibles :\n")
        for k, v in AMBIANCES.items():
            print(f"  {k:14s} {v['description']}")
            print(f"  {'':14s} etalonnage conseille : {v['grade']}\n")
        return

    if args.ambiance not in AMBIANCES:
        sys.exit(f"Ambiance inconnue : {args.ambiance}\n  connues : {', '.join(AMBIANCES)}")

    os.makedirs(args.outdir, exist_ok=True)
    pre = args.prefixe or args.ambiance
    px = args.w * args.h / 1e6
    print(f"ambiance : {args.ambiance} — {AMBIANCES[args.ambiance]['description']}")
    print(f"format   : {args.w}x{args.h}  ({px:.0f} Mpx)\n")

    for i in range(args.n):
        im, motif = generer(args.ambiance, args.seed + i * 977 + 13, args.w, args.h, args.motif)
        p = os.path.join(args.outdir, f"{pre}_{i:02d}.jpg")
        im.save(p, quality=args.qualite, subsampling=0)
        print(f"  {os.path.basename(p):<28} {motif:<14} {os.path.getsize(p)/1e6:.1f} Mo")


if __name__ == "__main__":
    main()
