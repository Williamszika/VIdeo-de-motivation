#!/usr/bin/env bash
# ============================================================
#  mz images — images IA par theme
#  Ecrit les prompts a partir de themes.json, puis les execute
#  chez le fournisseur configure. Sans cle : fonds calcules.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz images [options]

Lit projet/themes.json, redige un prompt par image en tenant compte du
sujet ET de l'ambiance du theme, puis genere les images dans
projet/03-broll/<theme>/.

OPTIONS
  -t <theme>     Ne traiter qu'un theme (son identifiant)
  -n <nombre>    Images par theme                     (defaut 14)
  -f <fourni>    auto · fal · replicate · openai · stability · comfyui · procedural
  -m <modele>    Forcer un modele du fournisseur
  -r <format>    2k · 4k · 8k                          (defaut 4k)
  -P             Ecrire seulement les prompts, ne rien generer
  -T             Essai : une seule image, pour valider ta cle
  -F             Regenerer meme si le fichier existe
  -h             Cette aide

CLES RECONNUES  (la premiere trouvee gagne)
  FAL_KEY               FLUX chez fal.ai        ~0,04 $/image
  REPLICATE_API_TOKEN   FLUX chez Replicate     ~0,04 $/image
  OPENAI_API_KEY        GPT Image               ~0,04 $/image
  STABILITY_API_KEY     Stable Diffusion        ~0,03 $/image
  MZ_COMFYUI_URL        ComfyUI en local        gratuit, demande un GPU

Sans aucune cle, le studio fabrique ses propres fonds : c'est gratuit et
ca ne part sur aucun serveur.

EXEMPLES
  mz images -P                    juste les prompts, a executer ailleurs
  mz images -T                    une image, pour verifier que la cle marche
  mz images -n 16 -r 4k           tout generer
  mz images -t 02-peur-echec -F   refaire un seul theme
EOU
}

SEUL=""; N=14; FOURNISSEUR="auto"; MODELE=""; RES="4k"
PROMPTS_SEULS=0; TEST=0; REFAIRE=0
THEMES="$MZ_ROOT/projet/themes.json"
PDIR="$MZ_ROOT/projet/prompts"

while getopts "t:n:f:m:r:PTFh" opt; do
  case "$opt" in
    t) SEUL="$OPTARG" ;; n) N="$OPTARG" ;; f) FOURNISSEUR="$OPTARG" ;;
    m) MODELE="$OPTARG" ;; r) RES="$OPTARG" ;;
    P) PROMPTS_SEULS=1 ;; T) TEST=1 ;; F) REFAIRE=1 ;;
    h) usage; exit 0 ;; *) usage; exit 1 ;;
  esac
done

need python3
[ -f "$THEMES" ] || die "Aucun theme : $THEMES
  Produis-les d'abord :  ./mz ecoute <fichier>   puis   ./mz themes"

case "$RES" in 2k) W=1080; H=1920 ;; 8k) W=4320; H=7680 ;; *) W=2160; H=3840 ;; esac

# ---------------------------------------------------------------
step "1/2  Redaction des prompts"
ARGS=(--themes "$THEMES" --outdir "$PDIR" --n "$N" --cible "$MZ_ROOT/projet/03-broll")
[ -n "$SEUL" ] && ARGS+=(--theme "$SEUL")
python3 "$MZ_TOOLS/make_prompts.py" "${ARGS[@]}" || die "Prompts impossibles"

if [ "$PROMPTS_SEULS" = "1" ]; then
  echo
  ok "Prompts prets — rien n'a ete genere."
  hint "Ouvre  $PDIR/LISEZ-MOI.md"
  hint "Avec OpenMontage : demande-lui d'executer les .json de ce dossier."
  exit 0
fi

# ---------------------------------------------------------------
step "2/2  Generation des images"
mapfile -t FICHIERS < <(find "$PDIR" -maxdepth 1 -name '*.json' | LC_ALL=C sort)
[ ${#FICHIERS[@]} -gt 0 ] || die "Aucun fichier de prompts dans $PDIR"

TOTAL=0; ECHECS=0
for J in "${FICHIERS[@]}"; do
  ID=$(basename "$J" .json)
  echo
  say "${C_S}$ID${C_0}"
  G=(--prompts "$J" --fournisseur "$FOURNISSEUR" --w "$W" --h "$H")
  [ -n "$MODELE" ] && G+=(--modele "$MODELE")
  [ "$TEST" = "1" ]    && G+=(--tester)
  [ "$REFAIRE" = "1" ] && G+=(--refaire)
  if python3 "$MZ_TOOLS/generer_images.py" "${G[@]}"; then
    TOTAL=$((TOTAL+1))
  else
    ECHECS=$((ECHECS+1))
    warn "echec sur $ID"
    [ "$TEST" = "1" ] && break
  fi
done

echo
[ "$ECHECS" -eq 0 ] && ok "$TOTAL theme(s) traite(s)" || warn "$ECHECS theme(s) en echec"
if [ "$TEST" = "1" ]; then
  hint "Essai termine. Si l'image est bonne :  ./mz images -n $N -r $RES"
else
  hint "Verifie :  ./mz plans projet/03-broll/<theme>"
  hint "Puis monte :  ./mz serie -S     (-S = ne pas refabriquer de fonds)"
fi
