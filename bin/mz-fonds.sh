#!/usr/bin/env bash
# ============================================================
#  mz fonds — genere des images de fond cinematographiques
#  Tout est calcule : aucune photo, aucun droit a verifier.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz fonds [options]

OPTIONS
  -a <ambiance>  aube_froide · braise · heure_doree · nuit_neon ·
                 orage · sommet · vide          (defaut aube_froide)
  -n <nombre>    combien d'images                (defaut 18)
  -o <dossier>   ou les ecrire                   (defaut projet/03-broll)
  -r <format>    2k · 4k · 8k                    (defaut 4k)
                   2k = 1080x1920    leger, pour essayer
                   4k = 2160x3840    recommande
                   8k = 4320x7680    zoom profond, fichiers lourds
  -m <motif>     forcer : cretes · cretes_figure · ville · ville_figure ·
                 route · mer · vide · vide_figure
  -g <graine>    change tout le tirage           (defaut 0)
  -l             lister les ambiances
  -h             Cette aide

EXEMPLES
  mz fonds -l
  mz fonds -a braise -n 20 -r 4k
  mz fonds -a sommet -n 12 -r 8k -o projet/03-broll/01-reussite
EOU
}

AMB="aube_froide"; N=18; OUT="$MZ_ROOT/projet/03-broll"; RES="4k"; MOTIF=""; GRAINE=0
while getopts "a:n:o:r:m:g:lh" opt; do
  case "$opt" in
    a) AMB="$OPTARG" ;; n) N="$OPTARG" ;; o) OUT="$OPTARG" ;; r) RES="$OPTARG" ;;
    m) MOTIF="$OPTARG" ;; g) GRAINE="$OPTARG" ;;
    l) python3 "$MZ_TOOLS/make_backdrop.py" --liste; exit 0 ;;
    h) usage; exit 0 ;; *) usage; exit 1 ;;
  esac
done

need python3
python3 -c "import numpy, PIL" 2>/dev/null || die "numpy et pillow sont requis — relance ./install.sh"

case "$RES" in
  2k) W=1080; H=1920 ;;
  8k) W=4320; H=7680 ;;
  *)  W=2160; H=3840 ;;
esac

step "Fonds — ambiance $AMB, ${N} images en ${W}x${H}"
[ "$RES" = "8k" ] && hint "8K : environ 8 a 12 Mo par image et 25 s de calcul chacune"
mkdir -p "$OUT"

ARGS=(--ambiance "$AMB" --n "$N" --outdir "$OUT" --w "$W" --h "$H" --seed "$GRAINE")
[ -n "$MOTIF" ] && ARGS+=(--motif "$MOTIF")
python3 "$MZ_TOOLS/make_backdrop.py" "${ARGS[@]}" || die "Generation impossible"

echo
ok "$N fonds ecrits dans $OUT"
hint "Verifie-les :  ./mz plans $OUT"
