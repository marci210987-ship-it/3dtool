# -*- coding: utf-8 -*-
"""Pfadkonstanten für Quellen und Anwendung."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAUSRASTER_SRC = ROOT / "geometry" / "hausraster" / "src"
HAUSRASTER_ROOT = ROOT / "geometry" / "hausraster"


# Unter Windows keine Konsolenfenster für Kindprozesse (FreeCADCmd, Versionsabfragen) aufblitzen lassen.
KEIN_FENSTER = 0x08000000 if os.name == "nt" else 0


def app_home() -> Path:
    env = os.environ.get("CADSTUDIO_HOME")
    if env:
        path = Path(env)
    elif os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
        path = Path(base) / "CADStudio"
    else:
        path = Path.home() / ".config" / "cad-studio"
    path.mkdir(parents=True, exist_ok=True)
    return path
