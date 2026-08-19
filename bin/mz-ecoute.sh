#!/usr/bin/env bash
# ============================================================
#  mz ecoute — transcrit une video ou un audio (Whisper)
#  Produit la base de tout le reste : sous-titres cales au mot
#  et matiere pour le decoupage en themes.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz ecoute <fichier> [options]

  <fichier>   ta video ou ton audio (mp4, mov, mkv, mp3, wav, m4a…)

OPTIONS
  -m <modele>  tiny · base · small · medium · large-v3 · large-v3-turbo
               (defaut large-v3-turbo : le meilleur rapport vitesse/qualite)
  -l <langue>  fr par defaut, ou 'auto' pour laisser detecter
  -o <prefixe> defaut : projet/02-audio/transcription
  -h           Cette aide

RESULTAT
  transcription.json   segments + mots horodates  (lu par les outils)
  transcription.srt    sous-titres standard
  transcription.txt    texte minute par minute, a relire

DUREE  environ la moitie de la duree du fichier sur 4 coeurs.
       Le premier lancement telecharge le modele (~1,5 Go pour turbo).

ENSUITE
  ./mz themes        propose un decoupage en sujets
EOU
}

SRC="${1:-}"; [ -n "$SRC" ] && shift
case "$SRC" in -h|--help|"") usage; exit 0;; esac

MODELE="large-v3-turbo"; LANGUE="fr"; OUT="$MZ_ROOT/projet/02-audio/transcription"
while getopts "m:l:o:h" opt; do
  case "$opt" in
    m) MODELE="$OPTARG" ;; l) LANGUE="$OPTARG" ;; o) OUT="$OPTARG" ;;
    h) usage; exit 0 ;; *) usage; exit 1 ;;
  esac
done

need python3; need ffmpeg
need_file "$SRC"
python3 -c "import faster_whisper" 2>/dev/null || die "faster-whisper n'est pas installe.
  pip install faster-whisper
  (ou relance ./install.sh)"

mz_has_audio "$SRC" || die "Aucune piste audio dans : $SRC"
DUR=$(mz_duration "$SRC")

step "Ecoute — $(basename "$SRC")"
hint "duree $(mz_hms "$DUR")  ·  modele $MODELE  ·  langue $LANGUE"
hint "compte environ $(mz_hms "$(awk -v d="$DUR" 'BEGIN{print d/2}')") de calcul"
mkdir -p "$(dirname "$OUT")"

python3 "$MZ_TOOLS/transcrire.py" "$SRC" --out "$OUT" \
        --modele "$MODELE" --langue "$LANGUE" || die "Transcription impossible"

echo
ok "Transcription terminee"
hint "Relis  ${OUT}.txt  puis lance :  ./mz themes"
