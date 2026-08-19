#!/usr/bin/env bash
# ============================================================
#  mz brand — fabrique la signature Mr ZIKA et ses animations
#  Produit :  logo or metallique + revelation d'intro + carte de fin,
#  avec balayage de lumiere (le "Light Sweep" de After Effects).
# ============================================================
source "$(dirname "${BASH_SOURCE[0]}")/../lib/common.sh"

usage() {
cat <<'EOU'
UTILISATION
  mz brand [options]

OPTIONS
  -n <nom>       Nom affiche en grand           (defaut: ZIKA)
  -p <prefixe>   Petit mot au-dessus            (defaut: Mr)
  -c <palette>   or | argent | feu | glace | blanc   (defaut: or)
  -a <texte>     Phrase de fin  (defaut: "ABONNE-TOI POUR LA SUITE")
  -i <sec>       Duree de l'intro              (defaut: 3.5)
  -o <sec>       Duree de la carte de fin      (defaut: 5)
  -h             Cette aide

RESULTAT  ->  assets/brand/
  signature_big.png     logo haute definition
  signature_mark.png    filigrane discret (coin de l'ecran)
  intro_signature.mov   revelation animee, fond transparent
  outro_signature.mov   carte de fin animee, fond transparent
EOU
}

NOM="ZIKA"; PREFIXE="Mr"; PALETTE="or"
APPEL="ABONNE-TOI POUR LA SUITE"
T_IN="3.5"; T_OUT="5"

while getopts "n:p:c:a:i:o:h" opt; do
  case "$opt" in
    n) NOM="$OPTARG" ;; p) PREFIXE="$OPTARG" ;; c) PALETTE="$OPTARG" ;;
    a) APPEL="$OPTARG" ;; i) T_IN="$OPTARG" ;; o) T_OUT="$OPTARG" ;;
    h) usage; exit 0 ;; *) usage; exit 1 ;;
  esac
done

need ffmpeg; need python3
mkdir -p "$MZ_BRAND"

# ---------------------------------------------------------------
step "1/3  Logo metallique"
python3 "$MZ_TOOLS/make_signature.py" \
  --prefix "$PREFIXE" --name "$NOM" --palette "$PALETTE" --outdir "$MZ_BRAND" \
  || die "Generation du logo impossible"

SIG="$MZ_BRAND/signature_big.png"
ALP="$MZ_BRAND/signature_alpha.png"
BND="$MZ_BRAND/sweep_band.png"
need_file "$SIG"

# taille du logo une fois mis a l'echelle dans le cadre vertical
SRC_W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$SIG")
SRC_H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SIG")
LW=$(awk -v w="$MZ_W" 'BEGIN{printf "%d", w*0.88}')
LH=$(awk -v lw="$LW" -v w="$SRC_W" -v h="$SRC_H" 'BEGIN{printf "%d", lw*h/w}')
BW=$(awk -v lw="$LW" 'BEGIN{printf "%d", lw*0.42}')

FONT=$(mz_font_display); FONT_E=$(mz_esc_path "$FONT")

# ---------------------------------------------------------------
# Le balayage : une bande lumineuse traverse le logo, decoupee par
# l'alpha des lettres. C'est ce detail qui fait "logo pro".
#   [band] bande grise qui se deplace
#   x[msk] alpha des lettres  -> la lumiere n'existe que sur le metal
#   alphamerge + overlay      -> ajout par-dessus le logo
# ---------------------------------------------------------------
sweep_graph() {   # $1 = debut du balayage   $2 = duree du balayage
  local S="$1" D="$2"
  cat <<EOF
[0:v]scale=$LW:$LH:flags=lanczos,format=rgba[sig];
[1:v]scale=$LW:$LH:flags=lanczos,format=rgba,alphaextract,format=gray[msk];
[2:v]scale=$BW:$LH:flags=bilinear,format=gray[bnd];
color=c=black:s=${LW}x${LH}:r=$MZ_FPS,format=gray[dark];
[dark][bnd]overlay=x='-$BW+((t-$S)/$D)*($LW+$BW)':y=0:eval=frame,format=gray[band];
[band][msk]blend=all_mode=multiply,format=gray[swa];
color=c=white:s=${LW}x${LH}:r=$MZ_FPS,format=rgba[wht];
[wht][swa]alphamerge[sweep];
[sig][sweep]overlay=0:0:format=auto[lit]
EOF
}

# ---------------------------------------------------------------
step "2/3  Revelation d'intro (${T_IN}s)"
FADE_OUT=$(awk -v t="$T_IN" 'BEGIN{printf "%.2f", t-0.55}')
SW_START=$(awk -v t="$T_IN" 'BEGIN{printf "%.2f", t*0.30}')

mz_ff "Rendu intro" ffmpeg -y -v error \
  -loop 1 -framerate "$MZ_FPS" -t "$T_IN" -i "$SIG" \
  -loop 1 -framerate "$MZ_FPS" -t "$T_IN" -i "$ALP" \
  -loop 1 -framerate "$MZ_FPS" -t "$T_IN" -i "$BND" \
  -filter_complex "
$(sweep_graph "$SW_START" 0.85);
[lit]scale=
  w='max(2,$LW*(1.16-0.16*min(1,t/0.40))*(1+0.014*t))':
  h='max(2,$LH*(1.16-0.16*min(1,t/0.40))*(1+0.014*t))':
  eval=frame:flags=bilinear[anim];
color=c=black@0.0:s=${MZ_W}x${MZ_H}:r=$MZ_FPS,format=rgba[canvas];
[canvas][anim]overlay=x='(W-w)/2':y='(H-h)/2-40':eval=frame:format=auto,
  fade=t=in:st=0:d=0.30:alpha=1,
  fade=t=out:st=$FADE_OUT:d=0.55:alpha=1,
  format=rgba[out]" \
  -map "[out]" -c:v qtrle -t "$T_IN" "$MZ_BRAND/intro_signature.mov" \
  || die "Rendu de l'intro impossible"
ok "intro_signature.mov"

# ---------------------------------------------------------------
step "3/3  Carte de fin (${T_OUT}s)"
O_FADE=$(awk -v t="$T_OUT" 'BEGIN{printf "%.2f", t-0.7}')
O_SW=$(awk -v t="$T_OUT" 'BEGIN{printf "%.2f", t*0.34}')
CALL_Y=$(awk -v h="$MZ_H" 'BEGIN{printf "%d", h*0.72}')
CALL_SZ=$(awk -v w="$MZ_W" 'BEGIN{printf "%d", w*0.058}')

mz_ff "Rendu outro" ffmpeg -y -v error \
  -loop 1 -framerate "$MZ_FPS" -t "$T_OUT" -i "$SIG" \
  -loop 1 -framerate "$MZ_FPS" -t "$T_OUT" -i "$ALP" \
  -loop 1 -framerate "$MZ_FPS" -t "$T_OUT" -i "$BND" \
  -filter_complex "
$(sweep_graph "$O_SW" 1.0);
[lit]scale=
  w='max(2,$LW*(1.05-0.05*min(1,t/0.55))*(1+0.008*t))':
  h='max(2,$LH*(1.05-0.05*min(1,t/0.55))*(1+0.008*t))':
  eval=frame:flags=bilinear[anim];
color=c=black@0.0:s=${MZ_W}x${MZ_H}:r=$MZ_FPS,format=rgba[canvas];
[canvas][anim]overlay=x='(W-w)/2':y='(H-h)/2-120':eval=frame:format=auto[withlogo];
[withlogo]drawtext=fontfile='$FONT_E':text='$APPEL':
  fontcolor=white@0.92:fontsize=$CALL_SZ:x=(w-text_w)/2:y=$CALL_Y:
  borderw=4:bordercolor=black@0.75:
  alpha='if(lt(t,0.9),0,min(1,(t-0.9)/0.5))'[txt];
[txt]fade=t=in:st=0:d=0.35:alpha=1,
     fade=t=out:st=$O_FADE:d=0.65:alpha=1,format=rgba[out]" \
  -map "[out]" -c:v qtrle -t "$T_OUT" "$MZ_BRAND/outro_signature.mov" \
  || die "Rendu de la carte de fin impossible"
ok "outro_signature.mov"

echo
ok "Identite ${C_S}${PREFIXE} ${NOM}${C_0} prete dans assets/brand/"
ls -1 "$MZ_BRAND" | sed 's/^/  /'
