# -*- coding: utf-8 -*-
"""FCStd-Dokumente für Phase 4. Phase-2-Dateien und deren Module bleiben unverändert."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import FreeCAD as App
import MeshPart

from hausraster_const import SYSTEM_NAME, default_params
from hausraster_fcstd import add_shape_object, export_stl, export_step
from hausraster_phase4_geom import PHASE4_VERSION

HINWEISE_PHASE4 = {
    "Herausnehmbare_Trennwaende": ("0/1", "1 = Nuten und separate Trennwände statt fester Fächer"),
    "Deckel": ("0/1", "1 = abnehmbarer Deckel, sitzt auf dem Lippen-Sims"),
    "Deckelstaerke": ("mm", "Deckelplatte, empfohlen 2,0"),
    "Deckel_Spiel": ("mm", "Spiel je Seite zwischen Deckel und Lippe, Standard 0,25"),
    "Trennwand_Spiel": ("mm", "Spiel je Seite in der Nut, Standard 0,25"),
    "Verriegelungsart": ("0/1/2", "0 keine, 1 Rastclip über Stapellippe, 2 Deckelraste"),
    "Kabelkerben": ("0/1", "1 = U-Kerben oben in den Trennwänden für Kabel"),
    "Modelltyp": ("", "Kennzeichnung des Phasen-4-Modells"),
}

# Zusätzliche Hinweise zu den bekannten Phase-2-Parametern, ohne deren Datei zu ändern
HINWEISE_BASIS = {
    "Einheiten_X": ("", "Rastereinheiten in der Breite (1–6)"),
    "Einheiten_Y": ("", "Rastereinheiten in der Tiefe (1–12 laut Grundmodell, Standardgrössen ≤ 6)"),
    "Einheiten_Z": ("", "Höheneinheiten à 7 mm (Lippe kommt oben drauf)"),
    "Wandstaerke": ("mm", "Aussenwand, Standard 1,20 (3 Linien à 0,4 mm)"),
    "Bodenstaerke_Box": ("mm", "Boxboden über dem Fussprofil, Standard 2,25"),
    "Fachanzahl_X": ("", "Fächer in der Breite"),
    "Fachanzahl_Y": ("", "Fächer in der Tiefe"),
    "Trennwandstaerke": ("mm", "Dicke der (festen oder herausnehmbaren) Trennwände"),
    "Passungsspiel": ("mm", "Zusätzliches Spiel je Aussenseite, Standard 0"),
    "Stapellippe": ("0/1", "1 = Lippe oben, stapelbar und deckeltauglich"),
    "Verriegelung": ("0/1", "Plattenparameter, für Boxen ohne direkte Wirkung"),
    "Innenradius": ("mm", "Innenecken"),
    "Raster_mm": ("mm", "42, nicht ändern"),
    "Hoeheneinheit_mm": ("mm", "7, nicht ändern"),
}


def add_spreadsheet_phase4(doc, params: dict):
    sheet = doc.addObject("Spreadsheet::Sheet", "HIER_MASSE_AENDERN")
    sheet.set("A1", "Parameter")
    sheet.set("B1", "Wert")
    sheet.set("C1", "Einheit")
    sheet.set("D1", "Hinweis")
    sheet.setStyle("A1:D1", "bold", "add")
    row = 2
    for name, value in params.items():
        sheet.set("A%d" % row, name)
        if isinstance(value, int) and not isinstance(value, bool):
            sheet.set("B%d" % row, "%d" % value)
        else:
            try:
                sheet.set("B%d" % row, "%.4f" % float(value))
            except Exception:
                sheet.set("B%d" % row, str(value))
        try:
            sheet.setAlias("B%d" % row, name)
        except Exception:
            pass
        einheit, hinweis = HINWEISE_PHASE4.get(name, HINWEISE_BASIS.get(name, ("", "")))
        sheet.set("C%d" % row, einheit)
        sheet.set("D%d" % row, hinweis)
        row += 1
    row += 1
    sheet.set("A%d" % row, "NACH DEM AENDERN")
    sheet.set("B%d" % row,
              "Macro Hausraster_Phase4_NeuBerechnen.FCMacro starten (FreeCAD-Mod HausrasterPhase4). "
              "Die gespeicherte Geometrie bleibt ohne Macro nutzbar (STL/STEP).")
    try:
        sheet.setColumnWidth("A", 220)
        sheet.setColumnWidth("B", 100)
        sheet.setColumnWidth("C", 80)
        sheet.setColumnWidth("D", 460)
    except Exception:
        pass
    return sheet


def embed_source_phase4(doc, src_dir: Path):
    td = doc.addObject("App::TextDocument", "HausrasterQuellcode")
    pieces = []
    for name in (
        "hausraster_const.py",
        "hausraster_geom.py",
        "hausraster_fcstd.py",
        "hausraster_phase4_geom.py",
        "hausraster_phase4_fcstd.py",
    ):
        path = src_dir / name
        if path.exists():
            pieces.append("# ===== %s =====\n%s" % (name, path.read_text(encoding="utf-8")))
    td.Text = "\n\n".join(pieces)[:200000]
    return td


def create_document_phase4(title, params, shapes: dict, out_fcstd: Path, src_dir: Path, bemerkung: str = ""):
    if out_fcstd.exists():
        # Nur eigene neue Dateien dürfen hier landen; Sicherheit: nie Phase-2-Standardboxen
        if out_fcstd.name in ("HR_Box_1x1x3.FCStd", "HR_Box_2x2x3.FCStd"):
            raise RuntimeError("Phase-2-Datei darf nicht überschrieben werden: %s" % out_fcstd)
        out_fcstd.unlink()
    doc = App.newDocument(title)
    add_spreadsheet_phase4(doc, params)
    for name, shape in shapes.items():
        add_shape_object(doc, name, shape)
    embed_source_phase4(doc, src_dir)
    note = doc.addObject("App::TextDocument", "Lesen")
    note.Text = (
        "%s %s\n\n%s\n\n"
        "Masse nur im Tabellenblatt HIER_MASSE_AENDERN ändern, keine Skizzen anfassen.\n"
        "Danach das Macro Hausraster_Phase4_NeuBerechnen.FCMacro ausführen, damit die Geometrie neu entsteht.\n"
        "Ohne das Macro bleibt die zuletzt gespeicherte Geometrie erhalten (STL/STEP-Export möglich).\n"
    ) % (SYSTEM_NAME, PHASE4_VERSION, bemerkung)
    doc.recompute()
    out_fcstd.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(out_fcstd))
    info = {}
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull():
            sh = obj.Shape
            bb = sh.BoundBox
            info[obj.Name] = {
                "is_valid": bool(sh.isValid()),
                "solids": len(sh.Solids),
                "volume": float(sh.Volume or 0),
                "size": [bb.XLength, bb.YLength, bb.ZLength],
            }
    App.closeDocument(doc.Name)
    return info
