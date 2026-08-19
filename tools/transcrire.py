#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — ecoute et transcription
Transcrit une video ou un fichier audio avec Whisper, avec horodatage
mot par mot. C'est la base de tout le reste : sous-titres cales au mot,
et decoupage en themes.

Sorties :
  <prefixe>.json   segments + mots horodates (lu par les autres outils)
  <prefixe>.srt    sous-titres standard
  <prefixe>.txt    texte lisible avec minutages, pour relecture
"""
import argparse, json, os, sys, time

MODELES = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]


def hms(t, virgule=","):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", virgule)


def court(t):
    return f"{int(t//60):02d}:{int(t%60):02d}"


def main():
    ap = argparse.ArgumentParser(description="Transcription Whisper avec horodatage mot a mot")
    ap.add_argument("source", help="fichier video ou audio")
    ap.add_argument("--out", default="projet/02-audio/transcription", help="prefixe de sortie")
    ap.add_argument("--modele", default="large-v3-turbo", choices=MODELES)
    ap.add_argument("--langue", default="fr", help="fr, en… ou 'auto'")
    ap.add_argument("--calcul", default="int8", choices=["int8", "int8_float32", "float32"])
    args = ap.parse_args()

    if not os.path.isfile(args.source):
        sys.exit(f"Fichier introuvable : {args.source}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper n'est pas installe.\n  pip install faster-whisper")

    print(f"modele  : {args.modele}  (premier lancement = telechargement)")
    t0 = time.time()
    m = WhisperModel(args.modele, device="cpu", compute_type=args.calcul)
    print(f"charge en {time.time()-t0:.0f}s — transcription en cours…")

    t0 = time.time()
    segs, info = m.transcribe(
        args.source,
        language=None if args.langue == "auto" else args.langue,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5,
        condition_on_previous_text=False,   # evite les boucles sur les longs discours
    )

    donnees = {"source": os.path.abspath(args.source), "langue": info.language,
               "duree": info.duration, "modele": args.modele, "segments": []}

    dernier = 0.0
    for s in segs:
        mots = [{"mot": w.word.strip(), "debut": round(w.start, 3),
                 "fin": round(w.end, 3), "score": round(w.probability, 3)}
                for w in (s.words or [])]
        donnees["segments"].append({
            "debut": round(s.start, 3), "fin": round(s.end, 3),
            "texte": s.text.strip(), "mots": mots})
        if s.end - dernier > 25:                     # signe de vie sur les longs fichiers
            print(f"  … {court(s.end)}")
            dernier = s.end

    calcul = time.time() - t0
    n_seg = len(donnees["segments"])
    n_mots = sum(len(s["mots"]) for s in donnees["segments"])
    if n_seg == 0:
        sys.exit("Aucune parole detectee. Verifie que le fichier contient bien une voix.")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)

    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)

    with open(args.out + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(donnees["segments"], 1):
            f.write(f"{i}\n{hms(s['debut'])} --> {hms(s['fin'])}\n{s['texte']}\n\n")

    # texte lisible : un paragraphe par respiration longue, minutage en marge
    with open(args.out + ".txt", "w", encoding="utf-8") as f:
        f.write(f"# {os.path.basename(args.source)}\n")
        f.write(f"# langue {info.language} · duree {court(info.duration)} · "
                f"{n_mots} mots · modele {args.modele}\n\n")
        prec = None
        for s in donnees["segments"]:
            if prec is not None and s["debut"] - prec > 1.6:
                f.write("\n")
            f.write(f"[{court(s['debut'])}] {s['texte']}\n")
            prec = s["fin"]

    vit = info.duration / calcul if calcul else 0
    print(f"\nlangue    : {info.language} ({info.language_probability:.0%} de certitude)")
    print(f"duree     : {court(info.duration)}")
    print(f"transcrit : {n_seg} segments, {n_mots} mots horodates "
          f"({calcul:.0f}s de calcul, {vit:.1f}x le temps reel)")
    print(f"\n  {args.out}.json   pour les outils")
    print(f"  {args.out}.srt    pour les sous-titres")
    print(f"  {args.out}.txt    a relire")


if __name__ == "__main__":
    main()
