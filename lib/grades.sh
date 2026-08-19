#!/usr/bin/env bash
# ============================================================
#  MZ STUDIO — etalonnage (color grading) facon DaVinci Resolve
#  Chaque "look" = une chaine de filtres ffmpeg lineaire.
# ============================================================

# ------------------------------------------------------------
# mz_grade <nom>
#   Renvoie une chaine de filtres (sans labels) a inserer telle quelle.
#   Reproduit les "Color Warper / Curves / Color Wheels" de Resolve :
#     - courbe en S      -> contraste cinema
#     - colorbalance     -> roues chromatiques (ombres/moyens/hautes)
#     - eq               -> saturation, luminosite, gamma
# ------------------------------------------------------------
mz_grade() {
  case "${1:-orange_teal}" in

    # Le look blockbuster : ombres cyan, peaux/hautes lumieres orange.
    orange_teal)
      echo "curves=all='0/0 0.22/0.16 0.5/0.51 0.78/0.84 1/1',\
colorbalance=rs=-0.075:gs=0.010:bs=0.105:rm=0.030:gm=0.000:bm=-0.020:rh=0.110:gh=0.030:bh=-0.085,\
eq=contrast=1.08:saturation=1.14:gamma=0.98"
      ;;

    # Discipline / froid / acier. Tres bon sur les plans de sport et de ville.
    ice)
      echo "curves=all='0/0.015 0.25/0.20 0.5/0.50 0.8/0.86 1/1',\
colorbalance=rs=-0.10:bs=0.14:rm=-0.03:bm=0.06:rh=-0.02:bh=0.05,\
eq=contrast=1.14:saturation=0.82:gamma=0.96"
      ;;

    # Le grind : rouge/orange brulant, noirs ecrases, tres punchy.
    fire)
      echo "curves=all='0/0 0.20/0.11 0.5/0.52 0.82/0.90 1/1',\
colorbalance=rs=0.06:gs=-0.02:bs=-0.06:rm=0.09:gm=0.01:bm=-0.07:rh=0.16:gh=0.04:bh=-0.12,\
eq=contrast=1.18:saturation=1.22:gamma=0.94"
      ;;

    # Heure doree : chaud, doux, noirs leves facon pellicule.
    gold)
      echo "curves=all='0/0.045 0.28/0.28 0.55/0.60 1/0.985',\
colorbalance=rs=0.05:gs=0.02:bs=-0.05:rm=0.07:gm=0.03:bm=-0.06:rh=0.10:gh=0.05:bh=-0.04,\
eq=contrast=1.02:saturation=1.10:gamma=1.03"
      ;;

    # Noir et blanc contraste, facon photo argentique.
    noir)
      echo "hue=s=0,\
curves=all='0/0 0.18/0.08 0.5/0.52 0.85/0.94 1/1',\
eq=contrast=1.26:gamma=0.95"
      ;;

    # Neon / nuit / futuriste.
    cyber)
      echo "curves=all='0/0.02 0.25/0.19 0.5/0.5 0.8/0.87 1/1',\
colorbalance=rs=0.05:bs=0.12:rm=-0.04:bm=0.07:rh=0.09:gh=-0.03:bh=0.10,\
eq=contrast=1.16:saturation=1.28:gamma=0.95"
      ;;

    # Sobre : juste ce qu'il faut pour que ca ne soit pas plat.
    raw|neutre)
      echo "curves=all='0/0 0.25/0.235 0.5/0.5 0.75/0.775 1/1',\
eq=contrast=1.04:saturation=1.06"
      ;;

    *) echo "curves=all='0/0 0.25/0.235 0.5/0.5 0.75/0.775 1/1',eq=contrast=1.04:saturation=1.06" ;;
  esac
}

mz_grades_list() { echo "orange_teal ice fire gold noir cyber raw"; }

# ------------------------------------------------------------
# mz_fx_halation <in> <out> <force 0..1>
#   Le "Glow / Bloom" de Resolve : on isole les hautes lumieres,
#   on les floute, on les teinte chaud, puis blend Screen.
#   C'est CE filtre qui donne l'aspect "cine" immediat.
# ------------------------------------------------------------
mz_fx_halation() {
  local IN="$1" OUT="$2" F="${3:-0.36}"
  cat <<EOF
[$IN]split=2[hl_a][hl_b];
[hl_b]curves=all='0/0 0.58/0 0.80/0.45 1/1',
      colorbalance=rh=0.28:gh=0.06:bh=-0.16,
      gblur=sigma=26:steps=2[hl_bl];
[hl_a][hl_bl]blend=all_mode=screen:all_opacity=$F[$OUT]
EOF
}

# ------------------------------------------------------------
# mz_fx_texture <force>
#   Grain argentique + aberration chromatique + vignettage +
#   micro-nettete. Chaine lineaire, a coller apres l'etalonnage.
# ------------------------------------------------------------
mz_fx_texture() {
  local L="${1:-normal}"
  case "$L" in
    doux)   echo "noise=alls=2:allf=t+a,rgbashift=rh=1:bh=-1,vignette=PI/5.2,unsharp=5:5:0.45:5:5:0.0" ;;
    normal) echo "noise=alls=4:allf=t+a,rgbashift=rh=2:bh=-2,vignette=PI/4.6,unsharp=5:5:0.65:5:5:0.0" ;;
    fort)   echo "noise=alls=8:allf=t+a,rgbashift=rh=3:bh=-3,vignette=PI/4.0,unsharp=7:7:0.85:5:5:0.0" ;;
    aucun)  echo "null" ;;
    *)      echo "noise=alls=4:allf=t+a,rgbashift=rh=2:bh=-2,vignette=PI/4.6,unsharp=5:5:0.65:5:5:0.0" ;;
  esac
}

# ------------------------------------------------------------
# mz_fx_shake <amplitude px> <vitesse>
#   Micro-tremblement camera "tenue a la main". Rend vivant un plan fixe.
# ------------------------------------------------------------
mz_fx_shake() {
  local A="${1:-6}" S="${2:-1.0}"
  echo "crop=w=iw-$((A*2)):h=ih-$((A*2)):x=$A+$A*sin(2*PI*t*0.83*$S):y=$A+$A*cos(2*PI*t*1.27*$S),scale=${MZ_W}:${MZ_H}:flags=bicubic"
}

# ------------------------------------------------------------
# mz_fx_breathe <amplitude %>
#   Respiration lente du cadre (zoom sinusoidal tres doux).
# ------------------------------------------------------------
mz_fx_breathe() {
  local A="${1:-2}"
  echo "scale=w=iw*(1+0.0$A*sin(2*PI*t/9)):h=-2:eval=frame,crop=${MZ_W}:${MZ_H}"
}

# ------------------------------------------------------------
# mz_look_desc <nom>  — description humaine, pour l'aide en ligne
# ------------------------------------------------------------
mz_look_desc() {
  case "$1" in
    orange_teal) echo "Blockbuster — ombres cyan, peaux orange. Valeur sure." ;;
    ice)         echo "Discipline — froid, acier, desature. Sport, ville, hiver." ;;
    fire)        echo "Le grind — orange brulant, noirs ecrases, tres punchy." ;;
    gold)        echo "Heure doree — chaud, doux, noirs leves facon pellicule." ;;
    noir)        echo "Noir & blanc contraste, facon photo argentique." ;;
    cyber)       echo "Neon nocturne — magenta / cyan, satures." ;;
    raw)         echo "Sobre — contraste leger, couleurs fideles." ;;
    *)           echo "" ;;
  esac
}
