#!/usr/bin/env bash
# ============================================================
#  MZ STUDIO — bibliotheque commune
#  Mr ZIKA — chaine de production video motivation / TikTok
# ============================================================

set -o pipefail

# ---------- Racine du projet ----------
MZ_ROOT="${MZ_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export MZ_ROOT

MZ_FONTS="$MZ_ROOT/assets/fonts"
MZ_BRAND="$MZ_ROOT/assets/brand"
MZ_SFX="$MZ_ROOT/assets/sfx"
MZ_TOOLS="$MZ_ROOT/tools"
MZ_PRESETS="$MZ_ROOT/presets"

# ---------- Format de sortie (TikTok) ----------
MZ_W="${MZ_W:-1080}"            # largeur
MZ_H="${MZ_H:-1920}"            # hauteur (9:16)
MZ_FPS="${MZ_FPS:-30}"          # images / seconde
MZ_DUR="${MZ_DUR:-300}"         # duree cible en secondes (5 minutes)
MZ_SR="${MZ_SR:-48000}"         # frequence audio
MZ_LUFS="${MZ_LUFS:--14}"       # loudness cible (standard plateformes)
MZ_TP="${MZ_TP:--1.5}"          # true peak max

# ---------- Couleurs terminal ----------
if [ -t 1 ]; then
  C_R=$'\033[31m'; C_G=$'\033[32m'; C_Y=$'\033[33m'; C_B=$'\033[36m'
  C_D=$'\033[2m';  C_S=$'\033[1m'; C_0=$'\033[0m'
else
  C_R=""; C_G=""; C_Y=""; C_B=""; C_D=""; C_S=""; C_0=""
fi

say()  { printf '%s\n' "${C_B}▸${C_0} $*"; }
ok()   { printf '%s\n' "${C_G}✔${C_0} $*"; }
warn() { printf '%s\n' "${C_Y}▲${C_0} $*" >&2; }
die()  { printf '%s\n' "${C_R}✖${C_0} $*" >&2; exit 1; }
step() { printf '\n%s\n' "${C_S}${C_B}── $* ${C_0}"; }
hint() { printf '%s\n' "${C_D}  $*${C_0}"; }

# ---------- Verifications ----------
need() {
  command -v "$1" >/dev/null 2>&1 || die "Outil manquant : $1
  Lance d'abord :  ./install.sh"
}

need_file() { [ -f "$1" ] || die "Fichier introuvable : $1"; }

# ---------- Sondes media ----------
# duree d'un fichier en secondes (decimal)
mz_duration() {
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$1" 2>/dev/null \
    | awk '{printf "%.3f", $1}'
}

# "video" | "image" | "audio" | "inconnu"
mz_kind() {
  local f="$1" vc ac nbf
  vc=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$f" 2>/dev/null)
  ac=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$f" 2>/dev/null)
  if [ -n "$vc" ]; then
    case "$vc" in
      mjpeg|png|bmp|gif|webp|tiff) echo image; return;;
    esac
    nbf=$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames -of csv=p=0 "$f" 2>/dev/null)
    if [ "$nbf" = "1" ]; then echo image; else echo video; fi
    return
  fi
  [ -n "$ac" ] && { echo audio; return; }
  echo inconnu
}

mz_has_audio() {
  [ -n "$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$1" 2>/dev/null)" ]
}

# ---------- Polices ----------
# Choisit la meilleure police disponible pour les gros titres
mz_font_display() {
  local c
  for c in "$MZ_FONTS/Anton-Regular.ttf" \
           "$MZ_FONTS/BebasNeue-Regular.ttf" \
           "$MZ_FONTS/Oswald-Variable.ttf" \
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" \
           "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" \
           "/System/Library/Fonts/Supplemental/Impact.ttf" \
           "/Library/Fonts/Arial Bold.ttf" \
           "C:/Windows/Fonts/impact.ttf"; do
    [ -f "$c" ] && { echo "$c"; return; }
  done
  fc-match -f '%{file}' 'sans:bold' 2>/dev/null || echo ""
}

# Police pour les sous-titres (bonne lisibilite, accents FR)
mz_font_subs() {
  local c
  for c in "$MZ_FONTS/Archivo-Variable.ttf" \
           "$MZ_FONTS/Oswald-Variable.ttf" \
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" \
           "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"; do
    [ -f "$c" ] && { echo "$c"; return; }
  done
  fc-match -f '%{file}' 'sans:bold' 2>/dev/null || echo ""
}

# echappe un chemin pour drawtext / subtitles
mz_esc_path() { printf '%s' "$1" | sed -e "s/\\\\/\\\\\\\\\\\\\\\\/g" -e "s/:/\\\\\\\\:/g" -e "s/'/\\\\\\\\'/g"; }

# ---------- Divers ----------
mz_tmpdir() {
  local d; d=$(mktemp -d "${TMPDIR:-/tmp}/mz.XXXXXXXX") || die "mktemp impossible"
  echo "$d"
}

# barre de progression simple pour ffmpeg (silencieux mais vivant)
mz_ff() {
  local label="$1"; shift
  printf '  %s… ' "$label"
  if "$@" >/tmp/mz-ff.log 2>&1; then
    printf '%s\n' "${C_G}ok${C_0}"
  else
    printf '%s\n' "${C_R}echec${C_0}"
    tail -25 /tmp/mz-ff.log >&2
    return 1
  fi
}

# arrondi mm:ss
mz_hms() { awk -v s="$1" 'BEGIN{printf "%d:%02d", int(s/60), int(s)%60}'; }
