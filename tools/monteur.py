#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — le monteur

Lit un fichier de projet et fabrique la video. Tout est decrit dedans :
les plans, leur ordre, leur duree, leur vitesse, l'etalonnage, les
raccords, les textes, le son, la signature. Tu edites le fichier, tu
relances, tu obtiens ta video.

  python3 tools/monteur.py --nouveau projet/ma-video.yml
  python3 tools/monteur.py -f projet/ma-video.yml
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "tools"))

# ------------------------------------------------------------------ couleurs
def _tty():
    return sys.stdout.isatty()
C_B = "\033[36m" if _tty() else ""
C_G = "\033[32m" if _tty() else ""
C_Y = "\033[33m" if _tty() else ""
C_R = "\033[31m" if _tty() else ""
C_D = "\033[2m" if _tty() else ""
C_S = "\033[1m" if _tty() else ""
C_0 = "\033[0m" if _tty() else ""

def dit(m):   print(f"{C_B}▸{C_0} {m}")
def ok(m):    print(f"{C_G}✔{C_0} {m}")
def att(m):   print(f"{C_Y}▲{C_0} {m}", file=sys.stderr)
def note(m):  print(f"{C_D}  {m}{C_0}")
def etape(m): print(f"\n{C_S}{C_B}── {m} {C_0}")
def meurs(m): print(f"{C_R}✖{C_0} {m}", file=sys.stderr); sys.exit(1)
def mmss(t):  return f"{int(t//60)}:{int(t%60):02d}"


# ------------------------------------------------------------------ reglages
RACCORDS = {
    "coupe": None, "flash": None, "noir": None, "fondu": None,
    "enchaine": "fade", "zoom": "zoomin", "flou": "hblur",
    "glisse": "slideleft", "dissolution": "dissolve", "pixel": "pixelize",
    "lumiere": "fadewhite", "ombre": "fadeblack", "radial": "radial",
    "volet": "smoothleft", "rideau": "wipeleft",
}
MOUVEMENTS = ["zoom_avant", "zoom_arriere", "pano_droite", "pano_gauche", "fixe"]

DEFAUTS = {
    "etalonnage": "luxe", "texture": "doux", "halo": 0.30, "brume": 0.25,
    "mouvement": "auto", "raccord": "enchaine", "raccord_duree": 0.4,
    "duree_plan": 6.0, "vitesse": 1.0, "nettete": 0.0, "zoom": 0.0,
}


def sh(cmd):
    """Toujours bash : « source » n'existe pas dans /bin/sh, qui est le
    shell par defaut de subprocess."""
    return subprocess.run(cmd, shell=True, executable="/bin/bash",
                          capture_output=True, text=True).stdout.strip()


def filtre_shell(fonction, *args):
    """Recupere une chaine de filtres depuis lib/grades.sh : une seule
    definition des etalonnages pour tout le studio."""
    a = " ".join(f'"{x}"' for x in args)
    return sh(f'cd "{RACINE}" && source lib/common.sh && source lib/grades.sh && {fonction} {a}')


def sonde(f, champ, flux="v:0"):
    return sh(f'ffprobe -v error -select_streams {flux} -show_entries stream={champ} '
              f'-of csv=p=0 "{f}" 2>/dev/null | head -1')


def duree_de(f):
    v = sh(f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{f}" 2>/dev/null')
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def est_image(f):
    c = sonde(f, "codec_name")
    if c in ("mjpeg", "png", "bmp", "gif", "webp", "tiff"):
        return True
    return sonde(f, "nb_frames") == "1"


# ==================================================================
#  Lecture et validation du projet
# ==================================================================
def charger(chemin):
    if not os.path.isfile(chemin):
        meurs(f"Projet introuvable : {chemin}\n"
              f"  Cree-en un :  ./mz projet --nouveau {chemin}")
    texte = open(chemin, encoding="utf-8").read()
    try:
        if chemin.endswith((".yml", ".yaml")):
            import yaml
            p = yaml.safe_load(texte)
        else:
            p = json.loads(texte)
    except ImportError:
        meurs("PyYAML manquant.  pip install pyyaml   (ou utilise un fichier .json)")
    except Exception as e:
        meurs(f"Le fichier de projet est mal forme :\n  {e}")
    if not isinstance(p, dict):
        meurs("Le fichier de projet doit contenir un dictionnaire.")
    return p


def resoudre(chemin, base):
    if not chemin:
        return None
    return chemin if os.path.isabs(chemin) else os.path.normpath(os.path.join(base, chemin))


def valider(p, base):
    """Verifie tout avant de lancer une heure de calcul."""
    erreurs, avertis = [], []

    plans = p.get("plans") or []
    if not plans:
        erreurs.append("aucun plan : la section « plans » est vide")

    d = dict(DEFAUTS); d.update(p.get("defaut") or {})
    p["defaut"] = d

    if d["etalonnage"] not in filtre_shell("mz_grades_list").split():
        erreurs.append(f"etalonnage inconnu « {d['etalonnage'] }»")
    if d["texture"] not in ("aucun", "doux", "normal", "fort"):
        erreurs.append(f"texture inconnue « {d['texture']} »")

    for i, c in enumerate(plans, 1):
        if not isinstance(c, dict) or not c.get("source"):
            erreurs.append(f"plan {i} : « source » manquante")
            continue
        f = resoudre(c["source"], base)
        if not os.path.isfile(f):
            erreurs.append(f"plan {i} : fichier introuvable — {c['source']}")
            continue
        c["_fichier"] = f
        c["_image"] = est_image(f)
        r = c.get("raccord", d["raccord"])
        if r not in RACCORDS:
            erreurs.append(f"plan {i} : raccord inconnu « {r} » "
                           f"(connus : {', '.join(RACCORDS)})")
        m = c.get("mouvement", d["mouvement"])
        if m not in MOUVEMENTS + ["auto"]:
            erreurs.append(f"plan {i} : mouvement inconnu « {m} »")
        v = float(c.get("vitesse", d["vitesse"]) or 1.0)
        if v <= 0:
            erreurs.append(f"plan {i} : vitesse doit etre > 0")
        if not c["_image"]:
            dur_src = duree_de(f)
            deb = float(c.get("debut", 0))
            besoin = float(c.get("duree", d["duree_plan"])) * v
            if deb + besoin > dur_src + 0.05:
                avertis.append(f"plan {i} : demande {deb+besoin:.1f}s de « "
                               f"{os.path.basename(f)} » qui n'en fait que {dur_src:.1f}s "
                               "— la derniere image sera tenue")

    son = p.get("son") or {}
    for cle in ("voix", "musique"):
        if son.get(cle):
            f = resoudre(son[cle], base)
            if not os.path.isfile(f):
                erreurs.append(f"son : « {cle} » introuvable — {son[cle]}")
            else:
                son["_" + cle] = f
    p["son"] = son

    st = p.get("soustitres") or {}
    for cle in ("script", "srt"):
        if st.get(cle):
            f = resoudre(st[cle], base)
            if not os.path.isfile(f):
                erreurs.append(f"soustitres : « {cle} » introuvable — {st[cle]}")
            else:
                st["_" + cle] = f
    p["soustitres"] = st

    # --- zones occupees par l'habillage : un titre pose dessus sera illisible
    marque = p.get("marque") or {}
    H = int((p.get("format") or {}).get("hauteur", 1920))
    dossier_marque = os.path.join(RACINE, "assets", "brand")
    # duree reelle attendue : somme des plans moins ce que mangent les
    # raccords, ou la duree imposee si le projet en fixe une
    brut = sum(float(c.get("duree", d["duree_plan"]))
               for c in plans if isinstance(c, dict))
    recouvre = 0.0
    for k in range(len(plans) - 1):
        if isinstance(plans[k], dict) and RACCORDS.get(
                plans[k].get("raccord", d["raccord"])):
            recouvre += float(plans[k].get("raccord_duree", d["raccord_duree"]))
    total_prevu = brut - recouvre
    imposee = p.get("duree", "auto")
    if str(imposee).lower() != "auto":
        try:
            total_prevu = float(imposee)
        except (TypeError, ValueError):
            erreurs.append(f"duree : « {imposee} » n'est ni un nombre ni « auto »")
    zones = []
    if str(marque.get("signature", "auto")).lower() not in ("non", "aucune", "0", "false"):
        intro = os.path.join(dossier_marque, "intro_signature.mov")
        outro = os.path.join(dossier_marque, "outro_signature.mov")
        if marque.get("intro", True) and os.path.isfile(intro):
            zones.append(("l'intro Mr ZIKA", 0.0, duree_de(intro),
                          H * 0.26, H * 0.62))
        if marque.get("fin", True):
            od = duree_de(outro) if os.path.isfile(outro) else 0
            if od and total_prevu >= od * 2.5:
                zones.append(("la carte de fin", total_prevu - od, total_prevu,
                              H * 0.26, H * 0.78))
            else:
                ds = max(1.2, min(2.4, total_prevu / 3.0))
                zones.append(("la signature de fin", total_prevu - ds, total_prevu,
                              H * 0.26, H * 0.56))
    if marque.get("filigrane", True):
        zones.append(("le filigrane", 0.0, total_prevu, H * 0.775, H * 0.87))

    for i, t in enumerate(p.get("textes") or [], 1):
        if not t.get("contenu"):
            erreurs.append(f"texte {i} : « contenu » manquant")
        if t.get("a") is None:
            erreurs.append(f"texte {i} : « a » (instant de depart) manquant")
            continue
        a = float(t["a"]); b = a + float(t.get("duree", 2.2))
        taille = int(t.get("taille", 130))
        y = float(t.get("hauteur", H * 0.42))
        haut, bas = y - taille * 0.6, y + taille * 0.6
        for nom, za, zb, zh, zb2 in zones:
            if a < zb and b > za and haut < zb2 and bas > zh:
                avertis.append(
                    f"texte {i} « {str(t['contenu'])[:26]} » passe sur {nom} "
                    f"(vers {mmss(a)}). Deplace-le : « hauteur: {int(zb2 + taille)} » "
                    "ou change son instant.")
                break

    # les sous-titres aussi peuvent tomber sous le filigrane
    st_y = int((p.get("soustitres") or {}).get("hauteur", H * 0.646))
    st_t = int((p.get("soustitres") or {}).get("taille", 112))
    if marque.get("filigrane", True) and st_y + st_t * 0.6 > H * 0.775:
        avertis.append(f"les sous-titres (hauteur {st_y}) touchent le filigrane. "
                       f"Remonte-les vers {int(H*0.775 - st_t*0.7)}.")

    return erreurs, avertis


# ==================================================================
#  Rendu d'un plan
# ==================================================================
def mouvement_de(nom, k, L, W, H, zoom_sup):
    """Chaine de filtres du mouvement de camera."""
    if nom == "auto":
        nom = MOUVEMENTS[k % 4]
    f = L * 30.0
    if nom == "fixe":
        # pas de mouvement, mais il faut quand meme redescendre a la
        # definition de sortie : le plan a ete pre-agrandi au double
        base = f"scale={W}:{H}:flags=lanczos"
    elif nom == "zoom_avant":
        base = (f"zoompan=z='1+0.11*on/{f:.1f}':x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)':d={int(f)}:s={W}x{H}:fps=30")
    elif nom == "zoom_arriere":
        base = (f"zoompan=z='1.11-0.11*on/{f:.1f}':x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)':d={int(f)}:s={W}x{H}:fps=30")
    elif nom == "pano_droite":
        base = (f"zoompan=z='1.06+0.06*on/{f:.1f}':x='(iw-iw/zoom)*on/{f:.1f}'"
                f":y='ih/2-(ih/zoom/2)':d={int(f)}:s={W}x{H}:fps=30")
    else:
        base = (f"zoompan=z='1.06+0.06*on/{f:.1f}':x='(iw-iw/zoom)*(1-on/{f:.1f})'"
                f":y='ih/2-(ih/zoom/2)':d={int(f)}:s={W}x{H}:fps=30")
    return base


def cle_cache(c, d, W, H, fps):
    m = hashlib.sha1()
    for x in (c.get("_fichier"), os.path.getmtime(c["_fichier"]),
              c.get("debut"), c.get("duree"), c.get("vitesse"),
              c.get("etalonnage", d["etalonnage"]), c.get("texture", d["texture"]),
              c.get("halo", d["halo"]), c.get("brume", d["brume"]),
              c.get("mouvement", d["mouvement"]), c.get("raccord", d["raccord"]),
              c.get("zoom", d["zoom"]), W, H, fps):
        m.update(str(x).encode())
    return m.hexdigest()[:16]


def rendre_plan(k, c, p, cache, W, H, fps, atmo):
    d = p["defaut"]
    L = float(c.get("duree", d["duree_plan"]))
    v = float(c.get("vitesse", d["vitesse"]) or 1.0)
    sortie = os.path.join(cache, f"plan_{k:04d}_{cle_cache(c, d, W, H, fps)}.mp4")
    if os.path.exists(sortie) and os.path.getsize(sortie) > 1000:
        return sortie, True

    grade = filtre_shell("mz_grade", c.get("etalonnage", d["etalonnage"]))
    text = filtre_shell("mz_fx_texture", c.get("texture", d["texture"]))
    halo = float(c.get("halo", d["halo"]))
    brume = float(c.get("brume", d["brume"]))

    entrees, prep = [], ""
    if c["_image"]:
        entrees += ["-loop", "1", "-framerate", str(fps), "-t", f"{L:.3f}", "-i", c["_fichier"]]
        pw, ph = W * 2, H * 2
        mv = mouvement_de(c.get("mouvement", d["mouvement"]), k, L, W, H, 0)
        prep = (f"scale={pw}:{ph}:force_original_aspect_ratio=increase,crop={pw}:{ph}"
                + ("," + mv if mv else ""))
    else:
        deb = float(c.get("debut", 0))
        entrees += ["-ss", f"{deb:.3f}", "-stream_loop", "3", "-i", c["_fichier"]]
        prep = (f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={W}:{H},setpts=(PTS-STARTPTS)*{1.0/v:.5f}")

    zsup = float(c.get("zoom", d["zoom"]))
    punch = ""
    if zsup > 0:
        z = zsup / 100.0
        punch = (f",scale=w='{W}*(1+{z:.4f}*max(0,1-t/0.32))':"
                 f"h='{H}*(1+{z:.4f}*max(0,1-t/0.32))':eval=frame:flags=bilinear,crop={W}:{H}")

    morceaux = [x for x in (prep, punch.lstrip(","), grade, "format=gbrp") if x]
    graphe = "[0:v]" + ",".join(morceaux) + "[pre];"
    graphe += filtre_shell("mz_fx_halation", "pre", "lit0", f"{halo}").replace("\n", "") + ";"
    if brume > 0 and atmo and os.path.isfile(atmo):
        entrees += ["-loop", "1", "-framerate", str(fps), "-t", f"{L:.3f}", "-i", atmo]
        dx, dy = 17 + (k * 7) % 13, 23 + (k * 11) % 19
        graphe += (f"[1:v]scale=2600:-1,format=gbrp,crop={W}:{H}:"
                   f"x='(iw-{W})*(0.5+0.45*sin(2*PI*t/{dx}))':"
                   f"y='(ih-{H})*(0.5+0.45*cos(2*PI*t/{dy}))'[atmo];"
                   f"[lit0][atmo]blend=all_mode=softlight:all_opacity={brume}[lit];")
    else:
        graphe += "[lit0]null[lit];"

    r = c.get("raccord", d["raccord"])
    fin = ""
    if r == "flash":
        fin = ",fade=t=in:st=0:d=0.08:color=white"
    elif r == "noir":
        fin = (",fade=t=in:st=0:d=0.14:color=black"
               f",fade=t=out:st={max(0,L-0.14):.2f}:d=0.14:color=black")
    elif r == "fondu":
        fin = (",fade=t=in:st=0:d=0.12:color=black"
               f",fade=t=out:st={max(0,L-0.12):.2f}:d=0.12:color=black")

    queue = [x for x in (text, fin.lstrip(","), f"trim=0:{L:.3f}", "setpts=PTS-STARTPTS",
                         "format=yuv420p", "setsar=1") if x]
    graphe += "[lit]" + ",".join(queue) + "[out]"

    cmd = (["ffmpeg", "-y", "-v", "error"] + entrees
           + ["-filter_complex", graphe, "-map", "[out]", "-an", "-t", f"{L:.3f}",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
              "-pix_fmt", "yuv420p", "-r", str(fps), "-f", "mp4", sortie + ".part"])
    r2 = subprocess.run(cmd, capture_output=True, text=True)
    if r2.returncode != 0 or not os.path.exists(sortie + ".part"):
        return (None, r2.stderr[-400:]), False
    os.replace(sortie + ".part", sortie)
    return sortie, False


# ==================================================================
#  Assemblage : raccords a recouvrement ou bout a bout
# ==================================================================
def assembler(fichiers, plans, p, cache, W, H, fps):
    d = p["defaut"]
    n = len(fichiers)
    durees = [float(c.get("duree", d["duree_plan"])) for c in plans]
    base = os.path.join(cache, "base.mp4")

    joints = []
    for k in range(n - 1):
        r = plans[k].get("raccord", d["raccord"])
        x = RACCORDS.get(r)
        if x:
            dx = float(plans[k].get("raccord_duree", d["raccord_duree"]))
            dx = min(dx, durees[k] * 0.45, durees[k + 1] * 0.45)
            joints.append((k, x, dx))

    total = sum(durees) - sum(j[2] for j in joints)

    if not joints:
        liste = os.path.join(cache, "concat.txt")
        with open(liste, "w", encoding="utf-8") as f:
            for x in fichiers:
                f.write(f"file '{x}'\n")
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
               "-i", liste, "-c", "copy", base]
    else:
        if n > 70:
            meurs(f"{n} plans a enchainer : trop pour la memoire.\n"
                  "  Allonge les plans, ou mets « raccord: coupe ».")
        entrees, graphe, prec, cumul = [], "", "0:v", 0.0
        for x in fichiers:
            entrees += ["-i", x]
        jd = {k: (x, dx) for k, x, dx in joints}
        for k in range(1, n):
            xk, dxk = jd.get(k - 1, (None, 0.0))
            cumul += durees[k - 1] - dxk
            sortie_l = "xout" if k == n - 1 else f"x{k}"
            if xk:
                graphe += (f"[{prec}][{k}:v]xfade=transition={xk}:duration={dxk:.3f}"
                           f":offset={cumul:.3f}[{sortie_l}];")
            else:
                # jointure sans recouvrement au milieu d'une chaine : fondu de 1 image
                graphe += (f"[{prec}][{k}:v]xfade=transition=fade:duration=0.033"
                           f":offset={cumul:.3f}[{sortie_l}];")
                cumul -= 0.033
            prec = sortie_l
        cmd = (["ffmpeg", "-y", "-v", "error"] + entrees
               + ["-filter_complex", graphe.rstrip(";"), "-map", "[xout]", "-an",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                  "-pix_fmt", "yuv420p", "-r", str(fps), base])

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        meurs("Assemblage impossible :\n  " + r.stderr[-500:])
    return base, total, len(joints)


# ==================================================================
#  Textes : sous-titres automatiques + titres poses a la main
# ==================================================================
def construire_ass(p, base_dir, cache, W, H, duree, police):
    import make_captions as mc
    st = p.get("soustitres") or {}
    textes = p.get("textes") or []
    if not st.get("_script") and not st.get("_srt") and not textes:
        return None

    familles = os.path.splitext(os.path.basename(police))[0].split("-")[0] if police else "Anton"

    # --- un style par configuration distincte (taille, couleurs, bandeau)
    styles, cles = [], {}

    def style_pour(taille, couleur, contour, bord, ombre, bandeau, marge_b):
        cle = (taille, couleur, contour, bord, ombre, bandeau, marge_b)
        if cle in cles:
            return cles[cle]
        nom = f"MZ{len(styles)}"
        cles[cle] = nom
        if bandeau:
            styles.append(f"Style: {nom},{familles},{taille},{mc.ass_color(couleur)},"
                          f"&H000000FF,{mc.ass_color(bandeau)},&H00000000,0,0,0,0,"
                          f"100,100,1,0,3,{marge_b},0,5,80,80,0,1")
        else:
            styles.append(f"Style: {nom},{familles},{taille},{mc.ass_color(couleur)},"
                          f"&H000000FF,{mc.ass_color(contour)},&H96000000,0,0,0,0,"
                          f"100,100,1,0,1,{bord},{ombre},5,80,80,0,1")
        return nom

    evenements = []

    # --- sous-titres automatiques
    if st.get("_script") or st.get("_srt"):
        taille = int(st.get("taille", 112))
        y = int(st.get("hauteur", int(H * 0.646)))
        anim = st.get("animation", "pop")
        accent = mc.ass_color(st.get("accent", "#FFC845"))
        bandeau = st.get("bandeau")
        nom_style = style_pour(taille, st.get("couleur", "#FFFFFF"),
                               st.get("contour", "#0A0A0A"), 9, 4, bandeau,
                               int(st.get("bandeau_marge", 22)))
        if st.get("_srt"):
            cales = mc.parse_srt(st["_srt"])
        else:
            morceaux = mc.chunk_text(open(st["_script"], encoding="utf-8-sig").read(),
                                     max(1, min(6, int(st.get("mots_par_groupe", 3)))))
            segs = None
            voix = (p.get("son") or {}).get("_voix")
            if voix:
                segs = mc.speech_segments(voix)
            cales = mc.time_chunks(morceaux, duree, segs)
        for corps, a, b in cales:
            for couche, ea, eb, _s, txt in mc.construire(
                    anim, mc.jetons(corps.strip()), a, b, W // 2, y, accent,
                    taille, police, W, H, bool(bandeau)):
                evenements.append((couche, ea, eb, nom_style, txt))

    # --- titres poses a la main
    for t in textes:
        taille = int(t.get("taille", 130))
        y = int(t.get("hauteur", int(H * 0.42)))
        a = float(t["a"])
        b = a + float(t.get("duree", 2.2))
        accent = mc.ass_color(t.get("accent", "#FFC845"))
        bandeau = t.get("bandeau")
        nom_style = style_pour(taille, t.get("couleur", "#FFFFFF"),
                               t.get("contour", "#0A0A0A"), 10, 5, bandeau,
                               int(t.get("bandeau_marge", 26)))
        for couche, ea, eb, _s, txt in mc.construire(
                t.get("animation", "frappe"), mc.jetons(str(t["contenu"])),
                a, b, W // 2, y, accent, taille, police, W, H, bool(bandeau)):
            evenements.append((couche + 2, ea, eb, nom_style, txt))

    if not evenements:
        return None

    entete = (f"[Script Info]\n; MZ STUDIO\nScriptType: v4.00+\nPlayResX: {W}\n"
              f"PlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
              "YCbCr Matrix: TV.709\n\n[V4+ Styles]\n"
              "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
              "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
              "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
              "MarginL, MarginR, MarginV, Encoding\n" + "\n".join(styles)
              + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, "
                "MarginR, MarginV, Effect, Text\n")
    lignes = [f"Dialogue: {c},{mc.ts(a)},{mc.ts(b)},{s},,0,0,0,,{t}"
              for c, a, b, s, t in sorted(evenements, key=lambda e: (e[1], e[0]))]
    chemin = os.path.join(cache, "textes.ass")
    open(chemin, "w", encoding="utf-8").write(entete + "\n".join(lignes) + "\n")
    return chemin, len(evenements)


# ==================================================================
#  Export : habillage, son, encodage
# ==================================================================
def echapper(chemin):
    return chemin.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def exporter(p, base, ass, duree, sortie, W, H, fps, crf, base_dir):
    marque = p.get("marque") or {}
    son = p.get("son") or {}
    dossier_marque = os.path.join(RACINE, "assets", "brand")
    polices = os.path.join(RACINE, "assets", "fonts")

    entrees = ["-i", base]
    graphe, cur, idx = "", "0:v", 1

    if ass:
        graphe += (f"[{cur}]subtitles='{echapper(ass)}'"
                   f":fontsdir='{echapper(polices)}'[vsub];")
        cur = "vsub"

    intro = os.path.join(dossier_marque, "intro_signature.mov")
    outro = os.path.join(dossier_marque, "outro_signature.mov")
    grand = os.path.join(dossier_marque, "signature_big.png")
    mark = os.path.join(dossier_marque, "signature_mark.png")

    sig = str(marque.get("signature", "auto")).lower()
    if sig not in ("non", "aucune", "0", "false"):
        if marque.get("intro", True) and os.path.isfile(intro):
            entrees += ["-i", intro]
            graphe += (f"[{idx}:v]setpts=PTS-STARTPTS[intro];"
                       f"[{cur}][intro]overlay=0:0:eof_action=pass:format=auto[vi];")
            cur, idx = "vi", idx + 1
        assez = os.path.isfile(outro) and duree >= duree_de(outro) * 2.5
        if assez and marque.get("fin", True):
            od = duree_de(outro)
            entrees += ["-i", outro]
            graphe += (f"[{idx}:v]setpts=PTS-STARTPTS+{max(0, duree-od):.2f}/TB[outro];"
                       f"[{cur}][outro]overlay=0:0:eof_action=pass:format=auto[vo];")
            cur, idx = "vo", idx + 1
        elif marque.get("fin", True) and os.path.isfile(grand):
            ds = max(1.2, min(2.4, duree / 3.0))
            ss = max(0.0, duree - ds)
            lw = int(W * 0.62)
            gw, gh = int(sonde(grand, "width") or 1), int(sonde(grand, "height") or 1)
            lh = int(lw * gh / max(1, gw))
            sy = int(H * 0.40 - lh / 2)
            graphe += (f"color=black:s={W}x{H}:r={fps}:d={ds:.2f},format=rgba,"
                       f"colorchannelmixer=aa=0.44,fade=t=in:st=0:d=0.45:alpha=1,"
                       f"setpts=PTS-STARTPTS+{ss:.2f}/TB[voile];"
                       f"[{cur}][voile]overlay=0:0:eof_action=pass:format=auto[vv];")
            entrees += ["-loop", "1", "-framerate", str(fps), "-t", f"{ds:.2f}", "-i", grand]
            graphe += (f"[{idx}:v]scale=w='max(2,{lw}*(1.09-0.09*min(1,t/0.40)))':"
                       f"h='max(2,{lh}*(1.09-0.09*min(1,t/0.40)))':eval=frame:flags=bilinear,"
                       f"format=rgba,fade=t=in:st=0:d=0.38:alpha=1,"
                       f"setpts=PTS-STARTPTS+{ss:.2f}/TB[sig];"
                       f"[vv][sig]overlay=x='(W-w)/2':y='{sy}':eval=frame"
                       ":eof_action=pass:format=auto[vo];")
            cur, idx = "vo", idx + 1

    if marque.get("filigrane", True) and os.path.isfile(mark):
        mw, my = int(W * 0.26), int(H * 0.775)
        entrees += ["-i", mark]
        graphe += (f"[{idx}:v]scale={mw}:-1,format=rgba,colorchannelmixer=aa=0.72[mk];"
                   f"[{cur}][mk]overlay=x=(W-w)/2:y={my}:format=auto[vm];")
        cur, idx = "vm", idx + 1

    graphe += f"[{cur}]format=yuv420p,setsar=1[vout];"

    # --- son
    lufs = float(son.get("lufs", -14))
    fs = float(son.get("fondu_sortie", 1.6))
    fade = max(0.0, duree - fs)
    voix, musique = son.get("_voix"), son.get("_musique")
    sr = 48000
    if voix and musique:
        entrees += ["-i", voix, "-stream_loop", "-1", "-t", f"{duree:.3f}", "-i", musique]
        iv, im = idx, idx + 1
        vol = float(son.get("volume_musique", -19))
        graphe += (
            f"[{iv}:a]aformat=sample_fmts=fltp:sample_rates={sr}:channel_layouts=stereo,"
            f"apad,atrim=0:{duree:.3f},asetpts=N/SR/TB,asplit=2[vx][vk];"
            f"[{im}:a]aformat=sample_fmts=fltp:sample_rates={sr}:channel_layouts=stereo,"
            f"apad,atrim=0:{duree:.3f},asetpts=N/SR/TB,volume={vol}dB[mu];"
            f"[mu][vk]sidechaincompress=threshold=0.045:ratio=9:attack=18:release=420"
            f":makeup=1[duck];[vx][duck]amix=inputs=2:duration=first:normalize=0[mix];"
            f"[mix]loudnorm=I={lufs}:TP=-1.5:LRA=11,alimiter=limit=0.97,"
            f"afade=t=out:st={fade:.2f}:d={fs:.2f}[aout]")
    elif voix or musique:
        src = voix or musique
        entrees += ["-stream_loop", "-1", "-t", f"{duree:.3f}", "-i", src]
        graphe += (
            f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates={sr}:channel_layouts=stereo,"
            f"apad,atrim=0:{duree:.3f},asetpts=N/SR/TB,"
            f"loudnorm=I={lufs}:TP=-1.5:LRA=11,alimiter=limit=0.97,"
            f"afade=t=out:st={fade:.2f}:d={fs:.2f}[aout]")
    else:
        entrees += ["-f", "lavfi", "-t", f"{duree:.3f}",
                    "-i", f"anullsrc=r={sr}:cl=stereo"]
        graphe += f"[{idx}:a]anull[aout]"

    os.makedirs(os.path.dirname(os.path.abspath(sortie)) or ".", exist_ok=True)
    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats"] + entrees
           + ["-filter_complex", graphe, "-map", "[vout]", "-map", "[aout]",
              "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
              "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
              "-r", str(fps), "-g", str(fps * 2), "-c:a", "aac", "-b:a", "192k",
              "-ar", str(sr), "-ac", "2", "-movflags", "+faststart",
              "-t", f"{duree:.3f}", sortie])
    r = subprocess.run(cmd)
    if r.returncode != 0:
        meurs("Export impossible.")
    return sortie


# ==================================================================
#  Creation de projets
# ==================================================================
MODELE = """# ═════════════════════════════════════════════════════════════
#  MZ STUDIO — fichier de projet
#  Edite ce fichier, relance « ./mz projet -f <ce fichier> ».
#  Seuls les plans deja rendus a l'identique sont reutilises :
#  changer un reglage ne refait que ce qui en depend.
# ═════════════════════════════════════════════════════════════

sortie: projet/04-rendu/ma-video.mp4

format:
  largeur: 1080
  hauteur: 1920
  images_par_seconde: 30

# duree : "auto" suit la somme des plans, sinon un nombre de secondes
duree: auto
qualite: 19            # 16 excellente · 19 equilibree · 23 legere

# Reglages appliques a TOUS les plans. Chaque plan peut les surcharger.
defaut:
  etalonnage: luxe     # ./mz looks
  texture: doux        # aucun · doux · normal · fort
  halo: 0.30           # halo cinema, 0 a 0.6
  brume: 0.25          # nappe derivante sur le fond, 0 pour couper
  mouvement: auto      # auto · zoom_avant · zoom_arriere · pano_droite · pano_gauche · fixe
  raccord: enchaine    # ./mz looks pour la liste complete
  raccord_duree: 0.4
  duree_plan: 6
  zoom: 0              # coup de zoom au demarrage du plan, en %

marque:
  filigrane: oui
  intro: oui
  fin: oui

son:
  voix: projet/02-audio/voix.wav
  musique: ~           # ~ = aucune
  volume_musique: -19
  lufs: -14
  fondu_sortie: 1.6

# ── Les plans, dans l'ordre ────────────────────────────────────
plans:
  - source: projet/03-broll/01.jpg
  - source: projet/03-broll/02.jpg
    duree: 4
    etalonnage: fire      # surcharge locale
    raccord: flou
  - source: projet/03-broll/un-clip.mp4
    debut: 12.5           # ou commencer dans le fichier
    duree: 5
    vitesse: 0.6          # < 1 = ralenti
    mouvement: fixe

# ── Sous-titres automatiques ───────────────────────────────────
soustitres:
  script: projet/script.txt   # ou bien :  srt: projet/parties/x.srt
  animation: pop              # python3 tools/make_captions.py --lister
  mots_par_groupe: 3
  taille: 112
  hauteur: 1240               # 65 % de 1920 : au-dessus de l'interface TikTok
  bandeau: "#0E0E10"          # supprime la ligne pour un simple contour
  accent: "#FFC845"

# ── Titres poses a la main, en plus des sous-titres ────────────
textes:
  - a: 0.6                    # instant de depart, en secondes
    duree: 2.2
    contenu: "PERSONNE NE VIENDRA"
    animation: frappe
    taille: 140
    hauteur: 760
"""


def nouveau(chemin):
    if os.path.exists(chemin):
        meurs(f"{chemin} existe deja — supprime-le ou choisis un autre nom.")
    os.makedirs(os.path.dirname(os.path.abspath(chemin)) or ".", exist_ok=True)
    open(chemin, "w", encoding="utf-8").write(MODELE)
    ok(f"projet cree : {C_S}{chemin}{C_0}")
    note("Ouvre-le, adapte les chemins, puis :")
    note(f"  ./mz projet -f {chemin}")


def depuis_dossier(dossier, chemin, duree_cible, plan_sec, script, voix, musique):
    exts = (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".mkv", ".webm", ".m4v")
    fichiers = sorted(f for f in os.listdir(dossier)
                      if f.lower().endswith(exts) and not f.startswith("."))
    if not fichiers:
        meurs(f"Aucune image ni clip dans {dossier}")

    n = max(1, int(round((duree_cible + plan_sec) / plan_sec)))
    # les chemins du projet sont relatifs AU FICHIER DE PROJET, pas au
    # repertoire courant : le projet reste valable ou qu'on le lance
    ancre = os.path.dirname(os.path.abspath(chemin)) or "."

    def rel(x):
        return os.path.relpath(os.path.abspath(x), ancre) if x else None

    plans = []
    for k in range(n):
        src = os.path.join(dossier, fichiers[k % len(fichiers)])
        e = {"source": rel(src)}
        if k >= len(fichiers) and not est_image(src):
            # deuxieme passage sur un clip : on repart d'ailleurs dedans
            d = duree_de(src)
            if d > plan_sec * 1.5:
                e["debut"] = round(((k // len(fichiers)) * 0.37) % 1.0 * (d - plan_sec), 2)
        plans.append(e)

    p = {
        "sortie": rel(os.path.join(RACINE, "projet", "04-rendu", "ma-video.mp4")),
        "format": {"largeur": 1080, "hauteur": 1920, "images_par_seconde": 30},
        "duree": duree_cible if duree_cible else "auto",
        "qualite": 19,
        "defaut": {"etalonnage": "orange_teal", "texture": "doux", "halo": 0.30,
                   "brume": 0.25, "mouvement": "auto", "raccord": "enchaine",
                   "raccord_duree": 0.4, "duree_plan": plan_sec, "zoom": 0},
        "marque": {"filigrane": True, "intro": True, "fin": True},
        "son": {"voix": rel(voix), "musique": rel(musique), "volume_musique": -19,
                "lufs": -14, "fondu_sortie": 1.6},
        "plans": plans,
    }
    if script:
        p["soustitres"] = {"script": rel(script), "animation": "pop", "mots_par_groupe": 3,
                           "taille": 112, "hauteur": 1240, "bandeau": "#0E0E10",
                           "accent": "#FFC845"}
    import yaml
    os.makedirs(os.path.dirname(os.path.abspath(chemin)) or ".", exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("# Projet genere depuis " + dossier + "\n"
                "# Reordonne les plans, change leurs durees, leurs raccords :\n"
                "# tout est modifiable ici.\n\n")
        yaml.safe_dump(p, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    ok(f"projet genere : {C_S}{chemin}{C_0}")
    note(f"{len(plans)} plans depuis {len(fichiers)} fichier(s)")
    note(f"  ./mz projet -f {chemin}")


# ==================================================================
def main():
    ap = argparse.ArgumentParser(description="Le monteur de MZ STUDIO")
    ap.add_argument("-f", "--fichier", help="projet a rendre")
    ap.add_argument("--nouveau", metavar="FICHIER", help="creer un projet modele")
    ap.add_argument("--depuis", metavar="DOSSIER", help="generer un projet depuis un dossier")
    ap.add_argument("--out", default="projet/mon-projet.yml", help="ou ecrire le projet genere")
    ap.add_argument("--duree", type=float, default=300.0, help="duree visee (--depuis)")
    ap.add_argument("--plan", type=float, default=6.0, help="duree d'un plan (--depuis)")
    ap.add_argument("--script", default=None, help="script des sous-titres (--depuis)")
    ap.add_argument("--voix", default=None, help="fichier voix (--depuis)")
    ap.add_argument("--musique", default=None, help="musique de fond (--depuis)")
    ap.add_argument("--verifier", action="store_true", help="controler sans rendre")
    ap.add_argument("--sortie", default=None, help="forcer le fichier produit")
    ap.add_argument("--refaire", action="store_true", help="ignorer le cache des plans")
    ap.add_argument("--jobs", type=int, default=0, help="plans rendus en parallele")
    a = ap.parse_args()

    if a.nouveau:
        return nouveau(a.nouveau)
    if a.depuis:
        return depuis_dossier(a.depuis, a.out, a.duree, a.plan,
                              a.script, a.voix, a.musique)
    if not a.fichier:
        ap.print_help()
        return

    chemin = os.path.abspath(a.fichier)
    base_dir = os.path.dirname(chemin)
    p = charger(chemin)

    etape("Verification")
    erreurs, avertis = valider(p, base_dir)
    for w in avertis:
        att(w)
    if erreurs:
        for e in erreurs:
            print(f"  {C_R}ERREUR{C_0}  {e}", file=sys.stderr)
        meurs(f"{len(erreurs)} probleme(s) — rien n'a ete calcule.")

    fmt = p.get("format") or {}
    W = int(fmt.get("largeur", 1080)); H = int(fmt.get("hauteur", 1920))
    fps = int(fmt.get("images_par_seconde", 30))
    crf = int(p.get("qualite", 19))
    plans = p["plans"]; d = p["defaut"]
    ok(f"{len(plans)} plan(s)  ·  {W}x{H} @ {fps} i/s  ·  etalonnage {d['etalonnage']}")

    prevu = sum(float(c.get("duree", d["duree_plan"])) for c in plans)
    note(f"duree brute des plans : {mmss(prevu)}")
    if a.verifier:
        print()
        return ok("Projet valide — rien n'a ete calcule.")

    cache = os.path.join(RACINE, "projet", ".cache", "monteur",
                         hashlib.sha1(chemin.encode()).hexdigest()[:12])
    os.makedirs(cache, exist_ok=True)
    if a.refaire:
        for f in os.listdir(cache):
            if f.startswith("plan_"):
                os.remove(os.path.join(cache, f))

    atmo = os.path.join(RACINE, "assets", "overlays", "brume.jpg")
    if any(float(c.get("brume", d["brume"])) > 0 for c in plans) and not os.path.isfile(atmo):
        os.makedirs(os.path.dirname(atmo), exist_ok=True)
        subprocess.run([sys.executable, os.path.join(RACINE, "tools", "make_backdrop.py"),
                        "--atmosphere", atmo], capture_output=True)

    etape(f"1/4  Rendu des {len(plans)} plans")
    nproc = a.jobs or (os.cpu_count() or 2)
    dit(f"en parallele sur {nproc} coeurs…")
    resultats = [None] * len(plans)
    with ThreadPoolExecutor(max_workers=nproc) as ex:
        futurs = {ex.submit(rendre_plan, k, c, p, cache, W, H, fps, atmo): k
                  for k, c in enumerate(plans)}
        for fu in futurs:
            k = futurs[fu]
            resultats[k] = fu.result()
    fichiers, caches = [], 0
    for k, (res, depuis_cache) in enumerate(resultats):
        if isinstance(res, tuple) or res is None:
            detail = res[1] if isinstance(res, tuple) else ""
            meurs(f"plan {k+1} ({plans[k]['source']}) : rendu impossible\n  {detail}")
        fichiers.append(res)
        caches += 1 if depuis_cache else 0
    ok(f"{len(fichiers)} plans" + (f"  ({caches} repris du cache)" if caches else ""))

    etape("2/4  Assemblage")
    base, total, n_raccords = assembler(fichiers, plans, p, cache, W, H, fps)
    duree = total if str(p.get("duree", "auto")).lower() == "auto" else float(p["duree"])
    ok(f"{mmss(total)} de sequence, {n_raccords} raccord(s) a recouvrement")
    if abs(duree - total) > 0.5:
        note(f"duree imposee : {mmss(duree)}")

    etape("3/4  Textes")
    police = sh(f'cd "{RACINE}" && source lib/common.sh && mz_font_display')
    res = construire_ass(p, base_dir, cache, W, H, duree, police)
    ass = None
    if res:
        ass, n_ev = res
        ok(f"{n_ev} evenement(s) de texte")
    else:
        note("aucun texte")

    etape("4/4  Export")
    sortie = a.sortie or resoudre(p.get("sortie", "projet/04-rendu/video.mp4"), base_dir)
    dit(f"encodage — CRF {crf}, {W}x{H} @ {fps} i/s…")
    exporter(p, base, ass, duree, sortie, W, H, fps, crf, base_dir)

    reelle = duree_de(sortie)
    taille = os.path.getsize(sortie) / 1e6
    print()
    ok(f"{C_S}Video prete{C_0}")
    print(f"  {sortie}")
    print(f"  {mmss(reelle)}  ·  {taille:.1f} Mo  ·  {W}x{H} @ {fps} i/s")


if __name__ == "__main__":
    main()
