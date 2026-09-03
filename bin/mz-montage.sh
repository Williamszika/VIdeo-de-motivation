#!/usr/bin/env bash
# ============================================================
#  mz montage — monte un rush a partir d'une liste de plans
#  Recadre en vertical, agrandit proprement, etalonne, enchaine
#  les plans, pose la signature. Une ligne d'EDL = un plan.
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"
source "$MZ_ROOT/lib/grades.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz montage -i <video> [options]

Lit une liste de montage (.edl.tsv) et produit une video verticale
1080x1920 prete pour TikTok.

  Format de la liste, une ligne par plan :
      debut <tab> duree <tab> vitesse <tab> commentaire
  vitesse < 1 = ralenti.  Les lignes qui commencent par # sont ignorees.
  Produis-en une automatiquement :  mz analyser <video>

OPTIONS
  -i <video>    Le rush a monter                       (obligatoire)
  -e <edl>      Liste de montage        (defaut : <video sans extension>.edl.tsv)
  -o <sortie>   Video produite          (defaut : projet/04-rendu/montage_<date>.mp4)
  -l <look>     Etalonnage : luxe orange_teal ice fire gold noir cyber raw
                                                       (defaut luxe)
  -x <texture>  aucun doux normal fort                 (defaut doux)
  -T <transi>   coupe flash noir fondu                 (defaut flash)
  -y <px>       Recadrage vertical, en pixels apres agrandissement
  -X <px>       Recadrage horizontal
  -n <force>    Nettete rendue apres agrandissement    (defaut 0.9)
  -z <pct>      Zoom lent sur chaque plan, en %        (defaut 3)
  -a <son>      origine · muet · <fichier audio>       (defaut origine)
  -k <0|1>      Filigrane Mr ZIKA                      (defaut 1)
  -I            Sans carte de fin
  -H <force>    Halo cinema, 0 a 0.6                   (defaut 0.30)
  -q <crf>      Qualite : 16 excellente, 23 legere     (defaut 18)
  -h            Cette aide

EXEMPLE
  mz analyser rush.mp4
  mz montage -i rush.mp4 -l luxe -y 250 -T flash
EOU
}

SRC=""; EDL=""; SORTIE=""; LOOK="luxe"; TEXTURE="doux"; TRANSI="flash"
CY=""; CX=""; NETTETE="0.9"; ZOOM="3"; SON="origine"; FILIGRANE="1"; HALO="0.30"
NOBRAND=0; CRF="18"

while getopts "i:e:o:l:x:T:y:X:n:z:a:k:q:H:Ih" opt; do
  case "$opt" in
    i) SRC="$OPTARG" ;;   e) EDL="$OPTARG" ;;   o) SORTIE="$OPTARG" ;;
    l) LOOK="$OPTARG" ;;  x) TEXTURE="$OPTARG" ;; T) TRANSI="$OPTARG" ;;
    y) CY="$OPTARG" ;;    X) CX="$OPTARG" ;;    n) NETTETE="$OPTARG" ;;
    z) ZOOM="$OPTARG" ;;  a) SON="$OPTARG" ;;   k) FILIGRANE="$OPTARG" ;;
    q) CRF="$OPTARG" ;;   H) HALO="$OPTARG" ;;   I) NOBRAND=1 ;;
    h) usage; exit 0 ;;   *) usage; exit 1 ;;
  esac
done

need ffmpeg; need ffprobe
[ -n "$SRC" ] || { usage; exit 1; }
need_file "$SRC"
[ -z "$EDL" ] && EDL="${SRC%.*}.edl.tsv"
[ -f "$EDL" ] || die "Liste de montage introuvable : $EDL
  Produis-en une :  ./mz analyser \"$SRC\""

MANQUE=$(mz_capacites_manquantes)
[ -n "$MANQUE" ] && warn "ffmpeg ne sait pas faire :$MANQUE — le rendu sera partiel"

# ---------------------------------------------------------------
step "Lecture du rush"
SW=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$SRC")
SH=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SRC")
SD=$(mz_duration "$SRC")
[ -n "$SW" ] && [ -n "$SH" ] || die "Impossible de lire les dimensions de $SRC"
ok "$SW x $SH  ·  $(mz_hms "$SD")"

# Agrandissement : on remplit le cadre vertical, puis on rogne l'excedent.
read -r RW RH FACT SENS < <(awk -v sw="$SW" -v sh="$SH" -v w="$MZ_W" -v h="$MZ_H" 'BEGIN{
  if (sw/sh <= w/h) { rw=w; rh=int(w*sh/sw+0.5); if(rh%2)rh++; printf "%d %d %.2f largeur", rw, rh, w/sw }
  else              { rh=h; rw=int(h*sw/sh+0.5); if(rw%2)rw++; printf "%d %d %.2f hauteur", rw, rh, h/sh }
}')
[ -z "$CY" ] && CY=$(( (RH - MZ_H) / 2 )); [ "$CY" -lt 0 ] && CY=0
[ -z "$CX" ] && CX=$(( (RW - MZ_W) / 2 )); [ "$CX" -lt 0 ] && CX=0
ok "agrandi en ${RW}x${RH} (x${FACT} en $SENS), rogne a ${MZ_W}x${MZ_H} en x=$CX y=$CY"
awk -v f="$FACT" 'BEGIN{ if (f > 1.6) print "▲ agrandissement x" f " : l\47image sera molle. C\47est la limite de la source." }' >&2

# ---------------------------------------------------------------
step "Liste de montage"
DEBUTS=(); DUREES=(); VITESSES=(); NOTES=()
while IFS=$'\t' read -r d u v c; do
  case "$d" in ''|'#'*) continue ;; esac
  [ -n "$u" ] && [ -n "$v" ] || continue
  DEBUTS+=("$d"); DUREES+=("$u"); VITESSES+=("$v"); NOTES+=("${c:-}")
done < "$EDL"
N=${#DEBUTS[@]}
[ "$N" -gt 0 ] || die "Aucun plan lisible dans $EDL"

TOTAL=0
for ((k=0; k<N; k++)); do
  L=$(awk -v u="${DUREES[$k]}" -v v="${VITESSES[$k]}" 'BEGIN{printf "%.3f", u/v}')
  TOTAL=$(awk -v a="$TOTAL" -v b="$L" 'BEGIN{printf "%.3f", a+b}')
  printf '  plan %d : %6.2fs +%.2fs  x%.2f  ->  %5.2fs   %s\n' \
    $((k+1)) "${DEBUTS[$k]}" "${DUREES[$k]}" "${VITESSES[$k]}" "$L" "${NOTES[$k]}"
done
ok "$N plans  ·  $(mz_hms "$TOTAL") a l'ecran"

GRADE=$(mz_grade "$LOOK"); TEXT=$(mz_fx_texture "$TEXTURE")
hint "etalonnage $LOOK — $(mz_look_desc "$LOOK")"

case "$TRANSI" in
  flash) FIN=",fade=t=in:st=0:d=0.08:color=white" ; FOUT="" ;;
  noir)  FIN=",fade=t=in:st=0:d=0.14:color=black" ; FOUT="noir" ;;
  fondu) FIN=",fade=t=in:st=0:d=0.12:color=black" ; FOUT="fondu" ;;
  *)     TRANSI="coupe"; FIN="" ; FOUT="" ;;
esac

# ---------------------------------------------------------------
step "Montage"
ENTREES=(); GRAPHE=""; CHAINE=""
for ((k=0; k<N; k++)); do
  ENTREES+=(-ss "${DEBUTS[$k]}" -t "${DUREES[$k]}" -i "$SRC")
  L=$(awk -v u="${DUREES[$k]}" -v v="${VITESSES[$k]}" 'BEGIN{printf "%.3f", u/v}')
  INV=$(awk -v v="${VITESSES[$k]}" 'BEGIN{printf "%.4f", 1/v}')
  # zoom lent, alterne pour que deux plans voisins ne bougent pas pareil
  Z=$(awk -v z="$ZOOM" 'BEGIN{printf "%.4f", z/100}')
  if [ $((k % 2)) -eq 0 ]; then
    PUSH="scale=w='${MZ_W}*(1+${Z}*t/${L})':h='${MZ_H}*(1+${Z}*t/${L})':eval=frame:flags=bilinear,crop=${MZ_W}:${MZ_H}"
  else
    PUSH="scale=w='${MZ_W}*(1+${Z}-${Z}*t/${L})':h='${MZ_H}*(1+${Z}-${Z}*t/${L})':eval=frame:flags=bilinear,crop=${MZ_W}:${MZ_H}"
  fi
  SORTFADE=""
  case "$FOUT" in
    noir)  SORTFADE=",fade=t=out:st=$(awk -v l="$L" 'BEGIN{printf "%.2f", l-0.14}'):d=0.14:color=black" ;;
    fondu) SORTFADE=",fade=t=out:st=$(awk -v l="$L" 'BEGIN{printf "%.2f", l-0.12}'):d=0.12:color=black" ;;
  esac
  GRAPHE+="[${k}:v]fps=${MZ_FPS},scale=${RW}:${RH}:flags=lanczos,crop=${MZ_W}:${MZ_H}:${CX}:${CY},\
setpts=(PTS-STARTPTS)*${INV},unsharp=5:5:${NETTETE}:5:5:0.0,${PUSH},${GRADE},format=gbrp[pre$k];"
  GRAPHE+="$(mz_fx_halation "pre$k" "lit$k" "$HALO");"
  GRAPHE+="[lit$k]${TEXT}${FIN}${SORTFADE},trim=0:${L},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[s$k];"
  CHAINE+="[s$k]"
done
GRAPHE+="${CHAINE}concat=n=${N}:v=1:a=0[mont];"
CUR="mont"; IDX=$N

# --- signature de fin.
# Sur un clip court, la carte de fin de 5 s mangerait la moitie de la video.
# On bascule alors sur une simple apparition du logo, proportionnee.
OUTRO="$MZ_BRAND/outro_signature.mov"
SIGNE="$MZ_BRAND/signature_big.png"
if [ "$NOBRAND" = "0" ]; then
  OD=0; [ -f "$OUTRO" ] && OD=$(mz_duration "$OUTRO")
  ASSEZ_LONG=$(awk -v t="$TOTAL" -v o="$OD" 'BEGIN{print (o>0 && t >= o*2.5) ? 1 : 0}')

  if [ "$ASSEZ_LONG" = "1" ]; then
    OS=$(awk -v t="$TOTAL" -v o="$OD" 'BEGIN{s=t-o; if(s<0)s=0; printf "%.2f", s}')
    ENTREES+=(-i "$OUTRO")
    GRAPHE+="[${IDX}:v]setpts=PTS-STARTPTS+${OS}/TB[outro];[$CUR][outro]overlay=0:0:eof_action=pass:format=auto[vo];"
    CUR="vo"; IDX=$((IDX+1))
    ok "carte de fin complete a $(mz_hms "$OS")"

  elif [ -f "$SIGNE" ]; then
    # duree de la signature : un tiers du clip, entre 1,2 s et 2,4 s
    SD_SIG=$(awk -v t="$TOTAL" 'BEGIN{d=t/3; if(d<1.2)d=1.2; if(d>2.4)d=2.4; if(d>t)d=t; printf "%.2f", d}')
    SS=$(awk -v t="$TOTAL" -v d="$SD_SIG" 'BEGIN{s=t-d; if(s<0)s=0; printf "%.2f", s}')
    LW_SIG=$(awk -v w="$MZ_W" 'BEGIN{printf "%d", w*0.62}')
    SGW=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$SIGNE")
    SGH=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SIGNE")
    LH_SIG=$(awk -v lw="$LW_SIG" -v w="$SGW" -v h="$SGH" 'BEGIN{printf "%d", lw*h/w}')
    SY=$(awk -v h="$MZ_H" -v lh="$LH_SIG" 'BEGIN{printf "%d", h*0.40 - lh/2}')
    # un voile sombre monte sous le logo : sans lui, l'or se perd dans l'image
    GRAPHE+="color=black:s=${MZ_W}x${MZ_H}:r=${MZ_FPS}:d=${SD_SIG},format=rgba,colorchannelmixer=aa=0.44,fade=t=in:st=0:d=0.45:alpha=1,setpts=PTS-STARTPTS+${SS}/TB[voile];[$CUR][voile]overlay=0:0:eof_action=pass:format=auto[vv];"
    CUR="vv"
    ENTREES+=(-loop 1 -framerate "$MZ_FPS" -t "$SD_SIG" -i "$SIGNE")
    GRAPHE+="[${IDX}:v]scale=w='max(2,${LW_SIG}*(1.09-0.09*min(1,t/0.40)))':h='max(2,${LH_SIG}*(1.09-0.09*min(1,t/0.40)))':eval=frame:flags=bilinear,format=rgba,fade=t=in:st=0:d=0.38:alpha=1,setpts=PTS-STARTPTS+${SS}/TB[sig];[$CUR][sig]overlay=x='(W-w)/2':y='${SY}':eval=frame:eof_action=pass:format=auto[vo];"
    CUR="vo"; IDX=$((IDX+1))
    ok "signature de fin ${SD_SIG}s a partir de $(mz_hms "$SS") (clip court)"
  fi
fi

# --- filigrane
MARK="$MZ_BRAND/signature_mark.png"
if [ "$FILIGRANE" = "1" ] && [ -f "$MARK" ]; then
  MW=$(awk -v w="$MZ_W" 'BEGIN{printf "%d", w*0.26}')
  MY=$(awk -v h="$MZ_H" 'BEGIN{printf "%d", h*0.775}')
  ENTREES+=(-i "$MARK")
  GRAPHE+="[${IDX}:v]scale=${MW}:-1,format=rgba,colorchannelmixer=aa=0.72[mk];\
[$CUR][mk]overlay=x=(W-w)/2:y=${MY}:format=auto[vm];"
  CUR="vm"; IDX=$((IDX+1))
fi
GRAPHE+="[$CUR]format=yuv420p,setsar=1[vout];"

# --- son
FADEA=$(awk -v t="$TOTAL" 'BEGIN{s=t-1.0; if(s<0)s=0; printf "%.2f", s}')
case "$SON" in
  muet)
    ENTREES+=(-f lavfi -t "$TOTAL" -i "anullsrc=r=${MZ_SR}:cl=stereo")
    GRAPHE+="[${IDX}:a]anull[aout]"
    ok "sans son — tu ajouteras la musique dans TikTok" ;;
  origine)
    ENTREES+=(-stream_loop -1 -t "$TOTAL" -i "$SRC")
    GRAPHE+="[${IDX}:a]aformat=sample_fmts=fltp:sample_rates=${MZ_SR}:channel_layouts=stereo,\
atrim=0:${TOTAL},asetpts=N/SR/TB,loudnorm=I=${MZ_LUFS}:TP=${MZ_TP}:LRA=11,\
alimiter=limit=0.97,afade=t=out:st=${FADEA}:d=1.0[aout]"
    ok "son d'origine, ramene a ${MZ_LUFS} LUFS" ;;
  *)
    need_file "$SON"
    ENTREES+=(-stream_loop -1 -t "$TOTAL" -i "$SON")
    GRAPHE+="[${IDX}:a]aformat=sample_fmts=fltp:sample_rates=${MZ_SR}:channel_layouts=stereo,\
atrim=0:${TOTAL},asetpts=N/SR/TB,loudnorm=I=${MZ_LUFS}:TP=${MZ_TP}:LRA=11,\
alimiter=limit=0.97,afade=t=out:st=${FADEA}:d=1.0[aout]"
    ok "musique : $(basename "$SON")" ;;
esac

# ---------------------------------------------------------------
step "Export"
[ -z "$SORTIE" ] && SORTIE="$MZ_ROOT/projet/04-rendu/montage_$(date +%Y%m%d-%H%M%S).mp4"
mkdir -p "$(dirname "$SORTIE")"
say "encodage — CRF $CRF, ${MZ_W}x${MZ_H} @ ${MZ_FPS} i/s"
ffmpeg -y -hide_banner -loglevel error -stats "${ENTREES[@]}" \
  -filter_complex "$GRAPHE" -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset slow -crf "$CRF" -profile:v high -level 4.1 \
  -pix_fmt yuv420p -r "$MZ_FPS" -g "$((MZ_FPS*2))" \
  -c:a aac -b:a 192k -ar "$MZ_SR" -ac 2 \
  -movflags +faststart -t "$TOTAL" "$SORTIE" || die "Export impossible"

echo
FD=$(mz_duration "$SORTIE")
ok "${C_S}Montage pret${C_0}"
printf '  %s\n' "$SORTIE"
printf '  %s  ·  %s  ·  %sx%s @ %s i/s\n' "$(mz_hms "$FD")" \
  "$(du -h "$SORTIE" | cut -f1)" "$MZ_W" "$MZ_H" "$MZ_FPS"
