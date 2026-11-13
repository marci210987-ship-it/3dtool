#!/bin/bash
set -euo pipefail
export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-offscreen}
export LIBGL_ALWAYS_SOFTWARE=1
export PYTHONPATH="/workspace/ordnungssystem/src${PYTHONPATH:+:$PYTHONPATH}"
SCRIPT="$1"
shift || true
# FreeCADCmd 1.1 führt übergebene .py-Dateien nicht zuverlässig aus; stdin-exec ist stabil.
/tmp/freecad/squashfs-root/AppRun freecadcmd -P /workspace/ordnungssystem/src "$@" << PY
import sys
sys.path.insert(0, "/workspace/ordnungssystem/src")
# Argumente für das Skript durchreichen
sys.argv = ["$SCRIPT"] + $(python3 -c "import json,sys; print(repr(sys.argv[1:]))" -- "$@")
exec(open("$SCRIPT", encoding="utf-8").read())
PY
