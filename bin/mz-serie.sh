#!/usr/bin/env bash
# ============================================================
#  mz serie — produit toutes les videos d'un coup
#  Lit projet/parties/plan.tsv et, pour chaque partie :
#    coupe la voix -> genere les fonds -> assemble la video.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz serie [options]

Produit une video de 5 minutes par partie decrite dans
projet/parties/plan.tsv (ecrit par : mz decouper).

OPTIONS
  -p <plan>     feuille de route      (defaut projet/parties/plan.tsv)
  -s <source>   fichier d'origine     (defaut : celui note dans le plan)
  -t <theme>    ne traiter qu'un theme (son identifiant)
  -n <nombre>   fonds generes par theme          (defaut 18)
  -r <format>   definition des fonds : 2k · 4k · 8k   (defaut 4k)
  -q <crf>      qualite d'encodage               (defaut 19)
  -F            regenerer les fonds meme s'ils existent
  -S            sauter la generation des fonds (tu fournis tes images)
  -e            essai a blanc : montre ce qui serait produit
  -h            Cette aide

EXEMPLES
  mz serie -e                        voir le programme sans rien calculer
  mz serie                           tout produire
  mz serie -t 02-discipline -r 8k    un seul theme, fonds en 8K
EOU
}

PLAN="$MZ_ROOT/projet/parties/plan.tsv"
SOURCE=""; SEUL=""; NFONDS=18; RES="4k"; CRF=19
FORCE_FONDS=0; SANS_FONDS=0; ESSAI=0

while getopts "p:s:t:n:r:q:FSeh" opt; do
  case "$opt" in
    p) PLAN="$OPTARG" ;; s) SOURCE="$OPTARG" ;; t) SEUL="$OPTARG" ;;
    n) NFONDS="$OPTARG" ;; r) RES="$OPTARG" ;; q) CRF="$OPTARG" ;;
    F) FORCE_FONDS=1 ;; S) SANS_FONDS=1 ;; e) ESSAI=1 ;;
    h) usage; exit 0 ;; *) usage; exit 1 ;;
  esac
done

need ffmpeg; need python3
[ -f "$PLAN" ] || die "Feuille de route introuvable : $PLAN
  Produis-la d'abord :  ./mz decouper"

[ -z "$SOURCE" ] && SOURCE=$(grep -m1 '^#source' "$PLAN" | cut -f2)
[ -n "$SOURCE" ] && [ -f "$SOURCE" ] || die "Fichier d'origine introuvable : ${SOURCE:-<vide>}
  Indique-le :  ./mz serie -s ma-video.mp4"

# La signature est refabriquee seulement quand la palette change d'un theme
# a l'autre : elle coute ~90 s, inutile de la refaire a chaque partie.
MARQUE="$MZ_BRAND/.palette"
assure_signature() {
  local voulue="${1:-or}" actuelle=""
  [ -f "$MARQUE" ] && actuelle=$(cat "$MARQUE" 2>/dev/null)
  if [ ! -f "$MZ_BRAND/intro_signature.mov" ] || [ "$actuelle" != "$voulue" ]; then
    say "signature Mr ZIKA — palette $voulue"
    bash "$MZ_ROOT/bin/mz-brand.sh" -c "$voulue" >/dev/null 2>&1 \
      || { warn "signature impossible en $voulue"; return 1; }
    printf '%s' "$voulue" > "$MARQUE"
    ok "signature prete"
  fi
  return 0
}

CACHE_SERIE="$MZ_ROOT/projet/.cache/journaux"
mkdir -p "$CACHE_SERIE"
mapfile -t LIGNES < <(grep -v '^#' "$PLAN" | grep -v '^[[:space:]]*$')
[ ${#LIGNES[@]} -gt 0 ] || die "La feuille de route est vide."

step "Serie — ${#LIGNES[@]} video(s) au programme"
hint "source : $(basename "$SOURCE")"

# ---------- programme ----------
TOTAL=0
for L in "${LIGNES[@]}"; do
  IFS=$'\t' read -r ID PARTIE DEBUT DUREE SRT AMB LOOK PAL PSEC TEX TRANS TITRE <<< "$L"
  [ -n "$SEUL" ] && [ "$ID" != "$SEUL" ] && continue
  TOTAL=$((TOTAL+1))
  printf '  %s%-26s%s partie %s  %6.1fs  %-12s %-11s %s\n' \
    "$C_S" "$ID" "$C_0" "$PARTIE" "$DUREE" "$AMB" "$LOOK" "$TITRE"
done
[ "$TOTAL" -gt 0 ] || die "Aucune partie ne correspond${SEUL:+ au theme « $SEUL »}."
echo
hint "$TOTAL video(s) — compte environ $((TOTAL * 20)) minutes de calcul"

if [ "$ESSAI" = "1" ]; then
  echo; ok "Essai a blanc : rien n'a ete calcule."
  exit 0
fi

# ---------- production ----------
FAITES=0; RATEES=0
for L in "${LIGNES[@]}"; do
  IFS=$'\t' read -r ID PARTIE DEBUT DUREE SRT AMB LOOK PAL PSEC TEX TRANS TITRE <<< "$L"
  [ -n "$SEUL" ] && [ "$ID" != "$SEUL" ] && continue

  NUM=$((FAITES + RATEES + 1))
  step "[$NUM/$TOTAL]  $ID · partie $PARTIE"
  [ -n "$TITRE" ] && hint "$TITRE"

  VOIX="$MZ_ROOT/projet/02-audio/${ID}-p${PARTIE}.wav"
  BROLL="$MZ_ROOT/projet/03-broll/${ID}"
  RENDU="$MZ_ROOT/projet/04-rendu/${ID}-p${PARTIE}.mp4"

  # --- 1. la voix : coupe puis mastering complet
  if [ ! -s "$VOIX" ]; then
    say "voix — coupe a $(mz_hms "$DEBUT") sur ${DUREE}s"
    bash "$MZ_ROOT/bin/mz-audio.sh" "$SOURCE" -d "$DEBUT" -t "$DUREE" -o "$VOIX" \
      >/dev/null 2>&1 || { warn "voix impossible pour $ID p$PARTIE"; RATEES=$((RATEES+1)); continue; }
    ok "voix prete ($(mz_hms "$(mz_duration "$VOIX")"))"
  else
    hint "voix deja presente — conservee"
  fi

  # --- 2. les fonds, une serie par theme
  if [ "$SANS_FONDS" = "0" ]; then
    EXISTE=$(find "$BROLL" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.png' \) 2>/dev/null | wc -l)
    if [ "$FORCE_FONDS" = "1" ] || [ "$EXISTE" -lt 6 ]; then
      say "fonds — ambiance $AMB"
      [ "$FORCE_FONDS" = "1" ] && rm -f "$BROLL"/*.jpg 2>/dev/null
      bash "$MZ_ROOT/bin/mz-fonds.sh" -a "$AMB" -n "$NFONDS" -o "$BROLL" -r "$RES" \
        -g "$((10#$(printf '%s' "$ID" | cksum | cut -d' ' -f1) % 100000))" \
        >/dev/null 2>&1 || { warn "fonds impossibles pour $ID"; RATEES=$((RATEES+1)); continue; }
      ok "$NFONDS fonds generes"
    else
      hint "$EXISTE fonds deja presents — reutilises"
    fi
  fi
  [ -d "$BROLL" ] || { warn "pas d'images pour $ID"; RATEES=$((RATEES+1)); continue; }

  # --- 3. la signature a la couleur du theme
  assure_signature "${PAL:-or}" || { RATEES=$((RATEES+1)); continue; }

  # --- 4. le montage
  say "montage — $LOOK / $TEX / $TRANS, plans de ${PSEC}s"
  # On garde le statut du montage a part : avec pipefail, juger un « if » sur
  # un pipeline (build | grep | tail) fait passer un succes pour un echec des
  # que grep ne trouve rien a afficher.
  JOURNAL="$CACHE_SERIE/${ID}-p${PARTIE}.log"
  bash "$MZ_ROOT/bin/mz-build.sh" \
       -a "$VOIX" -b "$BROLL" -s "$SRT" -o "$RENDU" \
       -d "$(printf '%.0f' "$DUREE")" -l "$LOOK" -x "$TEX" -T "$TRANS" \
       -p "$PSEC" -q "$CRF" > "$JOURNAL" 2>&1
  ETAT=$?
  grep -vE '^frame=|fps=|^[[:space:]]*$' "$JOURNAL" | tail -3
  if [ "$ETAT" -eq 0 ] && [ -s "$RENDU" ]; then
    ok "$(basename "$RENDU")  ·  $(du -h "$RENDU" 2>/dev/null | cut -f1)"
    FAITES=$((FAITES+1))
  else
    warn "montage rate pour $ID partie $PARTIE — detail : $JOURNAL"
    RATEES=$((RATEES+1))
  fi
done

echo
step "Bilan"
ok "$FAITES video(s) produite(s) dans projet/04-rendu/"
[ "$RATEES" -gt 0 ] && warn "$RATEES echec(s)"
ls -1sh "$MZ_ROOT/projet/04-rendu"/*.mp4 2>/dev/null | tail -20 | sed 's/^/  /'
echo
hint "Publication : docs/03-TIKTOK.md"
