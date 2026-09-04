#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — references techniques et verification de fichier

Tout est en dur, hors ligne, gratuit. Aucune cle, aucun appel reseau :
ce sont des chiffres fixes, pas des reponses a acheter au token.

  python3 tools/specs.py                    toutes les references
  python3 tools/specs.py tiktok             une plateforme
  python3 tools/specs.py --verifier v.mp4   controle un fichier
"""
import argparse, json, os, re, subprocess, sys

VERIFIE_LE = "2026-09-04"

def _tty(): return sys.stdout.isatty()
C_G = "\033[32m" if _tty() else ""
C_Y = "\033[33m" if _tty() else ""
C_R = "\033[31m" if _tty() else ""
C_B = "\033[36m" if _tty() else ""
C_D = "\033[2m"  if _tty() else ""
C_S = "\033[1m"  if _tty() else ""
C_0 = "\033[0m"  if _tty() else ""


# ==================================================================
#  Ce qui ne bouge jamais : geometrie et normes de mesure
# ==================================================================
ZONES = """
Zones couvertes par l'interface, en fraction de la hauteur. Ce sont des
proportions : elles ne dependent ni de la definition ni du telephone.

  haut     0 %  -> 8 %     recherche, onglets
  bas      85 % -> 100 %   pseudo, description, son
  droite   0 %  -> 20 % de la largeur   j'aime, commentaires, partage

  Le studio pose les sous-titres a 64,6 % et le filigrane a 77,5 % :
  au-dessus de la zone basse, a gauche des boutons.
"""

LOUDNESS = """
Le volume n'est pas une question de gout : les plateformes RENORMALISENT.
Livrer plus fort ne sert a rien, elles baissent. Livrer plus faible et
elles montent, en remontant le bruit avec.

  -14 LUFS   reseaux sociaux et streaming   <- ce que produit le studio
  -16 LUFS   podcast (norme Apple/Spotify parlee)
  -23 LUFS   broadcast television (EBU R128)

  Crete vraie : -1,0 dBTP en broadcast, -1,5 dBTP recommande en diffusion
  compressee. Le studio vise -1,5 : la compression AAC fait remonter les
  cretes, la marge evite l'ecretage a la lecture.

  Mesurer un fichier :
    ffmpeg -i fichier.mp4 -af ebur128 -f null -
"""

CODECS = """
  Video   H.264 (libx264), profil High, niveau 4.1
          pix_fmt yuv420p       <- obligatoire, yuv444 ou 10 bits ne
                                   s'affichent pas sur la moitie des lecteurs
          Images-cle toutes les 2 s (-g 60 a 30 i/s)
  Audio   AAC-LC, 128 a 192 kb/s, 48 kHz, stereo
  Conteneur  MP4 avec +faststart
          Sans faststart, l'index est en fin de fichier : la lecture ne
          demarre qu'apres telechargement complet.
"""

PLATEFORMES = {
    "tiktok": dict(
        nom="TikTok", l=1080, h=1920, ratio="9:16", fps=[30, 60],
        debit=(4, 10), duree_max=600, duree_conseil="7 s a 3 min",
        taille_max_mo=287.6, taille_note="287,6 Mo par l'application ; 4 Go par le site",
        source="https://www.tiktok.com/creators"),
    "reels": dict(
        nom="Instagram Reels", l=1080, h=1920, ratio="9:16", fps=[30],
        debit=(5, 8), duree_max=90, duree_conseil="jusqu'a 90 s",
        taille_max_mo=4096, taille_note="4 Go",
        source="https://help.instagram.com"),
    "shorts": dict(
        nom="YouTube Shorts", l=1080, h=1920, ratio="9:16", fps=[30, 60],
        debit=(10, 15), duree_max=180, duree_conseil="jusqu'a 3 min",
        taille_max_mo=None, taille_note="limite du compte YouTube",
        source="https://support.google.com/youtube/answer/1722171"),
    "youtube": dict(
        nom="YouTube (paysage 1080p)", l=1920, h=1080, ratio="16:9", fps=[30, 60],
        debit=(8, 12), duree_max=None, duree_conseil="libre",
        taille_max_mo=None, taille_note="256 Go ou 12 h",
        source="https://support.google.com/youtube/answer/1722171"),
    "linkedin": dict(
        nom="LinkedIn", l=1080, h=1920, ratio="9:16 ou 1:1", fps=[30],
        debit=(5, 10), duree_max=600, duree_conseil="30 s a 3 min",
        taille_max_mo=5120, taille_note="5 Go",
        source="https://www.linkedin.com/help/linkedin"),
}


# ==================================================================
#  Lecture d'un fichier
# ==================================================================
def sonde(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", f],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Lecture impossible : {f}\n{r.stderr[:300]}")
    return json.loads(r.stdout)


def faststart(f):
    """L'index (moov) doit preceder les donnees (mdat), sinon la lecture
    ne demarre qu'apres telechargement complet."""
    try:
        with open(f, "rb") as fh:
            tete = fh.read(4 * 1024 * 1024)
        m, d = tete.find(b"moov"), tete.find(b"mdat")
        if m == -1:
            return None
        return d == -1 or m < d
    except OSError:
        return None


def lufs(f):
    """peak=true est indispensable : sans lui, ebur128 ne sort aucune crete."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f,
                        "-af", "ebur128=framelog=quiet:peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", r.stderr)
    # la crete VRAIE est celle qui compte : elle depasse la crete
    # d'echantillon une fois le signal reconstruit a la lecture
    c = re.search(r"True peak:\s*\n\s*Peak:\s*(-?[\d.]+)\s*dBFS", r.stderr)
    if not c:
        c = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", r.stderr)
    return (float(m.group(1)) if m else None,
            float(c.group(1)) if c else None)


def ligne(etat, libelle, valeur, attendu=""):
    marque = {"ok": f"{C_G}✔{C_0}", "att": f"{C_Y}▲{C_0}", "ko": f"{C_R}✖{C_0}"}[etat]
    print(f"  {marque} {libelle:<22} {valeur:<26} {C_D}{attendu}{C_0}")


def verifier(f, cible):
    if not os.path.isfile(f):
        sys.exit("Fichier introuvable : " + f)
    p = PLATEFORMES[cible]
    d = sonde(f)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    fmt = d["format"]

    print(f"\n{C_S}{os.path.basename(f)}{C_0}  ->  {C_S}{p['nom']}{C_0}\n")
    if not v:
        sys.exit("Aucune piste video.")

    pb = 0
    lv, hv = int(v["width"]), int(v["height"])
    if (lv, hv) == (p["l"], p["h"]):
        ligne("ok", "definition", f"{lv}x{hv}")
    elif abs(lv / hv - p["l"] / p["h"]) < 0.01:
        ligne("att", "definition", f"{lv}x{hv}", f"bon cadrage, vise {p['l']}x{p['h']}")
    else:
        ligne("ko", "definition", f"{lv}x{hv}", f"attendu {p['l']}x{p['h']} ({p['ratio']})"); pb += 1

    try:
        n, dd = v.get("r_frame_rate", "0/1").split("/")
        f_ips = round(int(n) / max(1, int(dd)))
    except Exception:
        f_ips = 0
    if f_ips in p["fps"]:
        ligne("ok", "images/seconde", str(f_ips))
    else:
        ligne("att", "images/seconde", str(f_ips), f"attendu {' ou '.join(map(str,p['fps']))}")

    c = v.get("codec_name", "?")
    ligne("ok" if c == "h264" else "ko", "codec video", c, "h264 attendu")
    pb += 0 if c == "h264" else 1

    px = v.get("pix_fmt", "?")
    ligne("ok" if px == "yuv420p" else "ko", "espace couleur", px,
          "yuv420p obligatoire")
    pb += 0 if px == "yuv420p" else 1

    pr = v.get("profile", "?")
    ligne("ok" if pr in ("High", "Main") else "att", "profil", pr, "High recommande")

    dur = float(fmt.get("duration", 0))
    mm = f"{int(dur//60)}:{int(dur%60):02d}"
    if p["duree_max"] and dur > p["duree_max"]:
        ligne("ko", "duree", mm, f"maximum {p['duree_max']//60} min"); pb += 1
    else:
        ligne("ok", "duree", mm, p["duree_conseil"])

    octets = int(fmt.get("size", 0))
    mo = octets / 1e6
    deb = octets * 8 / max(1e-6, dur) / 1e6
    bas, haut = p["debit"]
    if deb < bas * 0.6:
        ligne("att", "debit", f"{deb:.1f} Mb/s", f"un peu bas, vise {bas}-{haut}")
    elif deb > haut * 1.8:
        ligne("att", "debit", f"{deb:.1f} Mb/s", f"eleve, {bas}-{haut} suffit")
    else:
        ligne("ok", "debit", f"{deb:.1f} Mb/s", f"cible {bas}-{haut}")

    if p["taille_max_mo"] and mo > p["taille_max_mo"]:
        ligne("ko", "taille", f"{mo:.0f} Mo", p["taille_note"]); pb += 1
    else:
        ligne("ok", "taille", f"{mo:.0f} Mo", p["taille_note"])

    fs = faststart(f)
    if fs is True:
        ligne("ok", "faststart", "actif", "lecture immediate")
    elif fs is False:
        ligne("ko", "faststart", "absent",
              "reencode avec -movflags +faststart"); pb += 1
    else:
        ligne("att", "faststart", "indetermine")

    if not a:
        ligne("ko", "audio", "aucune piste", "AAC attendu"); pb += 1
    else:
        ac = a.get("codec_name", "?")
        ligne("ok" if ac == "aac" else "ko", "codec audio", ac, "aac attendu")
        pb += 0 if ac == "aac" else 1
        sr = int(a.get("sample_rate", 0))
        ligne("ok" if sr in (44100, 48000) else "att", "echantillonnage",
              f"{sr} Hz", "48000 recommande")
        ch = int(a.get("channels", 0))
        ligne("ok" if ch == 2 else "att", "canaux", str(ch), "stereo")

        i, pk = lufs(f)
        if i is None:
            ligne("att", "volume", "non mesure")
        elif -16.0 <= i <= -12.0:
            ligne("ok", "volume", f"{i:.1f} LUFS", "cible -14")
        else:
            sens = "trop fort, la plateforme baissera" if i > -12 else \
                   "trop faible, elle montera le bruit avec"
            ligne("att", "volume", f"{i:.1f} LUFS", sens)
        if pk is not None:
            ligne("ok" if pk <= -0.9 else "att", "crete vraie", f"{pk:.1f} dBTP",
                  "sous -1,0 dBTP : marge contre AAC")

    print()
    if pb == 0:
        print(f"  {C_G}{C_S}Conforme.{C_0} Publiable tel quel sur {p['nom']}.\n")
    else:
        print(f"  {C_R}{C_S}{pb} point(s) bloquant(s){C_0} pour {p['nom']}.\n")
    return pb


def afficher(cible=None):
    print(f"\n{C_S}{C_B}── Formats de publication ──{C_0}")
    print(f"{C_D}  Verifie le {VERIFIE_LE}. Les plateformes changent leurs limites :")
    print(f"  controle a la source avant une grosse production.{C_0}\n")
    for cle, p in PLATEFORMES.items():
        if cible and cle != cible:
            continue
        print(f"  {C_S}{p['nom']}{C_0}  {C_D}({cle}){C_0}")
        print(f"    {p['l']}x{p['h']} {p['ratio']}   "
              f"{' ou '.join(str(x) for x in p['fps'])} i/s   "
              f"{p['debit'][0]}-{p['debit'][1]} Mb/s")
        print(f"    duree {p['duree_conseil']}   ·   {p['taille_note']}")
        print(f"    {C_D}{p['source']}{C_0}\n")
    if cible:
        return
    print(f"{C_S}{C_B}── Codecs ──{C_0}{CODECS}")
    print(f"{C_S}{C_B}── Volume sonore ──{C_0}{LOUDNESS}")
    print(f"{C_S}{C_B}── Zones a ne pas encombrer ──{C_0}{ZONES}")


def main():
    ap = argparse.ArgumentParser(description="References techniques, hors ligne")
    ap.add_argument("plateforme", nargs="?", default=None,
                    choices=list(PLATEFORMES), help="n'afficher qu'une plateforme")
    ap.add_argument("--verifier", metavar="FICHIER",
                    help="controler un fichier produit")
    ap.add_argument("--pour", default="tiktok", choices=list(PLATEFORMES),
                    help="plateforme visee par la verification")
    a = ap.parse_args()
    if a.verifier:
        sys.exit(1 if verifier(a.verifier, a.pour) else 0)
    afficher(a.plateforme)


if __name__ == "__main__":
    main()
