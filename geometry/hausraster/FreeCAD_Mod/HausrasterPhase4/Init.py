# Hausraster Phase 4 (kein Workbench, nur Macro-Unterstützung)
# Phase-2-Modul Hausraster wird nicht verändert.
import os
import sys
from pathlib import Path
try:
    here = Path(__file__).resolve().parent
except NameError:
    here = Path()
    appdata = os.environ.get("APPDATA")
    cands = []
    if appdata:
        cands.append(Path(appdata) / "FreeCAD" / "Mod" / "HausrasterPhase4")
    cands += [
        Path.home() / ".local/share/FreeCAD/v1-1/Mod/HausrasterPhase4",
        Path.home() / ".local/share/FreeCAD/Mod/HausrasterPhase4",
    ]
    for c in cands:
        if c.exists():
            here = c
            break
if here.exists() and str(here) not in sys.path:
    sys.path.insert(0, str(here))
