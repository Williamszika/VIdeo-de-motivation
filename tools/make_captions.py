#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — sous-titres animes facon TikTok
Fabrique un fichier .ass (libass) avec :
  - apparition "pop" elastique sur chaque groupe de mots
  - mot-cle mis en avant en couleur accent (ecris-le *entre asterisques*)
  - gros contour noir : lisible sur n'importe quelle image
  - calage automatique sur la voix (detection des silences) si tu passes --audio

Entrees possibles :
  --text  script.txt   texte brut, reparti automatiquement
  --srt   fichier.srt  sous-titres existants (Whisper, YouTube…)
"""
import argparse, os, re, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ couleurs
def ass_color(hexrgb):
    """#RRGGBB -> &HAABBGGRR (format ASS)"""
    h = hexrgb.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}"


# ------------------------------------------------------------------ decoupage
SENT_END = re.compile(r"(?<=[.!?…:;])\s+")

def chunk_text(text, per_chunk):
    """Coupe le texte en groupes de mots, en respectant la ponctuation."""
    chunks = []
    for para in [p for p in text.split("\n") if p.strip()]:
        for sent in [s for s in SENT_END.split(para.strip()) if s.strip()]:
            words = sent.split()
            i = 0
            while i < len(words):
                take = per_chunk
                # evite d'isoler un mot tout seul en fin de phrase
                if len(words) - i - take == 1:
                    take += 1
                chunks.append(" ".join(words[i:i + take]))
                i += take
    return chunks


def weight(chunk):
    """Poids temporel : nb de caracteres + pause sur la ponctuation."""
    base = len(re.sub(r"[*]", "", chunk))
    pause = 0
    if chunk.rstrip().endswith((".", "!", "?", "…")):
        pause = 9
    elif chunk.rstrip().endswith((",", ";", ":")):
        pause = 4
    return base + pause + 4


# ------------------------------------------------------------------ silences
def speech_segments(audio, noise="-32dB", mind=0.45):
    """Renvoie les plages de parole [(debut, fin)…] via silencedetect."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", audio,
             "-af", f"silencedetect=noise={noise}:d={mind}", "-f", "null", "-"],
            capture_output=True, text=True, timeout=900).stderr
    except Exception:
        return None
    dur = media_duration(audio)
    if not dur:
        return None
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", out)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", out)]
    segs, cur = [], 0.0
    for i, s in enumerate(starts):
        if s > cur + 0.20:
            segs.append((cur, s))
        cur = ends[i] if i < len(ends) else dur
    if dur > cur + 0.20:
        segs.append((cur, dur))
    total = sum(e - s for s, e in segs)
    # si la detection est absurde (moins de 25% de parole), on l'ignore
    if not segs or total < dur * 0.25:
        return None
    return segs


def media_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", path], capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return None


# ------------------------------------------------------------------ timing
def time_chunks(chunks, duration, segments=None, gap=0.06,
                minimum=0.55, maximum=3.2):
    """Attribue (debut, fin) a chaque groupe."""
    w = [weight(c) for c in chunks]
    total_w = sum(w) or 1

    if segments:
        # repartition proportionnelle a l'interieur de chaque plage de parole
        span = sum(e - s for s, e in segments)
        out, qi = [], 0
        for s, e in segments:
            share = (e - s) / span
            n = max(1, round(len(chunks) * share))
            part = chunks[qi:qi + n]
            if not part:
                continue
            qi += n
            pw = [weight(c) for c in part] or [1]
            tw = sum(pw)
            t = s
            for c, cw in zip(part, pw):
                d = max(minimum, (e - s) * cw / tw)
                # le rythme suit la parole, mais un groupe de mots ne reste
                # jamais fige plus de `maximum` : sinon ca donne une video morte
                out.append((c, t, min(e, t + min(d, maximum))))
                t += d
        for c in chunks[qi:]:                      # reliquat
            last = out[-1][2] if out else 0.0
            out.append((c, last, last + minimum))
        return [(c, a, max(a + minimum, b) - gap) for c, a, b in out]

    t, out = 0.0, []
    for c, cw in zip(chunks, w):
        d = min(maximum, max(minimum, duration * cw / total_w))
        out.append((c, t, t + d - gap))
        t += d
    return out


# ------------------------------------------------------------------ ASS
HEADER = """[Script Info]
; Genere par MZ STUDIO — sous-titres motivation
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MZ,{FONT},{SIZE},{PRI},&H000000FF,{OUT},&H96000000,0,0,0,0,100,100,{SPACING},0,1,{BORD},{SHAD},5,{MARGE},{MARGE},0,1
Style: MZB,{FONT},{SIZE},{PRI},&H000000FF,{FOND},&H00000000,0,0,0,0,100,100,{SPACING},0,3,{PAD},0,5,{MARGE},{MARGE},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


# ==================================================================
#  Bibliotheque d'animations de texte
#  Chaque entree reproduit un preset d'After Effects, ecrit en balises
#  ASS : \t() anime une propriete, \clip() masque, \move() deplace,
#  \blur floute, \k cadence le karaoke.
# ==================================================================
DESCRIPTIONS = {
    "pop":      "Rebond elastique — le texte depasse sa taille puis se pose. Le plus sur.",
    "frappe":   "Impact — arrive tres grand et net. Pour les phrases coup de poing.",
    "montee":   "Monte depuis le bas en s'ouvrant. Doux, pour les passages calmes.",
    "cascade":  "Lettre par lettre en decale, avec flou. L'« Animate In » d'After Effects.",
    "machine":  "Machine a ecrire : les lettres apparaissent une par une.",
    "balayage": "Revele par un balayage de gauche a droite, comme un masque anime.",
    "flou":     "Sort du flou en se posant. Tres cinema.",
    "glisse":   "Glisse depuis le cote avec une trainee de flou.",
    "karaoke":  "Chaque mot s'allume a son tour, cale sur le debit.",
    "bloc":     "Un bandeau se deploie, puis le texte apparait dessus.",
    "aucune":   "Aucune animation.",
}


CAL_TEXTE = "La discipline gagne toujours"
CAL_TAILLE = 100
CAL_DEFAUT = 0.60


def facteur_libass(police):
    """libass ne rend pas une police a la meme largeur que Pillow : le
    rapport est constant par police (0,573 pour Anton), mais aucune metrique
    simple ne le predit. On le mesure donc une fois, en rendant reellement
    une image, et on garde le resultat en cache."""
    import json, subprocess, tempfile
    if not police or not os.path.isfile(police):
        return CAL_DEFAUT
    cache = os.path.join(os.path.dirname(police), ".metriques.json")
    cle = os.path.basename(police)
    donnees = {}
    if os.path.isfile(cache):
        try:
            donnees = json.load(open(cache, encoding="utf-8"))
        except Exception:
            donnees = {}
    if cle in donnees:
        return float(donnees[cle])

    famille = os.path.splitext(cle)[0].split("-")[0]
    tmp = tempfile.mkdtemp(prefix="mz-cal-")
    try:
        a = os.path.join(tmp, "c.ass")
        png = os.path.join(tmp, "c.png")
        open(a, "w", encoding="utf-8").write(
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
            "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            f"Style: C,{famille},{CAL_TAILLE},&H00FFFFFF,&H000000FF,&H00000000,"
            "&H96000000,0,0,0,0,100,100,0,0,1,0,0,5,10,10,0,1\n\n[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n"
            "Dialogue: 0,0:00:00.00,0:00:02.00,C,,0,0,0,,"
            "{\\an5\\pos(540,960)}" + CAL_TEXTE + "\n")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "color=c=black:s=1080x1920",
             "-vf", f"subtitles='{a}':fontsdir='{os.path.dirname(police)}'",
             "-frames:v", "1", png],
            check=True, capture_output=True, timeout=120)
        import numpy as np
        from PIL import Image, ImageFont
        im = np.asarray(Image.open(png).convert("L"))
        cols = np.where(im.max(axis=0) > 60)[0]
        if len(cols) < 2:
            return CAL_DEFAUT
        rendu = float(cols.max() - cols.min())
        attendu = ImageFont.truetype(police, CAL_TAILLE).getlength(CAL_TEXTE)
        f = rendu / attendu if attendu else CAL_DEFAUT
        if not (0.2 < f < 2.0):
            return CAL_DEFAUT
        donnees[cle] = round(f, 4)
        try:
            json.dump(donnees, open(cache, "w", encoding="utf-8"), indent=1)
        except Exception:
            pass
        return f
    except Exception:
        return CAL_DEFAUT
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


def mesure(texte, police, taille):
    """Largeur et hauteur du texte TELLES QUE libass va les rendre.
    Sans ca, les bandeaux sont systematiquement trop etroits."""
    try:
        from PIL import ImageFont
        f = ImageFont.truetype(police, taille)
        k = facteur_libass(police)
        return int(f.getlength(texte) * k), int(taille * 0.74)
    except Exception:
        return int(len(texte) * taille * 0.31), int(taille * 0.74)


def jetons(chunk):
    """Decoupe en morceaux (texte, accentue) d'apres les *asterisques*."""
    out, i = [], 0
    for m in re.finditer(r"\*([^*]+)\*", chunk):
        if m.start() > i:
            out.append((chunk[i:m.start()], False))
        out.append((m.group(1), True))
        i = m.end()
    if i < len(chunk):
        out.append((chunk[i:], False))
    return out or [(chunk, False)]


def _couleur(accentue, accent):
    return f"\\c{accent}&" if accentue else "\\c&H00FFFFFF&"


def _corps(toks, accent):
    """Texte simple, avec les mots accentues colores."""
    s = ""
    for t, acc in toks:
        s += "{" + _couleur(acc, accent) + "}" + t
    return s


def _par_caractere(toks, accent, pas, duree, avec_flou):
    """Un bloc de balises par caractere : c'est ce qui produit le decale."""
    s, n = "", 0
    for t, acc in toks:
        for ch in t:
            if ch == " ":
                s += " "
                continue
            d0 = int(n * pas)
            d1 = d0 + duree
            tags = _couleur(acc, accent) + "\\alpha&HFF&"
            if avec_flou:
                tags += "\\blur6"
                s += ("{" + tags + f"\\t({d0},{d1},\\alpha&H00&\\blur0)" + "}") + ch
            else:
                s += ("{" + tags + f"\\t({d0},{d1},\\alpha&H00&)" + "}") + ch
            n += 1
    return s


def construire(nom, toks, a, b, cx, cy, accent, taille, police, W, H,
               fond=False):
    """Renvoie une liste de (couche, debut, fin, style, texte) pour un groupe."""
    plein = "".join(t for t, _ in toks)
    duree_ms = int((b - a) * 1000)
    base = f"\\an5\\pos({cx},{cy})"
    style = "MZB" if fond else "MZ"
    ev = []

    if nom == "frappe":
        tags = base + "\\fscx150\\fscy150\\alpha&HFF&" \
               "\\t(0,70,\\alpha&H00&\\fscx97\\fscy97)\\t(70,150,\\fscx100\\fscy100)"
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "montee":
        tags = (base.replace(f"\\pos({cx},{cy})", "")
                + f"\\move({cx},{cy+80},{cx},{cy},0,200)"
                + "\\alpha&HFF&\\fscx92\\fscy92"
                  "\\t(0,180,\\alpha&H00&\\fscx100\\fscy100)")
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "cascade":
        n = max(1, len(plein.replace(" ", "")))
        pas = min(46, max(14, duree_ms * 0.42 / n))
        ev.append((0, a, b, style, "{" + base + "}" + _par_caractere(toks, accent, pas, 150, True)))

    elif nom == "machine":
        n = max(1, len(plein.replace(" ", "")))
        pas = min(60, max(18, duree_ms * 0.55 / n))
        ev.append((0, a, b, style, "{" + base + "}" + _par_caractere(toks, accent, pas, 1, False)))

    elif nom == "balayage":
        # un masque rectangulaire s'ouvre de la gauche vers la droite
        lw, lh = mesure(plein, police, taille)
        x0, x1 = cx - lw / 2 - 30, cx + lw / 2 + 30
        y0, y1 = cy - lh, cy + lh
        tags = (base + f"\\clip({int(x0)},{int(y0)},{int(x0)},{int(y1)})"
                + f"\\t(0,260,\\clip({int(x0)},{int(y0)},{int(x1)},{int(y1)}))")
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "flou":
        tags = base + "\\blur12\\fscx108\\fscy108\\alpha&H60&" \
               "\\t(0,240,\\blur0\\fscx100\\fscy100\\alpha&H00&)"
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "glisse":
        dx = 220 if int(a * 10) % 2 == 0 else -220
        tags = (base.replace(f"\\pos({cx},{cy})", "")
                + f"\\move({cx+dx},{cy},{cx},{cy},0,220)"
                + "\\alpha&HFF&\\blur9\\t(0,200,\\alpha&H00&\\blur0)")
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "karaoke":
        # \kf remplit chaque mot a son tour ; la duree suit la longueur
        mots = plein.split()
        poids = [max(1, len(m)) for m in mots] or [1]
        total = sum(poids)
        cs = max(1, int((b - a) * 100))
        s = "{" + base + "\\c" + accent + "&\\2c&H00FFFFFF&}"
        pris = 0
        for i, m in enumerate(mots):
            d = int(cs * poids[i] / total) if i < len(mots) - 1 else cs - pris
            pris += d
            s += "{\\kf" + str(max(1, d)) + "}" + m + (" " if i < len(mots) - 1 else "")
        ev.append((0, a, b, style, s))

    elif nom == "bloc":
        # le bandeau est dessine par libass lui-meme (BorderStyle 3) : il epouse
        # donc exactement le texte, quelle que soit la police et la taille.
        style = "MZB"
        tags = (base + "\\fscx40\\fscy88\\alpha&HFF&"
                "\\t(0,150,\\alpha&H00&\\fscx104\\fscy104)"
                "\\t(150,240,\\fscx100\\fscy100)")
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    elif nom == "aucune":
        ev.append((0, a, b, style, "{" + base + "}" + _corps(toks, accent)))

    else:  # pop
        tags = base + "\\fscx58\\fscy58" \
               "\\t(0,90,\\fscx106\\fscy106)\\t(90,170,\\fscx100\\fscy100)"
        ev.append((0, a, b, style, "{" + tags + "}" + _corps(toks, accent)))

    return ev


def parse_srt(path):
    """Lit un .srt (Whisper, YouTube…). Tout ce qui suit la ligne de
    chronometrage, dans le meme bloc, est le texte."""
    out = []
    for blk in re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip()):
        lignes = blk.split("\n")
        idx = next((i for i, l in enumerate(lignes) if TC.search(l)), None)
        if idx is None:
            continue
        g = [int(x) for x in TC.search(lignes[idx]).groups()]
        a = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
        b = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
        body = " ".join(l.strip() for l in lignes[idx + 1:] if l.strip())
        body = re.sub(r"<[^>]+>", "", body).strip()
        if body and b > a:
            out.append((body, a, b))
    return out


def main():
    ap = argparse.ArgumentParser(description="Sous-titres animes TikTok (.ass)")
    src = ap.add_mutually_exclusive_group(required=False)
    src.add_argument("--text", help="fichier texte du script")
    src.add_argument("--srt", help="sous-titres existants (.srt)")
    ap.add_argument("--out", help="fichier .ass a produire")
    ap.add_argument("--audio", help="voix : sert a caler les mots sur la parole")
    ap.add_argument("--duration", type=float, default=300.0)
    ap.add_argument("--words", type=int, default=3, help="mots par groupe (1 a 5)")
    ap.add_argument("--font", default=None)
    ap.add_argument("--size", type=int, default=112)
    ap.add_argument("--accent", default="#FFC845")
    ap.add_argument("--color", default="#FFFFFF")
    ap.add_argument("--outline", default="#0A0A0A")
    ap.add_argument("--bord", type=int, default=9)
    ap.add_argument("--shadow", type=int, default=4)
    ap.add_argument("--spacing", type=int, default=1)
    ap.add_argument("--anim", "--entry", dest="anim", default="pop",
                    choices=list(DESCRIPTIONS),
                    help="animation d'apparition (voir --lister)")
    ap.add_argument("--lister", action="store_true", help="liste les animations")
    ap.add_argument("--fond", nargs="?", const="#0E0E10", default=None,
                    metavar="COULEUR",
                    help="bandeau opaque derriere CHAQUE sous-titre : "
                         "indispensable sur des images chargees")
    ap.add_argument("--fond-alpha", type=int, default=0,
                    help="transparence du bandeau, 0 opaque a 255 invisible. "
                         "Au-dela de 0, les mots colores laissent voir des "
                         "raccords : libass dessine une boite par segment")
    ap.add_argument("--fond-marge", type=int, default=22,
                    help="marge du bandeau autour du texte, en pixels")
    ap.add_argument("--y", type=int, default=1240, help="hauteur du texte (px)")
    ap.add_argument("--marge", type=int, default=86,
                    help="marge laterale : fixe ou le texte passe a la ligne")
    ap.add_argument("--W", type=int, default=1080)
    ap.add_argument("--H", type=int, default=1920)
    args = ap.parse_args()

    if args.lister:
        print("Animations de texte disponibles (option --anim) :\n")
        for k, v in DESCRIPTIONS.items():
            print(f"  {k:10s} {v}")
        return

    fontname = args.font or "Anton"
    if args.font and os.path.isfile(args.font):
        fontname = os.path.splitext(os.path.basename(args.font))[0].split("-")[0]

    if not args.out:
        sys.exit("Il manque --out (ou utilise --lister pour voir les animations).")
    if not args.srt and not args.text:
        sys.exit("Donne --text ou --srt (ou --lister pour voir les animations).")

    if args.srt:
        timed = parse_srt(args.srt)
        if not timed:
            sys.exit("SRT vide ou illisible : " + args.srt)
    else:
        raw = open(args.text, encoding="utf-8-sig").read()
        chunks = chunk_text(raw, max(1, min(6, args.words)))
        if not chunks:
            sys.exit("Le script est vide : " + args.text)
        dur = args.duration
        segs = None
        if args.audio and os.path.isfile(args.audio):
            dur = media_duration(args.audio) or dur
            segs = speech_segments(args.audio)
        timed = time_chunks(chunks, dur, segs)

    accent = ass_color(args.accent)
    fondu_hex = args.fond or "#0E0E10"
    aa = max(0, min(255, args.fond_alpha))
    fond_ass = ass_color(fondu_hex).replace("&H00", f"&H{aa:02X}", 1)
    head = HEADER.format(W=args.W, H=args.H, FONT=fontname, SIZE=args.size,
                         PRI=ass_color(args.color), OUT=ass_color(args.outline),
                         BORD=args.bord, SHAD=args.shadow, SPACING=args.spacing,
                         MARGE=args.marge, FOND=fond_ass, PAD=args.fond_marge)

    police = args.font if (args.font and os.path.isfile(args.font)) else ""
    lines = []
    cx = args.W // 2
    for body, a, b in timed:
        if b <= a:
            b = a + 0.4
        toks = jetons(body.strip())
        for couche, ea, eb, style, txt in construire(
                args.anim, toks, a, b, cx, args.y, accent,
                args.size, police, args.W, args.H, bool(args.fond)):
            lines.append(f"Dialogue: {couche},{ts(ea)},{ts(eb)},{style},,0,0,0,,{txt}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")

    span = timed[-1][2] - timed[0][1] if timed else 0
    affiche = sum(b - a for _, a, b in timed)
    print(f"sous-titres : {args.out}")
    print(f"  {len(timed)} groupes de mots, police {fontname} {args.size}px")
    print(f"  animation : {args.anim} — {DESCRIPTIONS[args.anim]}")
    if args.fond or args.anim == "bloc":
        print(f"  bandeau   : {fondu_hex}, transparence {aa}/255, marge {args.fond_marge}px")
    print(f"  couverture : {span/60:.1f} min" + ("  (cale sur la voix)" if args.audio else ""))

    # un script trop court laisse de longs passages sans texte a l'ecran
    cible = span if args.srt else args.duration
    if cible > 0 and affiche < cible * 0.55:
        mots = sum(len(c.split()) for c, _, _ in timed)
        # un debit parle normal tourne autour de 130 a 150 mots par minute
        bas, haut = int(cible / 60 * 130), int(cible / 60 * 150)
        print(f"  ATTENTION : du texte n'est affiche que {affiche/cible*100:.0f}% du temps.")
        print(f"  Ton script fait {mots} mots. Pour {cible/60:.0f} min de parole,")
        print(f"  ecris ce qui est reellement dit : compte {bas} a {haut} mots.")


if __name__ == "__main__":
    main()
