#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MZ STUDIO — generation d'images IA par theme

Un seul outil, plusieurs fournisseurs. Il lit les prompts produits par
make_prompts.py et ecrit les images directement dans le dossier du theme,
au bon format vertical.

Fournisseurs (choisis automatiquement selon les cles presentes) :
  fal         FAL_KEY            FLUX      ~0,04 $/image   rapide, tres bon
  replicate   REPLICATE_API_TOKEN FLUX     ~0,04 $/image
  openai      OPENAI_API_KEY     GPT Image ~0,04 $/image   suit bien les consignes
  stability   STABILITY_API_KEY  SD3       ~0,03 $/image
  comfyui     MZ_COMFYUI_URL     local     gratuit         demande un GPU
  procedural  aucune             calcule   gratuit         pas de photo

Rien n'est envoye nulle part tant qu'aucune cle n'est presente : sans cle,
l'outil bascule sur le generateur calcule du studio.
"""
import argparse, base64, json, os, sys, time, urllib.error, urllib.request

TIMEOUT = 300


# ------------------------------------------------------------------ reseau
def _poste(url, corps, entetes, brut=False, methode="POST"):
    donnees = corps if isinstance(corps, bytes) else json.dumps(corps).encode()
    req = urllib.request.Request(url, data=donnees, headers=entetes, method=methode)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        contenu = r.read()
    return contenu if brut else json.loads(contenu)


def _recupere(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        return r.read()


# ------------------------------------------------------------------ fournisseurs
def gen_fal(prompt, negatif, w, h, modele=None):
    cle = os.environ["FAL_KEY"]
    modele = modele or "fal-ai/flux-pro/v1.1-ultra"
    r = _poste(f"https://fal.run/{modele}",
               {"prompt": prompt, "aspect_ratio": "9:16",
                "image_size": "portrait_16_9", "num_images": 1,
                "output_format": "jpeg", "enable_safety_checker": True},
               {"Authorization": f"Key {cle}", "Content-Type": "application/json"})
    images = r.get("images") or []
    if not images:
        raise RuntimeError(f"fal n'a rien renvoye : {str(r)[:200]}")
    return _recupere(images[0]["url"])


def gen_replicate(prompt, negatif, w, h, modele=None):
    cle = os.environ["REPLICATE_API_TOKEN"]
    modele = modele or "black-forest-labs/flux-1.1-pro"
    r = _poste(f"https://api.replicate.com/v1/models/{modele}/predictions",
               {"input": {"prompt": prompt, "aspect_ratio": "9:16",
                          "output_format": "jpg", "safety_tolerance": 2}},
               {"Authorization": f"Bearer {cle}", "Content-Type": "application/json",
                "Prefer": "wait=120"})
    # en mode synchrone la sortie est deja la ; sinon on interroge jusqu'a la fin
    for _ in range(90):
        if r.get("status") == "succeeded":
            break
        if r.get("status") in ("failed", "canceled"):
            raise RuntimeError(f"replicate : {r.get('error') or r.get('status')}")
        time.sleep(2)
        req = urllib.request.Request(r["urls"]["get"],
                                     headers={"Authorization": f"Bearer {cle}"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as x:
            r = json.loads(x.read())
    sortie = r.get("output")
    url = sortie[0] if isinstance(sortie, list) else sortie
    if not url:
        raise RuntimeError("replicate n'a pas renvoye d'image")
    return _recupere(url)


def gen_openai(prompt, negatif, w, h, modele=None):
    cle = os.environ["OPENAI_API_KEY"]
    modele = modele or "gpt-image-1"
    r = _poste("https://api.openai.com/v1/images/generations",
               {"model": modele, "prompt": prompt, "size": "1024x1536", "n": 1},
               {"Authorization": f"Bearer {cle}", "Content-Type": "application/json"})
    d = (r.get("data") or [{}])[0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    if d.get("url"):
        return _recupere(d["url"])
    raise RuntimeError(f"openai n'a rien renvoye : {str(r)[:200]}")


def gen_stability(prompt, negatif, w, h, modele=None):
    cle = os.environ["STABILITY_API_KEY"]
    limite = "----mzstudio7f3a9"
    champs = {"prompt": prompt, "aspect_ratio": "9:16",
              "output_format": "jpeg", "negative_prompt": negatif[:900]}
    corps = b""
    for k, v in champs.items():
        corps += (f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                  f"{v}\r\n").encode()
    corps += f"--{limite}--\r\n".encode()
    return _poste("https://api.stability.ai/v2beta/stable-image/generate/core", corps,
                  {"Authorization": f"Bearer {cle}", "Accept": "image/*",
                   "Content-Type": f"multipart/form-data; boundary={limite}"}, brut=True)


def gen_comfyui(prompt, negatif, w, h, modele=None):
    """ComfyUI local : necessite un flux de travail expose en API.
    On envoie le prompt au point d'entree /prompt et on recupere l'image."""
    base = os.environ.get("MZ_COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    gabarit = os.environ.get("MZ_COMFYUI_WORKFLOW")
    if not gabarit or not os.path.isfile(gabarit):
        raise RuntimeError("ComfyUI : indique ton flux de travail au format API dans "
                           "MZ_COMFYUI_WORKFLOW (Enregistrer au format API dans ComfyUI)")
    wf = json.load(open(gabarit, encoding="utf-8"))
    # on remplit les champs marques {PROMPT}, {NEGATIF}, {W}, {H}
    txt = json.dumps(wf)
    txt = (txt.replace("{PROMPT}", json.dumps(prompt)[1:-1])
              .replace("{NEGATIF}", json.dumps(negatif)[1:-1])
              .replace("\"{W}\"", str(w)).replace("\"{H}\"", str(h)))
    wf = json.loads(txt)
    r = _poste(f"{base}/prompt", {"prompt": wf}, {"Content-Type": "application/json"})
    pid = r["prompt_id"]
    for _ in range(240):
        time.sleep(2)
        with urllib.request.urlopen(f"{base}/history/{pid}", timeout=60) as x:
            h_ = json.loads(x.read())
        if pid in h_:
            for noeud in h_[pid].get("outputs", {}).values():
                for im in noeud.get("images", []):
                    q = (f"{base}/view?filename={im['filename']}"
                         f"&subfolder={im.get('subfolder','')}&type={im.get('type','output')}")
                    return _recupere(q)
    raise RuntimeError("ComfyUI : delai depasse")


FOURNISSEURS = {
    "fal":       dict(fn=gen_fal,       cle="FAL_KEY",             cout=0.04, nom="FLUX (fal.ai)"),
    "replicate": dict(fn=gen_replicate, cle="REPLICATE_API_TOKEN", cout=0.04, nom="FLUX (Replicate)"),
    "openai":    dict(fn=gen_openai,    cle="OPENAI_API_KEY",      cout=0.04, nom="GPT Image (OpenAI)"),
    "stability": dict(fn=gen_stability, cle="STABILITY_API_KEY",   cout=0.03, nom="Stable Diffusion"),
    "comfyui":   dict(fn=gen_comfyui,   cle="MZ_COMFYUI_URL",      cout=0.00, nom="ComfyUI (local)"),
}
ORDRE = ["fal", "replicate", "openai", "stability", "comfyui"]


def detecte():
    for nom in ORDRE:
        if os.environ.get(FOURNISSEURS[nom]["cle"]):
            return nom
    return "procedural"


# ------------------------------------------------------------------ mise au format
def au_format(octets, chemin, w, h):
    """Recadre au format vertical exact et enregistre en JPEG."""
    from io import BytesIO
    from PIL import Image
    im = Image.open(BytesIO(octets)).convert("RGB")
    cible = w / h
    actuel = im.width / im.height
    if abs(actuel - cible) > 0.01:                    # recadre au centre
        if actuel > cible:
            nw = int(im.height * cible)
            im = im.crop(((im.width - nw) // 2, 0, (im.width + nw) // 2, im.height))
        else:
            nh = int(im.width / cible)
            im = im.crop((0, (im.height - nh) // 2, im.width, (im.height + nh) // 2))
    if im.width != w:
        im = im.resize((w, h), Image.LANCZOS)
    im.save(chemin, quality=94, subsampling=0)
    return im.size


# ------------------------------------------------------------------ programme
def main():
    ap = argparse.ArgumentParser(description="Genere les images d'un theme")
    ap.add_argument("--prompts", required=True, help="fichier .json produit par mz prompts")
    ap.add_argument("--fournisseur", default="auto",
                    choices=["auto", "procedural"] + ORDRE)
    ap.add_argument("--modele", default=None, help="forcer un modele du fournisseur")
    ap.add_argument("--w", type=int, default=2160)
    ap.add_argument("--h", type=int, default=3840)
    ap.add_argument("--outdir", default=None, help="par defaut : le dossier note dans le .json")
    ap.add_argument("--refaire", action="store_true", help="regenerer meme si le fichier existe")
    ap.add_argument("--tester", action="store_true", help="une seule image, pour valider la cle")
    ap.add_argument("--pause", type=float, default=0.8, help="secondes entre deux appels")
    a = ap.parse_args()

    if not os.path.isfile(a.prompts):
        sys.exit(f"Introuvable : {a.prompts}")
    d = json.load(open(a.prompts, encoding="utf-8"))
    images = d["images"][:1] if a.tester else d["images"]
    dest = a.outdir or d.get("dossier_cible") or "projet/03-broll"
    os.makedirs(dest, exist_ok=True)

    f = a.fournisseur if a.fournisseur != "auto" else detecte()

    # --- pas de cle : on retombe sur le generateur calcule du studio
    if f == "procedural":
        if a.fournisseur == "auto":
            print("Aucune cle d'API detectee — bascule sur les fonds calcules du studio.")
            print("Pour de la photo IA, definis une cle :  FAL_KEY, REPLICATE_API_TOKEN,")
            print("OPENAI_API_KEY ou STABILITY_API_KEY.  Details : docs/05-IMAGES-IA.md\n")
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.execv(sys.executable, [sys.executable,
                 os.path.join(racine, "tools", "make_backdrop.py"),
                 "--ambiance", d.get("ambiance") or "aube_froide",
                 "--n", str(len(images)), "--outdir", dest,
                 "--w", str(a.w), "--h", str(a.h),
                 "--prefixe", d.get("theme", "fond")])

    info = FOURNISSEURS[f]
    if not os.environ.get(info["cle"]):
        sys.exit(f"Le fournisseur « {f} » demande la variable {info['cle']}.\n"
                 f"  export {info['cle']}=...\n  Details : docs/05-IMAGES-IA.md")

    print(f"theme       : {d.get('theme')}  —  {d.get('titre','')}")
    print(f"fournisseur : {info['nom']}")
    print(f"destination : {dest}")
    print(f"format      : {a.w}x{a.h}")
    if info["cout"]:
        print(f"cout estime : environ {len(images)*info['cout']:.2f} $ "
              f"pour {len(images)} image(s)")
    print()

    faites, sautees, ratees = 0, 0, 0
    for i, im in enumerate(images, 1):
        nom = os.path.splitext(im["fichier"])[0] + ".jpg"
        chemin = os.path.join(dest, nom)
        if os.path.exists(chemin) and not a.refaire:
            print(f"  [{i:2d}/{len(images)}] {nom:<34} deja la")
            sautees += 1
            continue
        derniere = None
        for essai in range(3):
            try:
                t0 = time.time()
                octets = info["fn"](im["prompt"], im.get("negatif", ""), a.w, a.h, a.modele)
                taille = au_format(octets, chemin, a.w, a.h)
                print(f"  [{i:2d}/{len(images)}] {nom:<34} {taille[0]}x{taille[1]}  "
                      f"{os.path.getsize(chemin)/1e6:.1f} Mo  {time.time()-t0:.0f}s")
                faites += 1
                derniere = None
                break
            except urllib.error.HTTPError as e:
                corps = e.read()[:220].decode("utf-8", "replace")
                derniere = f"HTTP {e.code} — {corps}"
                if e.code in (401, 403):
                    print(f"\n  cle refusee : {derniere}")
                    sys.exit(1)
                time.sleep(3 * (essai + 1))
            except Exception as e:
                derniere = str(e)[:220]
                time.sleep(3 * (essai + 1))
        if derniere:
            print(f"  [{i:2d}/{len(images)}] {nom:<34} ECHEC — {derniere}")
            ratees += 1
        time.sleep(a.pause)

    print(f"\n{faites} generee(s), {sautees} deja presente(s), {ratees} en echec")
    if info["cout"] and faites:
        print(f"cout reel approximatif : {faites*info['cout']:.2f} $")
    if faites or sautees:
        print(f"\nVerifie :  ./mz plans {dest}")


if __name__ == "__main__":
    main()
