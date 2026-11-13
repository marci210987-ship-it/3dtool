# -*- coding: utf-8 -*-
"""Makro-Haken: Apostroph, FreeCADGui, Init.__file__, Schalen-Rebuild, Windows-Pfade."""
from __future__ import annotations

import FreeCAD as App

from qs_common import ROOT, REPORT, _rec
from hausraster_phase3_fcstd import params_from_sheet


def test_macro_hooks():
    p3 = (ROOT / "macros" / "Hausraster_Phase3_NeuBerechnen.FCMacro").read_text(encoding="utf-8")
    if "import FreeCADGui" in p3:
        idx = p3.find("import FreeCADGui")
        window = p3[max(0, idx - 120):idx + 80]
        safe = "try:" in window
        if not safe:
            _rec("Makro", "Phase-3-Makro importiert FreeCADGui ohne try/except", "FEHLERHAFT",
                 details="Unter FreeCADCmd (ohne GUI) schlaegt das Makro fehl, bevor die Geometrie neu berechnet wird.")
            REPORT["fehler"].append({
                "id": "P3_FREECADGUI", "schwere": "hoch",
                "ursache": "import FreeCADGui ohne Schutz im Phase-3-Makro.",
            })
        else:
            _rec("Makro", "Phase-3 FreeCADGui-Import geschuetzt", "BESTANDEN")
    else:
        _rec("Makro", "Phase-3-Makro importiert FreeCADGui nicht", "BESTANDEN")

    init = (ROOT / "FreeCAD_Mod" / "Hausraster" / "Init.py").read_text(encoding="utf-8")
    if "Path(__file__)" in init and "except" not in init:
        _rec("Makro", "Hausraster Init.py verwendet __file__ ohne Fallback", "EINGESCHRAENKT",
             details="Wenn FreeCAD Init.py ohne __file__ ausfuehrt, schlaegt das Laden des Mods fehl.")
        REPORT["fehler"].append({
            "id": "INIT_FILE", "schwere": "niedrig",
            "ursache": "Path(__file__) ohne Fallback in Init.py.",
        })
    else:
        _rec("Makro", "Init.py __file__-Fallback", "BESTANDEN")

    doc = App.newDocument("qs_sheet_apostroph")
    try:
        sh = doc.addObject("Spreadsheet::Sheet", "HIER_MASSE_AENDERN")
        sh.set("A2", "Modelltyp")
        sh.set("B2", "schraege")
        try:
            sh.setAlias("B2", "Modelltyp")
        except Exception:
            pass
        sh.set("A3", "Schubladenbreite")
        sh.set("B3", "200")
        try:
            sh.setAlias("B3", "Schubladenbreite")
        except Exception:
            pass
        doc.recompute()
        raw_b2_get = sh.get("B2")
        try:
            raw_b2_contents = sh.getContents("B2")
        except Exception as exc:
            raw_b2_contents = "<getContents Fehler: %s>" % exc
        params = params_from_sheet(sh)
        typ = params.get("Modelltyp")
        _rec("Makro", "params_from_sheet liest Modelltyp",
             "BESTANDEN" if typ in ("schraege", "schräge") else "FEHLERHAFT",
             messwerte={"get": repr(raw_b2_get), "getContents": repr(raw_b2_contents),
                        "params_typ": typ, "params": {k: params[k] for k in list(params)[:12]}})
        if typ not in ("schraege", "schräge"):
            REPORT["fehler"].append({
                "id": "P3_APOSTROPH", "schwere": "hoch",
                "ursache": "params_from_sheet liefert Modelltyp=%r (get=%r, getContents=%r)." % (
                    typ, raw_b2_get, raw_b2_contents),
            })
    finally:
        App.closeDocument(doc.Name)

    if "schale" not in p3.lower() and "Schalenwand" not in p3:
        _rec("Makro", "Phase-3-Makro unterscheidet Schale nicht von Vollkoerper", "FEHLERHAFT",
             details=(
                 "Schalen-FCStd haben Modelltyp schraege bzw. stufenregal plus Parameter Schalenwand. "
                 "Das Makro ruft stufen_teile/schraege_teile auf und wuerde die leichte Schale durch einen Vollkoerper ersetzen. "
                 "hausraster_phase3_schale.py liegt zudem nicht im FreeCAD-Mod."
             ))
        REPORT["fehler"].append({
            "id": "P3_SCHALE_REBUILD", "schwere": "hoch",
            "ursache": "Kein Schalen-Zweig im Phase-3-Makro; Modul fehlt im Mod-Paket.",
        })
    else:
        _rec("Makro", "Phase-3-Makro hat Schalen-Zweig", "BESTANDEN")

    p4 = (ROOT / "macros" / "Hausraster_Phase4_NeuBerechnen.FCMacro").read_text(encoding="utf-8")
    if "APPDATA" not in p4 and "FreeCAD/Mod/HausrasterPhase4" not in p4.replace("\\", "/"):
        _rec("Makro", "Phase-4-Makro findet den Mod unter Windows (%APPDATA%) nicht zuverlaessig", "FEHLERHAFT",
             details="Hart codierte Pfade zeigen auf /workspace/ordnungssystem. Auf einem Windows-Rechner schlaegt der Import fehl, sofern der Mod nicht zufaellig ueber einen anderen Kandidaten gefunden wird.")
        REPORT["fehler"].append({
            "id": "P4_PFAD", "schwere": "hoch",
            "ursache": "Phase-4-Makro ohne %APPDATA%\\FreeCAD\\Mod-Kandidaten, mit Box-Pfaden.",
        })
    else:
        _rec("Makro", "Phase-4-Makro hat portable Mod-Pfade", "BESTANDEN")

    p2 = (ROOT / "macros" / "Hausraster_NeuBerechnen.FCMacro").read_text(encoding="utf-8")
    if "APPDATA" not in p2:
        _rec("Makro", "Phase-2-Makro nennt %APPDATA% nicht explizit", "EINGESCHRAENKT",
             details="Es sucht unter ~/.local/share/FreeCAD/Mod und relativ zu __file__. Unter Windows haengt der Erfolg daran, dass der geladene Mod bereits in sys.path steht.")
    else:
        _rec("Makro", "Phase-2-Makro hat APPDATA-Pfad", "BESTANDEN")
