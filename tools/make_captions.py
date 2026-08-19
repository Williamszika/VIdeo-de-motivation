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
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MZ,{FONT},{SIZE},{PRI},&H000000FF,{OUT},&H96000000,0,0,0,0,100,100,{SPACING},0,1,{BORD},{SHAD},5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


ENTRIES = {
    # nom       : (tags d'apparition, duree ms)
    "pop":    (r"\fscx58\fscy58\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)", 170),
    "punch":  (r"\fscx135\fscy135\alpha&HFF&\t(0,70,\alpha&H00&\fscx96\fscy96)\t(70,150,\fscx100\fscy100)", 150),
    "montee": (r"\fscx100\fscy100\alpha&HFF&\move($CX,$CY2,$CX,$CY,0,180)\t(0,150,\alpha&H00&)", 180),
    "aucune": (r"", 0),
}


def render_line(chunk, accent, entry, cx, cy, keyword_scale=1.0):
    """Transforme *mot* en mot accentue, et applique l'animation d'entree."""
    tags, _ = ENTRIES.get(entry, ENTRIES["pop"])
    tags = tags.replace("$CX", str(cx)).replace("$CY2", str(cy + 70)).replace("$CY", str(cy))

    def repl(m):
        word = m.group(1)
        # les balises en ligne veulent une couleur fermee par &
        s = f"{{\\c{accent}&"
        if keyword_scale != 1.0:
            s += f"\\fscx{int(100*keyword_scale)}\\fscy{int(100*keyword_scale)}"
        s += "}" + word + "{\\c&H00FFFFFF&"
        if keyword_scale != 1.0:
            s += "\\fscx100\\fscy100"
        s += "}"
        return s

    body = re.sub(r"\*([^*]+)\*", repl, chunk)
    return "{\\an5\\pos(%d,%d)%s}%s" % (cx, cy, tags, body)


TC = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
                r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")


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
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="fichier texte du script")
    src.add_argument("--srt", help="sous-titres existants (.srt)")
    ap.add_argument("--out", required=True, help="fichier .ass a produire")
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
    ap.add_argument("--entry", default="pop", choices=list(ENTRIES))
    ap.add_argument("--y", type=int, default=1240, help="hauteur du texte (px)")
    ap.add_argument("--W", type=int, default=1080)
    ap.add_argument("--H", type=int, default=1920)
    args = ap.parse_args()

    fontname = args.font or "Anton"
    if args.font and os.path.isfile(args.font):
        fontname = os.path.splitext(os.path.basename(args.font))[0].split("-")[0]

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
    head = HEADER.format(W=args.W, H=args.H, FONT=fontname, SIZE=args.size,
                         PRI=ass_color(args.color), OUT=ass_color(args.outline),
                         BORD=args.bord, SHAD=args.shadow, SPACING=args.spacing)

    lines = []
    cx = args.W // 2
    for body, a, b in timed:
        if b <= a:
            b = a + 0.4
        txt = render_line(body.strip(), accent, args.entry, cx, args.y)
        lines.append(f"Dialogue: 0,{ts(a)},{ts(b)},MZ,,0,0,0,,{txt}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(head + "\n".join(lines) + "\n")

    span = timed[-1][2] - timed[0][1] if timed else 0
    affiche = sum(b - a for _, a, b in timed)
    print(f"sous-titres : {args.out}")
    print(f"  {len(timed)} groupes de mots, police {fontname} {args.size}px")
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
