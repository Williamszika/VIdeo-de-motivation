#!/usr/bin/env bash
# ============================================================
#  mz audio — extraction + mastering de la voix
#  Recupere l'audio d'une video (YouTube ou fichier local),
#  le nettoie et le calibre au niveau des plateformes.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz audio <source> [options]

  <source>   URL YouTube  ou  chemin d'un fichier local (mp4, mp3, wav…)

OPTIONS
  -o <fichier>   Fichier de sortie            (defaut: projet/02-audio/voix.wav)
  -d <debut>     Debut de la coupe   ex: 00:01:30  ou  90
  -f <fin>       Fin de la coupe     ex: 00:06:30  ou  390
  -t <duree>     Duree a garder en secondes (alternative a -f)
  -v <0..3>      Nettoyage de la voix : 0=aucun 1=leger 2=normal 3=fort  (defaut 2)
  -g <dB>        Gain manuel avant mastering (defaut 0)
  -l <LUFS>      Loudness cible              (defaut -14, standard TikTok)
  -k             Garder le fichier brut telecharge
  -c <fichier>   Fichier de cookies (format Netscape) — si YouTube demande
                 de confirmer que tu n'es pas un robot
  -C <navigateur> Prendre les cookies directement dans le navigateur :
                 chrome · firefox · edge · brave · opera · safari · chromium
  -h             Cette aide

EXEMPLES
  mz audio "https://youtu.be/XXXXXXXX"
  mz audio "https://youtu.be/XXXXXXXX" -d 00:00:45 -t 300 -o projet/02-audio/voix.wav
  mz audio discours.mp4 -v 3
EOU
}

OUT="$MZ_ROOT/projet/02-audio/voix.wav"
START=""; END=""; DUR=""; CLEAN=2; GAIN=0; TARGET="$MZ_LUFS"; KEEP=0
COOKIES=""; NAVIGATEUR=""
SRC="${1:-}"; [ -n "$SRC" ] && shift
case "$SRC" in -h|--help|"") usage; exit 0;; esac

while getopts "o:d:f:t:v:g:l:c:C:kh" opt; do
  case "$opt" in
    o) OUT="$OPTARG" ;;
    d) START="$OPTARG" ;;
    f) END="$OPTARG" ;;
    t) DUR="$OPTARG" ;;
    v) CLEAN="$OPTARG" ;;
    g) GAIN="$OPTARG" ;;
    l) TARGET="$OPTARG" ;;
    c) COOKIES="$OPTARG" ;;
    C) NAVIGATEUR="$OPTARG" ;;
    k) KEEP=1 ;;
    h) usage; exit 0 ;;
    *) usage; exit 1 ;;
  esac
done

need ffmpeg; need ffprobe
mkdir -p "$(dirname "$OUT")"
TMP=$(mz_tmpdir); trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------
# 1. Recuperation de la source
# ---------------------------------------------------------------
step "1/4  Recuperation de la source"
RAW=""
if [[ "$SRC" =~ ^https?:// ]]; then
  need yt-dlp

  AUTH=()
  [ -n "$COOKIES" ]    && { need_file "$COOKIES"; AUTH+=(--cookies "$COOKIES"); hint "cookies : $COOKIES"; }
  [ -n "$NAVIGATEUR" ] && { AUTH+=(--cookies-from-browser "$NAVIGATEUR"); hint "cookies pris dans : $NAVIGATEUR"; }

  # YouTube refuse parfois un client et en accepte un autre : on essaie
  # dans l'ordre jusqu'a ce que l'un passe.
  say "Telechargement de la piste audio…"
  for CLIENT in "" "web_safari" "tv_simply" "android" "mweb" "ios"; do
    EXTRA=()
    [ -n "$CLIENT" ] && EXTRA+=(--extractor-args "youtube:player_client=$CLIENT")
    yt-dlp -f "bestaudio/best" \
           --extract-audio --audio-format wav --audio-quality 0 \
           --no-playlist --no-warnings --progress \
           "${AUTH[@]}" "${EXTRA[@]}" \
           -o "$TMP/source.%(ext)s" "$SRC" >"$TMP/dl.log" 2>&1
    RAW=$(ls "$TMP"/source.* 2>/dev/null | head -1)
    if [ -n "$RAW" ]; then
      [ -n "$CLIENT" ] && hint "obtenu via le client « $CLIENT »"
      break
    fi
    [ -n "$CLIENT" ] && hint "client « $CLIENT » refuse — tentative suivante…"
  done

  if [ -z "$RAW" ]; then
    echo >&2
    tail -3 "$TMP/dl.log" >&2
    echo >&2
    if grep -qi "not a bot\|Sign in to confirm" "$TMP/dl.log"; then
      die "YouTube demande de confirmer que tu n'es pas un robot.

  Trois solutions, de la plus simple a la plus sure :

  1. Passe les cookies de ton navigateur — tu dois etre connecte a YouTube :
       mz audio \"$SRC\" -C chrome
     (remplace chrome par firefox, edge, brave, opera ou safari)

  2. Exporte tes cookies dans un fichier avec une extension
     « Get cookies.txt », puis :
       mz audio \"$SRC\" -c cookies.txt

  3. Telecharge la video a la main, puis lance le studio dessus :
       mz audio ma-video.mp4

  Ce blocage vise surtout les serveurs. Depuis ta connexion personnelle,
  la commande passe en general du premier coup."
    fi
    die "Le telechargement a echoue.
  Verifie l'URL, ou telecharge la video a la main puis relance sur le fichier."
  fi

  TITLE=$(yt-dlp --no-warnings --no-playlist "${AUTH[@]}" --print "%(title)s" "$SRC" 2>/dev/null | head -1)
  [ -n "$TITLE" ] && hint "Source : $TITLE"
else
  need_file "$SRC"
  RAW="$SRC"
fi
mz_has_audio "$RAW" || die "Aucune piste audio dans : $RAW"
ok "Source prete — duree $(mz_hms "$(mz_duration "$RAW")")"

# ---------------------------------------------------------------
# 2. Decoupe
# ---------------------------------------------------------------
step "2/4  Decoupe"
CUT="$TMP/cut.wav"
CUTARGS=()
[ -n "$START" ] && CUTARGS+=(-ss "$START")
if   [ -n "$DUR" ]; then CUTARGS+=(-t "$DUR")
elif [ -n "$END" ]; then CUTARGS+=(-to "$END"); fi

if [ ${#CUTARGS[@]} -gt 0 ]; then
  mz_ff "Coupe" ffmpeg -y -v error "${CUTARGS[@]}" -i "$RAW" \
        -vn -ac 2 -ar "$MZ_SR" -c:a pcm_s16le "$CUT" || die "Coupe impossible"
else
  mz_ff "Conversion" ffmpeg -y -v error -i "$RAW" \
        -vn -ac 2 -ar "$MZ_SR" -c:a pcm_s16le "$CUT" || die "Conversion impossible"
fi
ok "Segment retenu : $(mz_hms "$(mz_duration "$CUT")")"

# ---------------------------------------------------------------
# 3. Nettoyage + couleur de la voix
# ---------------------------------------------------------------
step "3/4  Nettoyage et couleur de la voix"
case "$CLEAN" in
  0) VOICE="anull" ;;
  1) VOICE="highpass=f=70,\
equalizer=f=250:t=q:w=1.0:g=-1.5,\
equalizer=f=3200:t=q:w=1.4:g=2,\
acompressor=threshold=-16dB:ratio=2.5:attack=20:release=220:makeup=1.5" ;;
  3) VOICE="highpass=f=95,lowpass=f=15000,\
afftdn=nf=-32:nt=w,\
equalizer=f=180:t=q:w=1.1:g=-4,\
equalizer=f=420:t=q:w=1.2:g=-2,\
equalizer=f=3000:t=q:w=1.3:g=4,\
equalizer=f=9500:t=h:g=3,\
acompressor=threshold=-22dB:ratio=4:attack=8:release=140:makeup=3,\
acompressor=threshold=-12dB:ratio=2:attack=30:release=300:makeup=1" ;;
  *) VOICE="highpass=f=85,\
afftdn=nf=-25:nt=w,\
equalizer=f=200:t=q:w=1.0:g=-2.5,\
equalizer=f=3000:t=q:w=1.2:g=3,\
equalizer=f=9000:t=h:g=2,\
acompressor=threshold=-18dB:ratio=3:attack=15:release=180:makeup=2" ;;
esac
[ "$GAIN" != "0" ] && VOICE="volume=${GAIN}dB,$VOICE"

CLEANED="$TMP/clean.wav"
mz_ff "Traitement" ffmpeg -y -v error -i "$CUT" -af "$VOICE" \
      -ac 2 -ar "$MZ_SR" -c:a pcm_s16le "$CLEANED" || die "Traitement audio impossible"
ok "Voix nettoyee (niveau $CLEAN)"

# ---------------------------------------------------------------
# 4. Loudness en deux passes (le vrai standard broadcast)
# ---------------------------------------------------------------
step "4/4  Calibration du volume (2 passes, cible ${TARGET} LUFS)"
say "Passe 1 — mesure…"
MEAS=$(ffmpeg -hide_banner -nostats -i "$CLEANED" \
   -af "loudnorm=I=${TARGET}:TP=${MZ_TP}:LRA=11:print_format=json" \
   -f null - 2>&1 | sed -n '/{/,/}/p')

get(){ printf '%s' "$MEAS" | grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 | sed 's/.*"\([^"]*\)"$/\1/'; }
MI=$(get input_i); MTP=$(get input_tp); MLRA=$(get input_lra); MTH=$(get input_thresh); MOFF=$(get target_offset)

if [ -n "$MI" ] && [ "$MI" != "-inf" ]; then
  hint "mesure : ${MI} LUFS  |  crete ${MTP} dBTP  |  dynamique ${MLRA} LU"
  LN="loudnorm=I=${TARGET}:TP=${MZ_TP}:LRA=11:measured_I=${MI}:measured_TP=${MTP}:measured_LRA=${MLRA}:measured_thresh=${MTH}:offset=${MOFF}:linear=true"
else
  warn "Mesure indisponible — passage en normalisation simple."
  LN="loudnorm=I=${TARGET}:TP=${MZ_TP}:LRA=11"
fi

say "Passe 2 — application…"
mz_ff "Mastering" ffmpeg -y -v error -i "$CLEANED" \
      -af "${LN},alimiter=limit=0.97:level=disabled" \
      -ac 2 -ar "$MZ_SR" -c:a pcm_s16le "$OUT" || die "Mastering impossible"

[ "$KEEP" = "1" ] && [ -n "$RAW" ] && [ -f "$RAW" ] && cp "$RAW" "$(dirname "$OUT")/" 2>/dev/null

FIN=$(mz_duration "$OUT")
VER=$(ffmpeg -hide_banner -nostats -i "$OUT" -af ebur128=framelog=quiet -f null - 2>&1 | grep -A3 "Integrated" | head -4 | tr -s ' ')
echo
ok "Audio pret : ${C_S}$OUT${C_0}"
hint "duree : $(mz_hms "$FIN")  ($FIN s)"
printf '%s\n' "$VER" | sed 's/^/  /'
echo
hint "Etape suivante :  mz broll   (preparer les images)"
