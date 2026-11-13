#!/usr/bin/env bash
# Startet das extrahierte FreeCAD 1.1.4 ohne AppImage-Mount.
set -euo pipefail
ROOT="${FREECAD_ROOT:-/tmp/freecad/squashfs-root}"
export PREFIX="$ROOT/usr"
export PYTHONHOME="$PREFIX"
export PATH_TO_FREECAD_LIBDIR="$PREFIX/lib"
export FONTCONFIG_FILE=/etc/fonts/fonts.conf
export FONTCONFIG_PATH=/etc/fonts
export SSL_CERT_FILE="$PREFIX/ssl/cacert.pem"
export GIT_SSL_CAINFO="$PREFIX/ssl/cacert.pem"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
# Library-Pfad nur für den FreeCAD-Prozess, nicht global persistieren
export LD_LIBRARY_PATH="$PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
# Projektquellen zusätzlich, falls der Mod-Pfad fehlt
export PYTHONPATH="/workspace/ordnungssystem/src:/workspace/ordnungssystem/FreeCAD_Mod/Hausraster:/workspace/ordnungssystem/FreeCAD_Mod/HausrasterPhase3:/workspace/ordnungssystem/FreeCAD_Mod/HausrasterPhase4${PYTHONPATH:+:$PYTHONPATH}"
exec "$ROOT/usr/bin/freecadcmd" "$@"
