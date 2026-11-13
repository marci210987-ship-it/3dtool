# -*- coding: utf-8 -*-
"""FCStd für Phase-3-Modelle. Bestehende Phase-2-Dateien werden nicht geändert."""

from __future__ import annotations

from pathlib import Path

import FreeCAD as App
import MeshPart

from hausraster_const import SYSTEM_NAME

PHASE3_VERSION = "0.2-phase3"

HINWEISE = {
    "Modelltyp": ("", "besteck, stufenregal, schraege, halter oder segmentverbinder"),
    "Schubladenbreite": ("mm", "Lichte Innenbreite der Schublade"),
    "Schubladentiefe": ("mm", "Lichte Innentiefe der Schublade"),
    "Verfuegbare_Hoehe": ("mm", "Lichte Innenhöhe; bei der Schräge wird der Winkel ggf. begrenzt"),
    "Schubladenspiel": ("mm", "Spiel je Seite, Standard 1,0 (wie Phase 2)"),
    "Einsatzhoehe": ("mm", "Höhe des Besteckeinsatzes ohne optionale Füsse"),
    "Wandstaerke": ("mm", "Empfohlen 1,2 (3 Bahnen bei 0,4-mm-Düse)"),
    "Bodenstaerke": ("mm", "Boden, Standard 1,6"),
    "Innenradius": ("mm", "Innenecken der Fächer, erleichtert die Reinigung"),
    "Bodenkehle": ("mm", "45°-Übergang Boden/Wand in geschlossenen Fächern"),
    "Trennwandstaerke": ("mm", "Feste oder herausnehmbare Stege, Standard 1,2"),
    "Trennwande_herausnehmbar": ("0/1", "1 = Nuten und separate Trennwände, 0 = fest (weniger Schmutzecken)"),
    "Nutspiel": ("mm", "Spiel der herausnehmbaren Trennwand in der Nut"),
    "Fuesse": ("0/1", "1 = optionale Hausraster-Füsse (Gridfinity-kompatibel), Standard 0"),
    "Passungsspiel": ("mm", "Zusatzspiel der Füsse, Standard 0"),
    "Verbinder_Spiel": ("mm", "Spiel je Kontaktfläche, Standard 0,20 wie Phase 2"),
    "Max_Segmentmass": ("mm", "Sicherheitsrand zum 256-mm-Bauraum, Standard 250"),
    "Fach_1_Breite": ("mm", "Messer, Standard 48 (Annahme, keine Messung)"),
    "Fach_1_Laenge": ("mm", "0 = volle Innentiefe"),
    "Fach_2_Breite": ("mm", "Gabeln, Standard 55 (Annahme)"),
    "Fach_2_Laenge": ("mm", "0 = volle Innentiefe"),
    "Fach_3_Breite": ("mm", "Esslöffel, Standard 55 (Annahme)"),
    "Fach_3_Laenge": ("mm", "0 = volle Innentiefe"),
    "Fach_4_Breite": ("mm", "Teelöffel, Standard 50 (Annahme)"),
    "Fach_4_Laenge": ("mm", "0 = volle Innentiefe"),
    "Fach_5_Breite": ("mm", "Kochbesteck; 0 = Restbreite"),
    "Fach_5_Laenge": ("mm", "0 = volle Innentiefe"),
    "Gesamtbreite": ("mm", "Stufenregal: Gesamtbreite"),
    "Gesamttiefe": ("mm", "Stufenregal: Gesamttiefe"),
    "Ebenenanzahl": ("1", "Stufenregal: 2–6 Ebenen"),
    "Stufenhoehe": ("mm", "Höhendifferenz zwischen zwei Ebenen"),
    "Stufentiefe": ("mm", "Tiefe einer Stufe; 0 = gleichmässig aus Gesamttiefe"),
    "Glasanzahl": ("1", "0 = so viele wie in die Breite passen (Annahme)"),
    "Glasdurchmesser": ("mm", "Annahme typischer Streugläser, keine Messung"),
    "Glaslange": ("mm", "Länge liegend, Annahme 110 mm, keine Messung"),
    "Glasabstand": ("mm", "Abstand zwischen Gläsern, Standard 4"),
    "Stufenlippe": ("mm", "Vordere Lippe / Seitenlippe je Stufe"),
    "Hinterlippe": ("mm", "Hohe Rückwand auf der obersten Stufe"),
    "Neigungswinkel": ("°", "Schrägeinsatz, 5–40; kann durch die verfügbare Höhe begrenzt werden"),
    "Reihen": ("1", "0 = so viele Reihen wie in die Breite passen"),
    "Glasspiel": ("mm", "Halter: Spiel zum eingegebenen Durchmesser, Standard 2"),
    "Wandhoehe": ("mm", "Halter: Wand über dem Boden"),
    "Frontausschnitt": ("0/1", "Halter: 1 = U-Öffnung vorne zum Einschieben"),
}


def add_spreadsheet(doc, params: dict):
    sheet = doc.addObject("Spreadsheet::Sheet", "HIER_MASSE_AENDERN")
    sheet.set("A1", "Parameter")
    sheet.set("B1", "Wert")
    sheet.set("C1", "Einheit")
    sheet.set("D1", "Hinweis")
    sheet.setStyle("A1:D1", "bold", "add")
    row = 2
    for name, value in params.items():
        sheet.set("A%d" % row, name)
        if isinstance(value, str):
            sheet.set("B%d" % row, value)
        elif isinstance(value, int) and not isinstance(value, bool):
            sheet.set("B%d" % row, "%d" % value)
        else:
            sheet.set("B%d" % row, "%.4f" % float(value))
        try:
            sheet.setAlias("B%d" % row, name)
        except Exception:
            pass
        einheit, hinweis = HINWEISE.get(name, ("", ""))
        sheet.set("C%d" % row, einheit)
        sheet.set("D%d" % row, hinweis)
        row += 1
    row += 1
    sheet.set("A%d" % row, "NACH DEM AENDERN")
    sheet.set("B%d" % row, "Macro Hausraster_Phase3_NeuBerechnen.FCMacro starten. Die aktuelle Geometrie ist gespeichert und sofort nutzbar.")
    try:
        sheet.setColumnWidth("A", 200)
        sheet.setColumnWidth("B", 110)
        sheet.setColumnWidth("C", 80)
        sheet.setColumnWidth("D", 460)
    except Exception:
        pass
    return sheet


def embed_source(doc, src_dir: Path):
    td = doc.addObject("App::TextDocument", "HausrasterPhase3Quellcode")
    pieces = []
    for name in (
        "hausraster_const.py",
        "hausraster_geom.py",
        "hausraster_phase3_plan.py",
        "hausraster_phase3_geom.py",
        "hausraster_phase3_fcstd.py",
    ):
        path = src_dir / name
        if path.exists():
            pieces.append("# ===== %s =====\n%s" % (name, path.read_text(encoding="utf-8")))
    td.Text = "\n\n".join(pieces)[:200000]
    return td


def add_shape_object(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def export_stl(shape, path, deflection=0.08):
    path = str(path)
    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=deflection, AngularDeflection=0.174, Relative=False
    )
    mesh.write(path)
    return path


def export_step(shape, path):
    path = str(path)
    shape.exportStep(path)
    return path


def create_document(title, params, shapes: dict, out_fcstd: Path, src_dir: Path, bemerkung: str = ""):
    if out_fcstd.exists():
        out_fcstd.unlink()
    doc = App.newDocument(title)
    add_spreadsheet(doc, params)
    for name, shape in shapes.items():
        add_shape_object(doc, name, shape)
    embed_source(doc, src_dir)
    note = doc.addObject("App::TextDocument", "Lesen")
    note.Text = (
        "%s %s\n\n%s\n\n"
        "Masse nur im Tabellenblatt HIER_MASSE_AENDERN ändern, keine Skizzen anfassen.\n"
        "Danach das Macro Hausraster_Phase3_NeuBerechnen.FCMacro ausführen, damit die Geometrie neu entsteht.\n"
        "Ohne das Macro bleibt die zuletzt gespeicherte Geometrie erhalten (STL/STEP-Export möglich).\n"
        "Küche: PLA ist nicht spülmaschinenfest und weicht bei Wärme. PETG ist formstabiler und lässt sich "
        "besser feucht abwischen, ist aber nicht automatisch lebensmittelecht. Lebensmittelechtheit wird hier "
        "nicht behauptet; sie hängt von Filament, Druck und Reinigung ab und ist nicht geprüft.\n"
    ) % (SYSTEM_NAME, PHASE3_VERSION, bemerkung)
    doc.recompute()
    out_fcstd.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(out_fcstd))
    info = {}
    for name, obj in ((o.Name, o) for o in doc.Objects if hasattr(o, "Shape") and o.Shape and not o.Shape.isNull()):
        sh = obj.Shape
        bb = sh.BoundBox
        info[name] = {
            "is_valid": bool(sh.isValid()),
            "solids": len(sh.Solids),
            "volume_mm3": float(sh.Volume) if sh.Volume else 0.0,
            "bbox": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
            "size": [bb.XLength, bb.YLength, bb.ZLength],
        }
    App.closeDocument(doc.Name)
    return info


def _sheet_text(value):
    """FreeCAD-Spreadsheet-Strings sauber machen (führendes Apostroph, Anführungszeichen)."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.startswith("="):
        s = s[1:].strip()
    # typische Spreadsheet-Präfixe: 'schraege  oder  "'schraege"
    s = s.strip().strip("'").strip('"').strip().strip("'")
    return s


def params_from_sheet(sheet):
    out = {}
    typen = {
        "besteck", "stufenregal", "schraege", "schräge", "halter",
        "segmentverbinder", "stufenregal_schale", "schraege_schale",
    }
    row = 2
    while True:
        try:
            name = sheet.get("A%d" % row)
        except Exception:
            break
        name = _sheet_text(name)
        if not name or name == "NACH DEM AENDERN":
            break
        try:
            val = sheet.getContents("B%d" % row)
        except Exception:
            val = sheet.get("B%d" % row)
        if isinstance(val, str):
            s = _sheet_text(val)
            if s.lower() in typen:
                out[name] = s.lower()
            else:
                try:
                    if "." in s or "e" in s.lower():
                        out[name] = float(s)
                    else:
                        out[name] = int(s)
                except Exception:
                    try:
                        raw = sheet.get("B%d" % row)
                        out[name] = float(raw) if not isinstance(raw, str) else _sheet_text(raw)
                    except Exception:
                        out[name] = s
        else:
            out[name] = val
        row += 1
    return out
