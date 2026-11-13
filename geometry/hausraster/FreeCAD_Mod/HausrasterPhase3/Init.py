# -*- coding: utf-8 -*-
# Hausraster Phase 3: Besteck und Gewürz. Benötigt zusätzlich das Mod-Paket Hausraster (Phase 2).
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
        cands.append(Path(appdata) / "FreeCAD" / "Mod" / "HausrasterPhase3")
    cands += [
        Path.home() / ".local/share/FreeCAD/v1-1/Mod/HausrasterPhase3",
        Path.home() / ".local/share/FreeCAD/Mod/HausrasterPhase3",
    ]
    for c in cands:
        if c.exists():
            here = c
            break
if here.exists() and str(here) not in sys.path:
    sys.path.insert(0, str(here))
