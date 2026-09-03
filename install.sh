#!/usr/bin/env bash
# ============================================================
#  MZ STUDIO — installation
#  Installe ffmpeg, yt-dlp, les bibliotheques Python et les polices.
#  Fonctionne sur Ubuntu/Debian, Fedora, Arch, macOS et Termux.
# ============================================================
set -u
cd "$(dirname "$0")" || exit 1
source lib/common.sh

step "MZ STUDIO — installation"

# ---------------------------------------------------------------
# 1. Detection du systeme
# ---------------------------------------------------------------
SYS="inconnu"; SUDO=""
[ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
if   [ -n "${PREFIX:-}" ] && command -v pkg  >/dev/null 2>&1; then SYS="termux"; SUDO=""
elif command -v brew    >/dev/null 2>&1; then SYS="brew"; SUDO=""
elif command -v apt-get >/dev/null 2>&1; then SYS="debian"
elif command -v dnf     >/dev/null 2>&1; then SYS="fedora"
elif command -v pacman  >/dev/null 2>&1; then SYS="arch"
fi
say "systeme detecte : $SYS"

installe() {   # $@ = paquets
  case "$SYS" in
    debian) $SUDO apt-get update -qq && $SUDO apt-get install -y --no-install-recommends "$@" ;;
    fedora) $SUDO dnf install -y "$@" ;;
    arch)   $SUDO pacman -Sy --noconfirm "$@" ;;
    brew)   brew install "$@" ;;
    termux) pkg install -y "$@" ;;
    *) warn "Systeme non reconnu — installe a la main : $*"; return 1 ;;
  esac
}

# ---------------------------------------------------------------
# 2. ffmpeg
# ---------------------------------------------------------------
step "1/4  ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  ok "deja present — $(ffmpeg -version 2>&1 | head -1 | cut -c1-46)"
else
  installe ffmpeg || die "Installe ffmpeg a la main : https://ffmpeg.org/download.html"
  command -v ffmpeg >/dev/null 2>&1 && ok "ffmpeg installe" || die "ffmpeg toujours absent"
fi
MANQUE=$(mz_capacites_manquantes)
if [ -n "$MANQUE" ]; then
  warn "ton ffmpeg ne sait pas faire :$MANQUE"
  case "$SYS" in
    brew) hint "brew install ffmpeg   puis verifie :  which -a ffmpeg" ;;
    *)    hint "installe un ffmpeg complet pour ton systeme" ;;
  esac
else
  ok "ffmpeg sait tout faire (sous-titres, texte, mouvement, x264, aac)"
fi

# ---------------------------------------------------------------
# 3. Python : pillow, numpy, yt-dlp
# ---------------------------------------------------------------
step "2/4  Python"
command -v python3 >/dev/null 2>&1 || installe python3 || die "python3 requis"
PIPOPT=""
python3 -c "import sys; sys.exit(0)" 2>/dev/null
if ! python3 -m pip --version >/dev/null 2>&1; then
  case "$SYS" in debian) installe python3-pip ;; fedora) installe python3-pip ;;
                 arch) installe python-pip ;; termux) pkg install -y python ;; esac
fi
# certaines distributions refusent l'installation hors environnement virtuel
PAQUETS="pillow numpy yt-dlp faster-whisper pyyaml"
python3 -m pip install --quiet --upgrade $PAQUETS 2>/dev/null \
  || python3 -m pip install --quiet --break-system-packages --upgrade $PAQUETS 2>/dev/null \
  || { PIPOPT="ko"; warn "pip a echoue. Cree un environnement :
     python3 -m venv .venv && source .venv/bin/activate && pip install $PAQUETS"; }
if [ "$PIPOPT" != "ko" ]; then
  python3 -c "import PIL, numpy" 2>/dev/null && ok "pillow + numpy" || warn "pillow/numpy absents"
  command -v yt-dlp >/dev/null 2>&1 && ok "yt-dlp $(yt-dlp --version 2>/dev/null)" \
    || warn "yt-dlp absent (necessaire seulement pour les URL YouTube)"
  python3 -c "import faster_whisper" 2>/dev/null && ok "faster-whisper (transcription)" \
    || warn "faster-whisper absent — « mz ecoute » ne fonctionnera pas"
  python3 -c "import yaml" 2>/dev/null && ok "pyyaml (fichiers de projet)" \
    || warn "pyyaml absent — « mz projet » ne lira que le JSON"
fi

# ---------------------------------------------------------------
# 4. Polices (licence libre OFL, utilisables commercialement)
# ---------------------------------------------------------------
step "3/4  Polices"
mkdir -p assets/fonts
UA="Mozilla/5.0 (X11; Linux x86_64)"
recupere() {
  local url="$1" dest="assets/fonts/$2"
  [ -s "$dest" ] && { ok "$2 (deja la)"; return 0; }
  if command -v curl >/dev/null 2>&1; then curl -sSL -A "$UA" -o "$dest" "$url"
  elif command -v wget >/dev/null 2>&1; then wget -q -U "$UA" -O "$dest" "$url"
  else warn "ni curl ni wget"; return 1; fi
  local entete=""; [ -s "$dest" ] && entete=$(head -c4 "$dest" 2>/dev/null)
  if [ -s "$dest" ] && grep -qE $'\x00\x01\x00\x00|OTTO|true|ttcf' <<< "$entete"; then
    ok "$2"
  else
    rm -f "$dest"; warn "$2 non telechargee — une police systeme sera utilisee"
  fi
}
B="https://raw.githubusercontent.com/google/fonts/main/ofl"
recupere "$B/anton/Anton-Regular.ttf"            "Anton-Regular.ttf"
recupere "$B/bebasneue/BebasNeue-Regular.ttf"    "BebasNeue-Regular.ttf"
recupere "$B/oswald/Oswald%5Bwght%5D.ttf"        "Oswald-Variable.ttf"
recupere "$B/archivo/Archivo%5Bwdth%2Cwght%5D.ttf" "Archivo-Variable.ttf"

# ---------------------------------------------------------------
step "4/4  Mise en place du projet"
chmod +x mz bin/*.sh install.sh 2>/dev/null
mkdir -p projet/{01-source,02-audio,03-broll,04-rendu} assets/brand
[ -f projet/script.txt ] || cp presets/script-exemple.txt projet/script.txt 2>/dev/null
ok "dossiers prets"

echo
./mz doctor
echo
say "${C_S}Prochaine etape${C_0} :  ./mz brand    puis    ./mz demo"
