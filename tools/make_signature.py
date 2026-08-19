#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — generateur de signature
Fabrique le logo "Mr ZIKA" en or metallique avec halo, ombre portee
et biseau, comme un calque de texte After Effects.

Sorties (dans assets/brand/) :
  signature_big.png    2000px  — pour la revelation d'intro / outro
  signature_mark.png    720px  — filigrane permanent, discret
  signature_alpha.png  2000px  — masque alpha pur (sert au balayage de lumiere)
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- palettes
PALETTES = {
    "or": [(0.00, (94, 63, 12)), (0.26, (214, 166, 60)), (0.42, (255, 240, 190)),
           (0.52, (247, 214, 116)), (0.72, (150, 103, 26)), (0.88, (226, 183, 88)),
           (1.00, (120, 80, 20))],
    "argent": [(0.00, (78, 84, 92)), (0.28, (188, 196, 206)), (0.44, (255, 255, 255)),
               (0.54, (206, 214, 224)), (0.74, (110, 118, 128)), (0.90, (198, 206, 216)),
               (1.00, (88, 94, 102))],
    "feu": [(0.00, (86, 14, 4)), (0.30, (214, 66, 18)), (0.46, (255, 196, 92)),
            (0.56, (243, 128, 32)), (0.78, (142, 34, 8)), (1.00, (206, 74, 20))],
    "glace": [(0.00, (16, 52, 84)), (0.28, (74, 158, 218)), (0.44, (226, 246, 255)),
              (0.54, (140, 202, 240)), (0.76, (26, 80, 128)), (1.00, (96, 170, 224))],
    "blanc": [(0.00, (224, 224, 224)), (0.45, (255, 255, 255)),
              (0.60, (238, 238, 238)), (1.00, (208, 208, 208))],
}
GLOW_TINT = {"or": (255, 196, 74), "argent": (200, 224, 255), "feu": (255, 110, 30),
             "glace": (110, 200, 255), "blanc": (255, 255, 255)}


def find_font(preferred=None):
    cands = []
    if preferred:
        cands.append(preferred)
    cands += [os.path.join(ROOT, "assets/fonts", f) for f in
              ("Anton-Regular.ttf", "BebasNeue-Regular.ttf", "Oswald-Variable.ttf")]
    cands += ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/System/Library/Fonts/Supplemental/Impact.ttf",
              "C:/Windows/Fonts/impact.ttf"]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    sys.exit("Aucune police trouvee. Lance ./install.sh")


def gradient(size, stops):
    """Degrade vertical lisse a partir de points d'arret."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        prev, nxt = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                prev, nxt = stops[i], stops[i + 1]
                break
        span = max(1e-6, nxt[0] - prev[0])
        k = (t - prev[0]) / span
        k = k * k * (3 - 2 * k)                       # lissage cubique
        px[0, y] = tuple(int(prev[1][j] + (nxt[1][j] - prev[1][j]) * k) for j in range(3))
    return img.resize((w, h), Image.BILINEAR)


def draw_tracked(draw, xy, text, font, tracking, fill=255):
    """Ecrit un texte avec interlettrage (PIL ne le gere pas nativement)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def tracked_width(draw, text, font, tracking):
    if not text:
        return 0
    w = sum(draw.textlength(c, font=font) for c in text)
    return w + tracking * (len(text) - 1)


def build(prefix, name, palette, fontfile, width=2000, pad=90,
          tracking_ratio=0.10, glow=True, rules=True, max_h_ratio=0.30):
    stops = PALETTES.get(palette, PALETTES["or"])
    tint = GLOW_TINT.get(palette, (255, 196, 74))

    # --- dimensionner la police pour que le nom remplisse la largeur utile
    usable = width - pad * 2
    size = 100
    probe = Image.new("L", (10, 10)); pd = ImageDraw.Draw(probe)
    for _ in range(80):
        f = ImageFont.truetype(fontfile, size)
        w = tracked_width(pd, name, f, size * tracking_ratio)
        if w >= usable:
            break
        size = int(size * 1.06) + 1
    # bride la hauteur : une signature doit rester large et basse,
    # sinon les polices condensees (Anton) montent trop haut.
    f = ImageFont.truetype(fontfile, size)
    bb = f.getbbox(name)
    if (bb[3] - bb[1]) > width * max_h_ratio:
        size = max(12, int(size * (width * max_h_ratio) / (bb[3] - bb[1])))

    font_main = ImageFont.truetype(fontfile, size)
    tr_main = size * tracking_ratio
    font_pre = ImageFont.truetype(fontfile, max(12, int(size * 0.34)))
    tr_pre = size * 0.34 * 0.42

    a_main = font_main.getbbox(name)
    h_main = a_main[3] - a_main[1]
    h_pre = 0
    if prefix:
        b = font_pre.getbbox(prefix)
        h_pre = b[3] - b[1]

    gap = int(size * 0.15)
    rule_gap = int(size * 0.15) if rules else 0
    rule_h = max(3, int(size * 0.035)) if rules else 0
    height = pad * 2 + h_pre + gap + h_main + (rule_gap + rule_h if rules else 0)

    # --- masque du texte (canal alpha de reference)
    mask = Image.new("L", (width, height), 0)
    md = ImageDraw.Draw(mask)
    y = pad
    if prefix:
        wpre = tracked_width(md, prefix, font_pre, tr_pre)
        draw_tracked(md, ((width - wpre) / 2, y - font_pre.getbbox(prefix)[1]),
                     prefix, font_pre, tr_pre, 255)
        y += h_pre + gap
    wmain = tracked_width(md, name, font_main, tr_main)
    draw_tracked(md, ((width - wmain) / 2, y - a_main[1]), name, font_main, tr_main, 255)
    y += h_main

    if rules:
        y += rule_gap
        half = wmain / 2
        md.rectangle([ (width/2 - half, y), (width/2 - half + half*0.44, y + rule_h) ], fill=255)
        md.rectangle([ (width/2 + half - half*0.44, y), (width/2 + half, y + rule_h) ], fill=255)
        cx, cy = width/2, y + rule_h/2
        r = rule_h * 1.9
        md.polygon([(cx, cy - r), (cx + r*0.62, cy), (cx, cy + r), (cx - r*0.62, cy)], fill=255)

    # --- corps metallique : degrade masque par le texte
    grad = gradient((width, height), stops).convert("RGBA")
    body = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    body.paste(grad, (0, 0), mask)

    # --- biseau : liseré clair en haut, sombre en bas (relief)
    up = ImageChops.subtract(mask, ImageChops.offset(mask, 0, int(size*0.014)))
    dn = ImageChops.subtract(mask, ImageChops.offset(mask, 0, -int(size*0.014)))
    hi = Image.new("RGBA", (width, height), (255, 252, 232, 255)); hi.putalpha(up.point(lambda v: int(v*0.55)))
    lo = Image.new("RGBA", (width, height), (26, 16, 2, 255));     lo.putalpha(dn.point(lambda v: int(v*0.45)))
    body = Image.alpha_composite(body, hi)
    body = Image.alpha_composite(body, lo)

    # --- contour fin sombre : detache le logo de l'image de fond
    edge = mask.filter(ImageFilter.MaxFilter(5))
    outline = Image.new("RGBA", (width, height), (14, 10, 4, 255))
    outline.putalpha(ImageChops.subtract(edge, mask).point(lambda v: int(v * 0.85)))

    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # --- ombre portee
    sh = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    sh.putalpha(mask.filter(ImageFilter.GaussianBlur(size*0.05)).point(lambda v: int(v*0.62)))
    out = Image.alpha_composite(out, ImageChops.offset(sh, 0, int(size*0.05)))

    # --- halo exterieur (le "Glow" de After Effects)
    if glow:
        for radius, strength in ((size*0.20, 0.30), (size*0.065, 0.52)):
            g = Image.new("RGBA", (width, height), tint + (255,))
            g.putalpha(mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v*strength)))
            out = Image.alpha_composite(out, g)

    out = Image.alpha_composite(out, outline)
    out = Image.alpha_composite(out, body)
    return out, mask



def make_band(w, h, tilt=0.42, sigma_ratio=0.11):
    """Bande de lumiere diagonale (niveaux de gris) — sert au balayage
    facon reflet metallique d'After Effects."""
    x = np.arange(w)[None, :].astype(np.float32)
    y = np.arange(h)[:, None].astype(np.float32)
    d = x + tilt * (y - h / 2.0)
    sig = w * sigma_ratio
    core = np.exp(-((d - w * 0.5) / sig) ** 2)
    halo = np.exp(-((d - w * 0.5) / (sig * 3.2)) ** 2) * 0.35
    v = np.clip((core + halo) * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v]), "RGB")


def main():
    ap = argparse.ArgumentParser(description="Genere la signature Mr ZIKA")
    ap.add_argument("--prefix", default="Mr")
    ap.add_argument("--name", default="ZIKA")
    ap.add_argument("--palette", default="or", choices=list(PALETTES))
    ap.add_argument("--font", default=None)
    ap.add_argument("--outdir", default=os.path.join(ROOT, "assets/brand"))
    ap.add_argument("--width", type=int, default=2000)
    args = ap.parse_args()

    font = find_font(args.font)
    os.makedirs(args.outdir, exist_ok=True)

    big, mask = build(args.prefix, args.name, args.palette, font, width=args.width)
    big.save(os.path.join(args.outdir, "signature_big.png"))

    alpha = Image.new("RGBA", big.size, (255, 255, 255, 0)); alpha.putalpha(mask)
    alpha.save(os.path.join(args.outdir, "signature_alpha.png"))

    bw = max(120, int(big.width * 0.42))
    make_band(bw, big.height).save(os.path.join(args.outdir, "sweep_band.png"))

    mark, _ = build(args.prefix, args.name, args.palette, font, width=720, pad=44,
                    glow=True, rules=True)
    a = mark.getchannel("A").point(lambda v: int(v * 0.80))
    mark.putalpha(a)
    mark.save(os.path.join(args.outdir, "signature_mark.png"))

    print(f"police      : {font}")
    print(f"signature   : {args.prefix} {args.name}  ({args.palette})")
    for f in ("signature_big.png", "signature_alpha.png", "sweep_band.png", "signature_mark.png"):
        p = os.path.join(args.outdir, f)
        im = Image.open(p)
        print(f"  {f:<22} {im.width}x{im.height}")


if __name__ == "__main__":
    main()
