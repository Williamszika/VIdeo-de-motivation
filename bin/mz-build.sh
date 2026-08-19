#!/usr/bin/env bash
# ============================================================
#  mz build — assemble la video finale
#  Chaine : plans -> etalonnage -> texture -> montage ->
#           sous-titres -> signature -> son -> export TikTok
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
source "$MZ_ROOT/lib/grades.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz build [options]

ENTREES (par defaut)
  projet/02-audio/voix.wav      la voix (produite par : mz audio)
  projet/02-audio/musique.*     musique de fond, facultative
  projet/03-broll/              tes images et clips (jpg, png, mp4, mov…)
  projet/script.txt             le texte des sous-titres, facultatif

OPTIONS
  -a <fichier>  Voix
  -m <fichier>  Musique de fond
  -b <dossier>  Dossier des plans
  -s <fichier>  Sous-titres : un .txt (*mot* = mis en avant) ou un .srt deja cale
  -o <fichier>  Video de sortie
  -d <sec>      Duree exacte              (defaut 300 = 5 min ; "auto" = duree de la voix)
  -l <look>     orange_teal ice fire gold noir cyber raw   (defaut orange_teal)
  -x <texture>  aucun doux normal fort                     (defaut normal)
  -T <transi>   coupe flash noir fondu                     (defaut coupe)
  -p <sec>      Duree d'un plan                            (defaut 6)
  -v <vol>      Volume de la musique en dB                 (defaut -19)
  -f <taille>   Taille des sous-titres en px               (defaut 112)
  -w <mots>     Mots par groupe de sous-titres             (defaut 3)
  -k <0|1>      Filigrane permanent Mr ZIKA                (defaut 1)
  -q <crf>      Qualite : 16 excellente, 20 legere         (defaut 19)
  -N            Sans sous-titres
  -I            Sans intro / carte de fin
  -R            Refaire les plans (ignorer le cache)
  -h            Cette aide

EXEMPLE
  mz build -l fire -x fort -T flash -p 4.5
EOU
}

AUDIO="$MZ_ROOT/projet/02-audio/voix.wav"
MUSIQUE=""
BROLL="$MZ_ROOT/projet/03-broll"
SCRIPT="$MZ_ROOT/projet/script.txt"
SORTIE=""
DUREE="$MZ_DUR"
LOOK="orange_teal"; TEXTURE="normal"; TRANSI="coupe"
SEG="6"; MVOL="-19"; SUBSZ="112"; SUBW="3"
FILIGRANE="1"; CRF="19"; NOSUBS=0; NOBRAND=0; REFAIRE=0

while getopts "a:m:b:s:o:d:l:x:T:p:v:f:w:k:q:NIRh" opt; do
  case "$opt" in
    a) AUDIO="$OPTARG" ;;   m) MUSIQUE="$OPTARG" ;;  b) BROLL="$OPTARG" ;;
    s) SCRIPT="$OPTARG" ;;  o) SORTIE="$OPTARG" ;;   d) DUREE="$OPTARG" ;;
    l) LOOK="$OPTARG" ;;    x) TEXTURE="$OPTARG" ;;  T) TRANSI="$OPTARG" ;;
    p) SEG="$OPTARG" ;;     v) MVOL="$OPTARG" ;;     f) SUBSZ="$OPTARG" ;;
    w) SUBW="$OPTARG" ;;    k) FILIGRANE="$OPTARG" ;; q) CRF="$OPTARG" ;;
    N) NOSUBS=1 ;;          I) NOBRAND=1 ;;          R) REFAIRE=1 ;;
    h) usage; exit 0 ;;     *) usage; exit 1 ;;
  esac
done

need ffmpeg; need ffprobe; need python3

# ---------------------------------------------------------------
step "Verification"
[ -f "$AUDIO" ] || die "Voix introuvable : $AUDIO
  Produis-la d'abord :  mz audio <url ou fichier>"
[ -d "$BROLL" ] || die "Dossier des plans introuvable : $BROLL"

mapfile -t PLANS < <(find "$BROLL" -maxdepth 1 -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \
     -o -iname '*.mp4' -o -iname '*.mov' -o -iname '*.mkv' -o -iname '*.webm' -o -iname '*.m4v' \) \
  | LC_ALL=C sort)
NP=${#PLANS[@]}
[ "$NP" -gt 0 ] || die "Aucune image ni clip dans $BROLL
  Depose au moins 8 fichiers (voir docs/01-GUIDE-TOURNAGE.md)"

VDUR=$(mz_duration "$AUDIO")
if [ "$DUREE" = "auto" ]; then DUREE=$(awk -v d="$VDUR" 'BEGIN{printf "%.0f", d}'); fi

if [ -z "$MUSIQUE" ]; then
  MUSIQUE=$(find "$MZ_ROOT/projet/02-audio" -maxdepth 1 -type f \
    \( -iname 'musique.*' -o -iname 'music.*' \) 2>/dev/null | head -1)
fi

NSEG=$(awk -v d="$DUREE" -v s="$SEG" 'BEGIN{printf "%d", (d/s)+0.999}')
[ "$NSEG" -lt 1 ] && NSEG=1

ok "$NP source(s) de plans  ->  $NSEG plans de ${SEG}s"
ok "voix : $(mz_hms "$VDUR")   |   video : $(mz_hms "$DUREE")"
[ -n "$MUSIQUE" ] && ok "musique : $(basename "$MUSIQUE") a ${MVOL} dB"
awk -v v="$VDUR" -v d="$DUREE" 'BEGIN{
  if (v < d-2) printf "▲ la voix est plus courte que la video de %.0f s : du silence sera ajoute a la fin.\n", d-v;
  if (v > d+2) printf "▲ la voix depasse la video de %.0f s : elle sera coupee (fondu de sortie).\n", v-d;
}' >&2

# L'empreinte couvre tout ce qui change l'image d'un plan. Deux videos aux
# reglages differents ne peuvent donc pas se voler leurs plans en cache.
CLE=$( { printf '%s|%s|%s|%s|%s|%sx%s@%s\n' "$LOOK" "$TEXTURE" "$TRANSI" "$SEG" "$DUREE" "$MZ_W" "$MZ_H" "$MZ_FPS"
         printf '%s\n' "${PLANS[@]}"; } | cksum | cut -d' ' -f1)
CACHE="${MZ_CACHE:-$MZ_ROOT/projet/.cache/$CLE}"
mkdir -p "$CACHE/plans" "$MZ_ROOT/projet/04-rendu"
[ "$REFAIRE" = "1" ] && rm -f "$CACHE/plans/"*.mp4
[ -z "$SORTIE" ] && SORTIE="$MZ_ROOT/projet/04-rendu/MrZIKA_$(date +%Y%m%d-%H%M).mp4"

GRADE=$(mz_grade "$LOOK")
TEXT=$(mz_fx_texture "$TEXTURE")
hint "look : $LOOK — $(mz_look_desc "$LOOK")"

case "$TRANSI" in coupe|flash|noir|fondu) ;; *) TRANSI="coupe" ;; esac

# ---------------------------------------------------------------
step "1/5  Fabrication des $NSEG plans (etalonnage $LOOK, texture $TEXTURE)"

JOBS="$CACHE/jobs.txt"; : > "$JOBS"
for ((k=0; k<NSEG; k++)); do
  printf '%s\n' "$k" >> "$JOBS"
done

# --- script de rendu d'un plan (appele en parallele) ---
cat > "$CACHE/render_seg.sh" <<'EOSEG'
#!/usr/bin/env bash
source "$MZ_ROOT/lib/common.sh"
source "$MZ_ROOT/lib/grades.sh"
k="$1"
OUTF="$CACHE/plans/$(printf '%04d' "$k").mp4"
[ -s "$OUTF" ] && exit 0

IFS=$'\n' read -r -d '' -a PLANS < <(cat "$CACHE/liste.txt" && printf '\0')
NP=${#PLANS[@]}
SRC="${PLANS[$((k % NP))]}"
CYCLE=$(( k / NP ))                      # 0,1,2… : varie a chaque passage
KIND=$(mz_kind "$SRC")

# --- mouvement de camera : alterne pour ne jamais se repeter
DIRZ=$(( (k + CYCLE) % 4 ))
case "$DIRZ" in
  0) ZEXPR="1+0.11*on/(${SEG}*${MZ_FPS})";        PX="iw/2-(iw/zoom/2)";                 PY="ih/2-(ih/zoom/2)" ;;
  1) ZEXPR="1.11-0.11*on/(${SEG}*${MZ_FPS})";     PX="iw/2-(iw/zoom/2)";                 PY="ih/2-(ih/zoom/2)" ;;
  2) ZEXPR="1.06+0.06*on/(${SEG}*${MZ_FPS})";     PX="(iw-iw/zoom)*on/(${SEG}*${MZ_FPS})"; PY="ih/2-(ih/zoom/2)" ;;
  3) ZEXPR="1.06+0.06*on/(${SEG}*${MZ_FPS})";     PX="(iw-iw/zoom)*(1-on/(${SEG}*${MZ_FPS}))"; PY="ih/2-(ih/zoom/2)" ;;
esac

FRAMES=$(awk -v s="$SEG" -v f="$MZ_FPS" 'BEGIN{printf "%d", s*f}')
PRE_W=$((MZ_W*2)); PRE_H=$((MZ_H*2))

INARGS=(); PREP=""
if [ "$KIND" = "image" ]; then
  INARGS=(-loop 1 -framerate "$MZ_FPS" -t "$SEG" -i "$SRC")
  PREP="scale=${PRE_W}:${PRE_H}:force_original_aspect_ratio=increase,crop=${PRE_W}:${PRE_H},\
zoompan=z='${ZEXPR}':x='${PX}':y='${PY}':d=${FRAMES}:s=${MZ_W}x${MZ_H}:fps=${MZ_FPS}"
else
  SDUR=$(mz_duration "$SRC"); SDUR=${SDUR:-0}
  OFF=$(awk -v d="$SDUR" -v s="$SEG" -v c="$CYCLE" -v k="$k" 'BEGIN{
    u = d - s; if (u <= 0) { print 0; exit }
    # point de depart different a chaque reutilisation du meme clip
    p = ( (c*0.37 + k*0.11) % 1.0 ) * u; printf "%.2f", p }')
  INARGS=(-ss "$OFF" -stream_loop 3 -i "$SRC")
  PREP="fps=${MZ_FPS},scale=${MZ_W}:${MZ_H}:force_original_aspect_ratio=increase:flags=lanczos,\
crop=${MZ_W}:${MZ_H},setpts=PTS-STARTPTS"
fi

# --- coup de zoom au demarrage du plan : donne du rythme
PUNCH="scale=w='${MZ_W}*(1+0.035*max(0,1-t/0.32))':h='${MZ_H}*(1+0.035*max(0,1-t/0.32))':eval=frame:flags=bilinear,crop=${MZ_W}:${MZ_H}"

OUTFADE=""
case "$TRANSI" in
  noir)  OUTFADE=",fade=t=out:st=$(awk -v s="$SEG" 'BEGIN{printf "%.2f", s-0.24}'):d=0.24:color=black" ;;
  fondu) OUTFADE=",fade=t=out:st=$(awk -v s="$SEG" 'BEGIN{printf "%.2f", s-0.16}'):d=0.16:color=black" ;;
esac
INFADE=""
case "$TRANSI" in
  flash) INFADE=",fade=t=in:st=0:d=0.09:color=white" ;;
  noir)  INFADE=",fade=t=in:st=0:d=0.24:color=black" ;;
  fondu) INFADE=",fade=t=in:st=0:d=0.16:color=black" ;;
esac

ffmpeg -y -v error "${INARGS[@]}" -filter_complex "
[0:v]${PREP},${PUNCH},${GRADE},format=gbrp[pre];
$(mz_fx_halation pre lit 0.36);
[lit]${TEXT}${INFADE}${OUTFADE},format=yuv420p,setsar=1[out]" \
  -map "[out]" -an -t "$SEG" \
  -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p -r "$MZ_FPS" \
  -x264-params "keyint=$((MZ_FPS*2)):min-keyint=$((MZ_FPS*2)):scenecut=0" -f mp4 \
  "$OUTF.part" 2>"$CACHE/plans/$(printf '%04d' "$k").log" \
  && mv "$OUTF.part" "$OUTF" || { echo "ECHEC plan $k ($SRC)" >&2; exit 1; }
EOSEG
chmod +x "$CACHE/render_seg.sh"

printf '%s\n' "${PLANS[@]}" > "$CACHE/liste.txt"
export MZ_ROOT CACHE SEG GRADE TEXT TRANSI MZ_W MZ_H MZ_FPS

DEJA=$(find "$CACHE/plans" -name '*.mp4' 2>/dev/null | wc -l)
[ "$DEJA" -gt 0 ] && hint "$DEJA plan(s) deja en cache — reutilises (-R pour tout refaire)"

CPU=$(nproc 2>/dev/null || echo 2)
say "rendu en parallele sur $CPU coeurs…"
< "$JOBS" xargs -P "$CPU" -I{} bash "$CACHE/render_seg.sh" {} || die "Le rendu d'au moins un plan a echoue.
  Detail :  ls $CACHE/plans/*.log"

FAITS=$(find "$CACHE/plans" -name '*.mp4' | wc -l)
[ "$FAITS" -eq "$NSEG" ] || die "$FAITS/$NSEG plans produits — abandon."
ok "$NSEG plans etalonnes"

# ---------------------------------------------------------------
step "2/5  Montage"
: > "$CACHE/concat.txt"
for ((k=0; k<NSEG; k++)); do
  printf "file '%s'\n" "$CACHE/plans/$(printf '%04d' "$k").mp4" >> "$CACHE/concat.txt"
done
mz_ff "Assemblage" ffmpeg -y -v error -f concat -safe 0 -i "$CACHE/concat.txt" \
  -c copy -t "$DUREE" "$CACHE/base.mp4" || die "Assemblage impossible"
ok "sequence de $(mz_hms "$(mz_duration "$CACHE/base.mp4")")"

# ---------------------------------------------------------------
step "3/5  Sous-titres"
SUBFILE=""
if [ "$NOSUBS" = "0" ] && [ -f "$SCRIPT" ] && [ -s "$SCRIPT" ]; then
  SUBFILE="$CACHE/soustitres.ass"
  case "$SCRIPT" in
    *.srt|*.SRT) SRCARG=(--srt "$SCRIPT")
                 hint "sous-titres tires de la transcription (deja cales)" ;;
    *)           SRCARG=(--text "$SCRIPT" --audio "$AUDIO") ;;
  esac
  python3 "$MZ_TOOLS/make_captions.py" "${SRCARG[@]}" --out "$SUBFILE" \
     --duration "$DUREE" --words "$SUBW" --size "$SUBSZ" \
     --font "$(mz_font_display)" --W "$MZ_W" --H "$MZ_H" || die "Sous-titres impossibles"
else
  [ "$NOSUBS" = "1" ] && hint "sous-titres desactives (-N)" \
                      || hint "pas de script.txt — video sans sous-titres"
fi

step "4/5  Habillage : sous-titres, signature, filigrane"

VIN=(-i "$CACHE/base.mp4")
GRAPH=""; CUR="0:v"; VIDX=1

# --- sous-titres graves dans l'image (libass)
if [ -n "$SUBFILE" ]; then
  GRAPH+="[$CUR]subtitles='$(mz_esc_path "$SUBFILE")':fontsdir='$(mz_esc_path "$MZ_FONTS")'[vsub];"
  CUR="vsub"
  ok "sous-titres graves"
fi

# --- revelation d'intro
INTRO="$MZ_BRAND/intro_signature.mov"
OUTRO="$MZ_BRAND/outro_signature.mov"
if [ "$NOBRAND" = "0" ] && [ -f "$INTRO" ]; then
  VIN+=(-i "$INTRO")
  GRAPH+="[$VIDX:v]setpts=PTS-STARTPTS[intro];[$CUR][intro]overlay=0:0:eof_action=pass:format=auto[vi];"
  CUR="vi"; VIDX=$((VIDX+1))
  ok "intro Mr ZIKA"
fi

# --- carte de fin, calee sur la fin de la video
if [ "$NOBRAND" = "0" ] && [ -f "$OUTRO" ]; then
  ODUR=$(mz_duration "$OUTRO")
  OSTART=$(awk -v d="$DUREE" -v o="$ODUR" 'BEGIN{s=d-o; if(s<0)s=0; printf "%.2f", s}')
  VIN+=(-i "$OUTRO")
  GRAPH+="[$VIDX:v]setpts=PTS-STARTPTS+${OSTART}/TB[outro];[$CUR][outro]overlay=0:0:eof_action=pass:format=auto[vo];"
  CUR="vo"; VIDX=$((VIDX+1))
  ok "carte de fin a $(mz_hms "$OSTART")"
fi

# --- filigrane permanent
MARK="$MZ_BRAND/signature_mark.png"
if [ "$FILIGRANE" = "1" ] && [ -f "$MARK" ]; then
  MW=$(awk -v w="$MZ_W" 'BEGIN{printf "%d", w*0.26}')
  MY=$(awk -v h="$MZ_H" 'BEGIN{printf "%d", h*0.775}')
  VIN+=(-i "$MARK")
  GRAPH+="[$VIDX:v]scale=${MW}:-1,format=rgba,colorchannelmixer=aa=0.72[mk];\
[$CUR][mk]overlay=x=(W-w)/2:y=${MY}:format=auto[vm];"
  CUR="vm"; VIDX=$((VIDX+1))
  ok "filigrane permanent"
fi

GRAPH+="[$CUR]format=yuv420p,setsar=1[vout];"

# ---------------------------------------------------------------
# Son. Les entrees audio sont ajoutees APRES les calques video :
# leur numero depend donc du nombre de calques utilises.
# ---------------------------------------------------------------
AIN=(-i "$AUDIO"); I_VOIX="$VIDX"
FADE_A=$(awk -v d="$DUREE" 'BEGIN{s=d-1.6; if(s<0)s=0; printf "%.2f", s}')

if [ -n "$MUSIQUE" ] && [ -f "$MUSIQUE" ]; then
  AIN+=(-stream_loop -1 -t "$DUREE" -i "$MUSIQUE"); I_MUS=$((VIDX+1))
  # la musique s'efface d'elle-meme des que la voix parle (sidechain)
  GRAPH+="[${I_VOIX}:a]aformat=sample_fmts=fltp:sample_rates=$MZ_SR:channel_layouts=stereo,\
apad,atrim=0:$DUREE,asetpts=N/SR/TB,asplit=2[vx][vkey];
[${I_MUS}:a]aformat=sample_fmts=fltp:sample_rates=$MZ_SR:channel_layouts=stereo,\
apad,atrim=0:$DUREE,asetpts=N/SR/TB,volume=${MVOL}dB[mu];
[mu][vkey]sidechaincompress=threshold=0.045:ratio=9:attack=18:release=420:makeup=1[duck];
[vx][duck]amix=inputs=2:duration=first:normalize=0[mix];
[mix]alimiter=limit=0.97,afade=t=out:st=${FADE_A}:d=1.6[aout]"
  ok "voix + musique (baisse automatique sous la voix)"
else
  GRAPH+="[${I_VOIX}:a]aformat=sample_fmts=fltp:sample_rates=$MZ_SR:channel_layouts=stereo,\
apad,atrim=0:$DUREE,asetpts=N/SR/TB,alimiter=limit=0.97,\
afade=t=out:st=${FADE_A}:d=1.6[aout]"
  ok "voix seule"
fi

# ---------------------------------------------------------------
step "5/5  Export TikTok"
say "encodage final — CRF $CRF, ${MZ_W}x${MZ_H} @ ${MZ_FPS} i/s…"
ffmpeg -y -hide_banner -loglevel error -stats \
  "${VIN[@]}" "${AIN[@]}" \
  -filter_complex "$GRAPH" \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset slow -crf "$CRF" -profile:v high -level 4.1 \
  -pix_fmt yuv420p -r "$MZ_FPS" -g "$((MZ_FPS*2))" \
  -c:a aac -b:a 192k -ar "$MZ_SR" -ac 2 \
  -movflags +faststart -t "$DUREE" \
  "$SORTIE" || die "Export final impossible"

echo
FD=$(mz_duration "$SORTIE"); FS=$(du -h "$SORTIE" | cut -f1)
ok "${C_S}Video prete${C_0}"
printf '  %s\n' "$SORTIE"
printf '  duree %s   |   %s   |   %sx%s @ %s i/s\n' "$(mz_hms "$FD")" "$FS" "$MZ_W" "$MZ_H" "$MZ_FPS"
echo
hint "Verifie le rendu, puis publie. Conseils : docs/03-TIKTOK.md"
