# Hausraster FreeCAD-Mod
import os
import sys
from pathlib import Path

try:
    here = Path(__file__).resolve().parent
except NameError:
    here = Path()
    candidates = [
        Path.home() / ".local/share/FreeCAD/v1-1/Mod/Hausraster",
        Path.home() / ".local/share/FreeCAD/Mod/Hausraster",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.insert(0, Path(appdata) / "FreeCAD" / "Mod" / "Hausraster")
    for c in candidates:
        if c.exists():
            here = c
            break

src = here.parent.parent / "src"
# Im ausgelieferten Mod liegen die Python-Dateien direkt hier
for p in (here, src):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
