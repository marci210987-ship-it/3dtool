# -*- coding: utf-8 -*-
"""FreeCAD-Worker. Läuft nur innerhalb von FreeCADCmd.

Protokoll: eine JSON-Zeile je Anfrage über einen lokalen TCP-Socket.
FreeCADCmd liest das Startskript von stdin; der Socket bleibt danach frei.
"""

from __future__ import annotations

import json
import math
import os
import socket
import sys
import traceback
from pathlib import Path


def _src_auf_pfad():
    src = os.environ.get("CADSTUDIO_SRC")
    root = os.environ.get("CADSTUDIO_ROOT")
    for entry in (src, root):
        if entry and entry not in sys.path:
            sys.path.insert(0, entry)


def _antwort(ok, ergebnis=None, fehler=""):
    return {"ok": ok, "result": ergebnis, "fehler": fehler}


def _genaue_bbox(shape):
    """Genaue Bounding-Box; BoundBox ist bei gekrümmten Flächen um bis zu ~1 mm zu groß."""
    try:
        return shape.optimalBoundingBox()
    except Exception:
        return shape.BoundBox


def _drucklage(shape, App):
    bb = _genaue_bbox(shape)
    if abs(bb.ZMin) > 1e-4:
        shape = shape.copy()
        shape.translate(App.Vector(0, 0, -bb.ZMin))
    return shape


def _solid_info(shape) -> dict:
    bb = _genaue_bbox(shape)
    return {
        "valid": bool(shape.isValid()),
        "solids": len(shape.Solids),
        "volume_mm3": float(shape.Volume) if shape.Volume else 0.0,
        "bbox_mm": [float(bb.XLength), float(bb.YLength), float(bb.ZLength)],
        "zmin": float(bb.ZMin),
    }


def _mesh_info(Mesh, pfad: Path) -> dict:
    mesh = Mesh.Mesh(str(pfad))
    bb = mesh.BoundBox
    info = {
        "punkte": int(mesh.CountPoints),
        "facetten": int(mesh.CountFacets),
        "bbox_mm": [float(bb.XLength), float(bb.YLength), float(bb.ZLength)],
        "zmin": float(bb.ZMin),
    }
    if hasattr(mesh, "isSolid"):
        info["is_solid"] = bool(mesh.isSolid())
    if hasattr(mesh, "hasNonManifolds"):
        info["nicht_mannigfaltig"] = bool(mesh.hasNonManifolds())
    if hasattr(mesh, "hasSelfIntersections"):
        info["selbstschnitt"] = bool(mesh.hasSelfIntersections())
    ok = info.get("is_solid", False) and not info.get("nicht_mannigfaltig", False)
    if info.get("selbstschnitt"):
        ok = False
    info["ok"] = ok
    if not ok:
        info["fehler"] = "FreeCAD-Mesh ist nicht geschlossen bzw. nicht mannigfaltig."
    return info


def _speichern(App, fcstd, title, params, shapes: dict, src_dir: Path, bemerkung: str):
    from hausraster_fcstd import add_spreadsheet, add_shape_object, embed_source

    if fcstd.exists():
        fcstd.unlink()
    fcstd.parent.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument(title)
    add_spreadsheet(doc, params)
    for name, shape in shapes.items():
        add_shape_object(doc, name, shape)
    embed_source(doc, src_dir)
    note = doc.addObject("App::TextDocument", "Lesen")
    note.Text = bemerkung
    doc.recompute()
    doc.saveAs(str(fcstd))
    App.closeDocument(doc.Name)


def _neu_laden(App, pfad: Path) -> dict:
    doc = App.openDocument(str(pfad))
    try:
        blaetter = [o for o in doc.Objects if getattr(o, "TypeId", "") == "Spreadsheet::Sheet"]
        koerper = []
        for obj in doc.Objects:
            shape = getattr(obj, "Shape", None)
            if shape is None or shape.isNull() or not shape.Solids:
                continue
            bb = shape.BoundBox
            koerper.append(
                {
                    "name": obj.Name,
                    "valid": bool(shape.isValid()),
                    "solids": len(shape.Solids),
                    "volume_mm3": float(shape.Volume) if shape.Volume else 0.0,
                    "bbox_mm": [float(bb.XLength), float(bb.YLength), float(bb.ZLength)],
                }
            )
        ok = bool(blaetter) and len(koerper) >= 1 and all(k["valid"] and k["solids"] >= 1 for k in koerper)
        return {
            "ok": ok,
            "tabellenblatt": bool(blaetter),
            "koerper": koerper,
            "fehler": "" if ok else "FCStd ohne gültigen Körper oder ohne Tabellenblatt.",
        }
    finally:
        App.closeDocument(doc.Name)


def _rechteck_draht(x, y, b, t, radius):
    """Rechteck als Drahtzug, bei radius > 0 mit abgerundeten Ecken."""
    import FreeCAD as App
    import Part

    if radius <= 1e-9:
        return Part.makePolygon([App.Vector(x, y, 0), App.Vector(x + b, y, 0), App.Vector(x + b, y + t, 0), App.Vector(x, y + t, 0), App.Vector(x, y, 0)])
    r = radius
    z = App.Vector(0, 0, 1)
    kanten = [
        Part.makeLine(App.Vector(x + r, y, 0), App.Vector(x + b - r, y, 0)),
        Part.makeCircle(r, App.Vector(x + b - r, y + r, 0), z, 270, 360),
        Part.makeLine(App.Vector(x + b, y + r, 0), App.Vector(x + b, y + t - r, 0)),
        Part.makeCircle(r, App.Vector(x + b - r, y + t - r, 0), z, 0, 90),
        Part.makeLine(App.Vector(x + b - r, y + t, 0), App.Vector(x + r, y + t, 0)),
        Part.makeCircle(r, App.Vector(x + r, y + t - r, 0), z, 90, 180),
        Part.makeLine(App.Vector(x, y + t - r, 0), App.Vector(x, y + r, 0)),
        Part.makeCircle(r, App.Vector(x + r, y + r, 0), z, 180, 270),
    ]
    return Part.Wire(Part.sortEdges(kanten)[0])


def _kante_bearbeiten(shape, oben: bool, art: int, mm: float, bezeichnung: str):
    """Fase (art 1) oder Rundung (art 2) an der Außenkante der obersten bzw. untersten ebenen Fläche."""
    if mm <= 1e-9 or art == 0:
        return shape
    bb = shape.BoundBox
    z_ref = bb.ZMax if oben else bb.ZMin
    kandidaten = []
    for f in shape.Faces:
        if f.Surface.TypeId != "Part::GeomPlane":
            continue
        n = f.normalAt(0, 0)
        if abs(abs(n.z) - 1.0) > 1e-6:
            continue
        if abs(f.BoundBox.ZMax - z_ref) > 1e-6 or abs(f.BoundBox.ZMin - z_ref) > 1e-6:
            continue
        kandidaten.append(f)
    if not kandidaten:
        raise ValueError("%s: Keine ebene Fläche an der Kante gefunden." % bezeichnung)
    flaeche = max(kandidaten, key=lambda f: f.Area)
    aussen = flaeche.OuterWire.Edges
    kanten = [e for e in shape.Edges if any(e.isSame(k) for k in aussen)]
    try:
        neu = shape.makeFillet(mm, kanten) if art == 2 else shape.makeChamfer(mm, kanten)
    except Exception as exc:
        raise ValueError("%s mit %.2f mm ist an diesem Teil nicht möglich (%s). Kleineren Wert wählen." % (bezeichnung, mm, exc))
    if not neu.isValid() or len(neu.Solids) != 1:
        raise ValueError("%s mit %.2f mm ergibt keinen gültigen Körper. Kleineren Wert wählen." % (bezeichnung, mm))
    return neu


def _kontur_abstand(form: dict, px: float, py: float) -> float:
    """Abstand eines Punkts zur Umrisslinie einer Form (Draufsicht)."""
    import math

    typ = form["typ"]
    if typ == "kreis":
        return abs(math.hypot(px - float(form["x"]), py - float(form["y"])) - float(form["r"]))
    if typ == "rechteck":
        x, y, b, t = float(form["x"]), float(form["y"]), float(form["b"]), float(form["t"])
        r = float(form.get("radius") or 0.0)
        winkel = float(form.get("winkel") or 0.0)
        mx, my = x + b / 2.0, y + t / 2.0
        if winkel:
            # Punkt in das Koordinatensystem des ungedrehten Rechtecks zurückdrehen
            w = math.radians(-winkel)
            dx, dy = px - mx, py - my
            px = mx + dx * math.cos(w) - dy * math.sin(w)
            py = my + dx * math.sin(w) + dy * math.cos(w)
        qx = abs(px - mx) - (b / 2.0 - r)
        qy = abs(py - my) - (t / 2.0 - r)
        d = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
        return abs(d)
    punkte = [(float(a), float(c)) for a, c in form["punkte"]]
    beste = float("inf")
    for i, (ax, ay) in enumerate(punkte):
        bx, by = punkte[(i + 1) % len(punkte)]
        dx, dy = bx - ax, by - ay
        laenge2 = dx * dx + dy * dy
        u = 0.0 if laenge2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / laenge2))
        beste = min(beste, math.hypot(px - (ax + u * dx), py - (ay + u * dy)))
    return beste


def _form_draht(form: dict):
    import FreeCAD as App
    import Part

    typ = form["typ"]
    if typ == "rechteck":
        x, y, b, t = float(form["x"]), float(form["y"]), float(form["b"]), float(form["t"])
        draht = _rechteck_draht(x, y, b, t, float(form.get("radius") or 0.0))
        winkel = float(form.get("winkel") or 0.0)
        if winkel % 360:
            draht = draht.copy()
            draht.rotate(App.Vector(x + b / 2.0, y + t / 2.0, 0), App.Vector(0, 0, 1), winkel)
        return draht
    if typ == "kreis":
        return Part.Wire(Part.makeCircle(float(form["r"]), App.Vector(float(form["x"]), float(form["y"]), 0), App.Vector(0, 0, 1)))
    radius = float(form.get("radius") or 0.0)
    if radius > 1e-9:
        return _polygon_gerundet([(float(px), float(py)) for px, py in form["punkte"]], radius)
    pts = [App.Vector(float(px), float(py), 0) for px, py in form["punkte"]]
    return Part.makePolygon(pts + [pts[0]])


def _polygon_gerundet(punkte, radius: float):
    """Vieleck mit Kreisbögen (Radius) an allen Ecken."""
    import FreeCAD as App
    import Part

    n = len(punkte)
    ecken = []
    for i, (vx, vy) in enumerate(punkte):
        px, py = punkte[i - 1]
        nx, ny = punkte[(i + 1) % n]
        a = (px - vx, py - vy)
        b = (nx - vx, ny - vy)
        la, lb = math.hypot(*a), math.hypot(*b)
        ua, ub = (a[0] / la, a[1] / la), (b[0] / lb, b[1] / lb)
        cos_t = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1]))
        theta = math.acos(cos_t)
        if theta > math.pi - 1e-6 or theta < 1e-6:
            ecken.append((App.Vector(vx, vy, 0), None, App.Vector(vx, vy, 0)))
            continue
        tl = radius / math.tan(theta / 2.0)
        if tl > min(la, lb) / 2.0 + 1e-9:
            raise ValueError("Der Eckenradius %.1f mm ist am Punkt %d zu groß für die anliegenden Seiten." % (radius, i + 1))
        p1 = App.Vector(vx + ua[0] * tl, vy + ua[1] * tl, 0)
        p2 = App.Vector(vx + ub[0] * tl, vy + ub[1] * tl, 0)
        bis = (ua[0] + ub[0], ua[1] + ub[1])
        lbis = math.hypot(*bis)
        bis = (bis[0] / lbis, bis[1] / lbis)
        abstand = radius / math.sin(theta / 2.0)
        c = (vx + bis[0] * abstand, vy + bis[1] * abstand)
        mitte = App.Vector(c[0] - bis[0] * radius, c[1] - bis[1] * radius, 0)
        ecken.append((p1, mitte, p2))
    kanten = []
    for i, (p1, mitte, p2) in enumerate(ecken):
        if mitte is not None:
            kanten.append(Part.Arc(p1, mitte, p2).toShape())
        naechste = ecken[(i + 1) % n][0]
        if (p2 - naechste).Length > 1e-9:
            kanten.append(Part.makeLine(p2, naechste))
    return Part.Wire(Part.sortEdges(kanten)[0])


def _text_koerper(form: dict, z0: float, h0: float):
    import FreeCAD as App
    import Part
    from sidecar.pixelschrift import text_rechtecke

    boxen = [
        Part.makeBox(b, t, h0, App.Vector(x, y, z0))
        for x, y, b, t in text_rechtecke(str(form["text"]), float(form["x"]), float(form["y"]), float(form["schrift_mm"]))
    ]
    if not boxen:
        raise ValueError("Der Text enthält keine Zeichen.")
    koerper = boxen[0]
    for kasten in boxen[1:]:
        koerper = koerper.fuse(kasten)
    return koerper.removeSplitter()


def _senk_werkzeuge(form: dict, hoehe_gesamt: float) -> list:
    """Zusätzliche Schneidkörper für Senkung, Gegenbohrung oder Sechskant an einem runden Loch."""
    import FreeCAD as App
    import Part

    art = form.get("senk_art") or "keine"
    if art == "keine" or form["typ"] != "kreis" or not form.get("loch"):
        return []
    r = float(form["r"])
    gross = float(form["senk_d_mm"]) / 2.0
    tief = (gross - r) if art == "senkung" else float(form.get("senk_t_mm") or 0.0)
    oben = (form.get("senk_seite") or "oben") != "unten"
    x, y = float(form["x"]), float(form["y"])
    z_unten = hoehe_gesamt - tief if oben else 0.0
    ueber = 1.0
    if art == "senkung":
        if oben:
            return [Part.makeCone(r, gross + ueber, tief + ueber, App.Vector(x, y, hoehe_gesamt - tief), App.Vector(0, 0, 1))]
        return [Part.makeCone(gross + ueber, r, tief + ueber, App.Vector(x, y, -ueber), App.Vector(0, 0, 1))]
    z_start = z_unten if oben else -ueber
    if art == "gegenbohrung":
        return [Part.makeCylinder(gross, tief + ueber, App.Vector(x, y, z_start), App.Vector(0, 0, 1))]
    umkreis = gross / math.cos(math.radians(30))
    ecken = [App.Vector(x + umkreis * math.cos(math.radians(60 * k)), y + umkreis * math.sin(math.radians(60 * k)), z_start) for k in range(6)]
    flaeche = Part.Face(Part.makePolygon(ecken + [ecken[0]]))
    return [flaeche.extrude(App.Vector(0, 0, tief + ueber))]


def _seitenloch_werkzeug(s: dict, bb):
    import FreeCAD as App
    import Part

    seite = s["seite"]
    pos = float(s["pos_mm"])
    z = float(s["z_mm"])
    tiefe = float(s.get("tiefe_mm") or 0.0)
    if (s.get("art") or "rund") == "rund":
        b = h = float(s["d_mm"])
    else:
        b, h = float(s["b_mm"]), float(s["h_mm"])
    ueber = 1.0
    if seite in ("vorne", "hinten"):
        laenge = bb.YLength
        a0, a1 = bb.YMin, bb.YMax
    else:
        laenge = bb.XLength
        a0, a1 = bb.XMin, bb.XMax
    if seite in ("vorne", "links"):
        von, bis = a0 - ueber, (a1 + ueber if tiefe <= 0 else a0 + tiefe)
    else:
        von, bis = (a0 - ueber if tiefe <= 0 else a1 - tiefe), a1 + ueber
    rund = (s.get("art") or "rund") == "rund"
    if seite in ("vorne", "hinten"):
        if rund:
            return Part.makeCylinder(b / 2.0, bis - von, App.Vector(pos, von, z), App.Vector(0, 1, 0))
        return Part.makeBox(b, bis - von, h, App.Vector(pos - b / 2.0, von, z - h / 2.0))
    if rund:
        return Part.makeCylinder(b / 2.0, bis - von, App.Vector(von, pos, z), App.Vector(1, 0, 0))
    return Part.makeBox(bis - von, b, h, App.Vector(von, pos - b / 2.0, z - h / 2.0))


def _profil_koerper(params: dict):
    import FreeCAD as App
    import Part

    dx, dy = float(params.get("DrehX") or 0.0), float(params.get("DrehY") or 0.0)
    pts = [App.Vector(dx + float(r), dy, float(z)) for r, z in params["Profil"]]
    flaeche = Part.Face(Part.makePolygon(pts + [pts[0]]))
    koerper = flaeche.revolve(App.Vector(dx, dy, 0), App.Vector(0, 0, 1), 360)
    if koerper.ShapeType != "Solid":
        koerper = Part.makeSolid(koerper) if koerper.ShapeType == "Shell" else Part.Solid(koerper)
    return koerper


def _form_koerper(form: dict, z0: float, h0: float, schraege: float):
    """Körper einer Form: gerade Extrusion, mit Schräge (Verjüngung/Konus) oder als Keil."""
    import FreeCAD as App
    import Part

    if form["typ"] == "text":
        return _text_koerper(form, z0, h0)
    keil = float(form.get("keil_mm") or 0.0) if form["typ"] == "rechteck" else 0.0
    if keil:
        x, y, b, t = float(form["x"]), float(form["y"]), float(form["b"]), float(form["t"])
        profil = Part.makePolygon([
            App.Vector(x, y, 0), App.Vector(x, y + t, 0),
            App.Vector(x, y + t, h0 + keil), App.Vector(x, y, h0), App.Vector(x, y, 0),
        ])
        koerper = Part.Face(profil).extrude(App.Vector(b, 0, 0))
    elif schraege:
        unten = _form_draht(form)
        # Material: Schräge verjüngt nach oben (nach innen). Loch: weitet sich nach oben (nach außen).
        versatz = schraege if form.get("loch") else -schraege
        oben = unten.makeOffset2D(versatz, 2)
        wires = oben.Wires if hasattr(oben, "Wires") else [oben]
        if len(wires) != 1 or not wires[0].isClosed():
            raise ValueError("Die Schräge lässt sich an dieser Form nicht berechnen. Kleineren Wert wählen.")
        oben = wires[0].copy()
        oben.translate(App.Vector(0, 0, h0))
        koerper = Part.makeLoft([unten, oben], True, True)
    else:
        koerper = Part.Face(_form_draht(form)).extrude(App.Vector(0, 0, h0))
    koerper.translate(App.Vector(0, 0, z0))
    return koerper


def _form_kanten(shape, formen: list, hoehe: float, boden: float):
    """Fase oder Rundung am Oberrand einzelner Formen (Material) bzw. am Lochrand (Löcher)."""
    for index, form in enumerate(formen, 1):
        art = {"fase": 1, "rund": 2}.get(form.get("kante_art") or "keine", 0)
        mm = float(form.get("kante_mm") or 0.0)
        if not art or mm <= 1e-9:
            continue
        bezeichnung = "Kante an Form %d" % index
        if form.get("loch"):
            z0 = float(form["z_mm"]) if form.get("z_mm") not in (None, "") else boden
            h0 = float(form["h_mm"]) if form.get("h_mm") not in (None, "") else hoehe - z0 + 1.0
            z_min, z_max = z0, z0 + h0
        else:
            z0 = float(form.get("z_mm") or 0.0)
            h0 = float(form["h_mm"]) if form.get("h_mm") not in (None, "") else hoehe - z0
            z_min = z_max = z0 + h0
        kandidaten = []
        for e in shape.Edges:
            bb = e.BoundBox
            if bb.ZLength > 1e-5 or bb.ZMin < z_min - 1e-5 or bb.ZMax > z_max + 1e-5:
                continue
            mitte = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
            if _kontur_abstand(form, mitte.x, mitte.y) < 0.02:
                kandidaten.append((bb.ZMin, e))
        if not kandidaten:
            raise ValueError("%s: Am Rand dieser Form wurde keine Kante gefunden (verdeckt oder weggeschnitten)." % bezeichnung)
        z_oben = max(z for z, _ in kandidaten)
        kanten = [e for z, e in kandidaten if abs(z - z_oben) < 1e-5]
        try:
            neu = shape.makeFillet(mm, kanten) if art == 2 else shape.makeChamfer(mm, kanten)
        except Exception as exc:
            raise ValueError("%s mit %.2f mm ist nicht möglich (%s). Kleineren Wert wählen." % (bezeichnung, mm, exc))
        if not neu.isValid() or len(neu.Solids) != 1:
            raise ValueError("%s mit %.2f mm ergibt keinen gültigen Körper. Kleineren Wert wählen." % (bezeichnung, mm))
        shape = neu
    return shape


def _eigen_shape(params: dict):
    """Extrudiert die gezeichneten Formen. Löcher schneiden ab der Bodenhöhe."""
    import FreeCAD as App
    import Part

    hoehe = float(params["Hoehe"])
    boden = float(params.get("Boden") or 0.0)
    hoehe_gesamt = hoehe
    for f in params["Formen"]:
        if not f.get("loch"):
            z_f = float(f.get("z_mm") or 0.0)
            h_f = float(f["h_mm"]) if f.get("h_mm") not in (None, "") else hoehe - z_f
            k_f = float(f.get("keil_mm") or 0.0) if f["typ"] == "rechteck" else 0.0
            hoehe_gesamt = max(hoehe_gesamt, z_f + h_f + max(0.0, k_f))
    for _r, z_p in params.get("Profil") or []:
        hoehe_gesamt = max(hoehe_gesamt, float(z_p))
    plus = _profil_koerper(params) if params.get("Profil") else None
    minus = []
    for form in params["Formen"]:
        schraege = float(form.get("schraege_mm") or 0.0)
        if form.get("loch"):
            # Loch: Standard ab Boden bis über die Oberkante, mit z_mm/h_mm auch als Tasche an beliebiger Höhe
            z0 = float(form["z_mm"]) if form.get("z_mm") not in (None, "") else boden
            standard = form.get("h_mm") in (None, "")
            h0 = hoehe_gesamt - z0 + 1.0 if standard else float(form["h_mm"])
            if standard and schraege:
                # Die Aufweitung gilt bis zur Oberkante; das Werkzeug ragt 1 mm darüber hinaus
                schraege = schraege * h0 / max(h0 - 1.0, 1e-6)
            minus.append(_form_koerper(form, z0, h0, schraege))
            minus.extend(_senk_werkzeuge(form, hoehe_gesamt))
        else:
            z0 = float(form.get("z_mm") or 0.0)
            h0 = float(form["h_mm"]) if form.get("h_mm") not in (None, "") else hoehe - z0
            koerper = _form_koerper(form, z0, h0, schraege)
            plus = koerper if plus is None else plus.fuse(koerper)
    if plus is None:
        raise ValueError("Keine Form, die Material hinzufügt.")
    for loch in minus:
        plus = plus.cut(loch)
    plus = plus.removeSplitter()
    plus = _form_kanten(plus, params["Formen"], hoehe_gesamt, boden)
    plus = _kante_bearbeiten(plus, True, int(params.get("KanteObenArt") or 0), float(params.get("KanteObenMm") or 0.0), "Obere Kante")
    plus = _kante_bearbeiten(plus, False, 1, float(params.get("KanteUntenMm") or 0.0), "Untere Fase")
    box = _genaue_bbox(plus)
    for seitenloch in params.get("Seitenloecher") or []:
        plus = plus.cut(_seitenloch_werkzeug(seitenloch, box))
    if params.get("Seitenloecher"):
        plus = plus.removeSplitter()
    return plus


def _shapes_fuer(teil: dict):
    import FreeCAD as App
    rolle = teil["rolle"]
    params = teil["params"]
    if rolle == "grundplatte":
        from hausraster_geom import make_plate_shape

        return {"Grundplatte": _drucklage(make_plate_shape(params), App)}, {"zentriert": True}
    if rolle == "box":
        from hausraster_geom import make_box_shape

        return {"Box": _drucklage(make_box_shape(params), App)}, {"zentriert": True}
    if rolle == "phase4":
        from hausraster_phase4_geom import make_phase4_box

        _p, shapes, _hinweise = make_phase4_box(params)
        return {name: _drucklage(shape, App) for name, shape in shapes.items()}, {"zentriert": True}
    if rolle == "verbinder":
        from hausraster_geom import make_verbinder_clip_shape

        return {"Plattenverbinder": _drucklage(make_verbinder_clip_shape(params, drucklage=True), App)}, {"zentriert": True}
    if rolle == "rastclip":
        from hausraster_geom import make_rastclip_shape

        return {"Rastclip": _drucklage(make_rastclip_shape(params), App)}, {"zentriert": False}
    if rolle == "eigen":
        return {"Eigenteil": _drucklage(_eigen_shape(params), App)}, {"zentriert": False}
    if rolle == "ersatzteil":
        from sidecar.ersatzteil_geom import baue_ersatzteil

        return {"Ersatzteil": _drucklage(baue_ersatzteil(params), App)}, {"zentriert": False}
    if rolle == "kabel":
        from sidecar.kabel_geom import baue_kabel

        return {"Kabel": _drucklage(baue_kabel(params), App)}, {"zentriert": False}
    if rolle == "gehaeuse":
        from sidecar.gehaeuse_geom import baue_gehaeuse

        name = "Deckel" if str(params.get("teil")) == "deckel" else "Gehäuse"
        return {name: _drucklage(baue_gehaeuse(params), App)}, {"zentriert": False}
    if rolle == "besteck":
        from hausraster_phase3_geom import besteck_teile

        plan, shapes = besteck_teile(params)
        meta = {"zentriert": False, "segmente": []}
        ausgabe = {}
        for name, shape in shapes.items():
            ausgabe[name] = _drucklage(shape, App)
        for seg in plan.segmente:
            meta["segmente"].append(
                {"name": "Segment_%d_%d" % (seg.ix + 1, seg.iy + 1), "x0": seg.x0, "y0": seg.y0, "breite": seg.breite, "tiefe": seg.tiefe}
            )
        return ausgabe, meta
    raise ValueError("Unbekannte Rolle %s" % rolle)


def _passt_soll(ist, soll, tol=0.6) -> str:
    if not soll:
        return ""
    diffs = [abs(float(ist[i]) - float(soll[i])) for i in range(3)]
    if any(d > tol for d in diffs):
        return "BREP-Mass %.2f×%.2f×%.2f mm weicht vom Soll %.2f×%.2f×%.2f mm ab." % (
            ist[0], ist[1], ist[2], soll[0], soll[1], soll[2]
        )
    return ""


def _bauraum_fehler(bbox) -> str:
    grenzen = (256.0, 256.0, 256.0)
    if any(bbox[i] > grenzen[i] + 0.2 for i in range(3)):
        return "Teil überschreitet den Bauraum 256 mm: %.1f×%.1f×%.1f mm." % tuple(bbox)
    return ""


def baue_teil(teil: dict, out_dir: Path) -> dict:
    import FreeCAD as App
    import Mesh
    from hausraster_fcstd import export_stl
    from sidecar.paths import HAUSRASTER_SRC

    shapes, meta = _shapes_fuer(teil)
    dateien = []
    fehler = []
    hinweise: list[str] = []
    soll = teil.get("soll_mm")
    haupt = True
    for name, shape in shapes.items():
        info = _solid_info(shape)
        datei_id = teil["id"] if len(shapes) == 1 else "%s_%s" % (teil["id"], name)
        stl = out_dir / ("%s.stl" % datei_id)
        fcstd = out_dir / ("%s.FCStd" % datei_id)
        if not info["valid"] or info["solids"] != 1 or info["volume_mm3"] <= 1.0:
            fehler.append(
                "%s besteht aus mehreren getrennten Körpern oder ist ungültig. Formen müssen sich berühren oder überlappen, auch in der Höhe." % datei_id
                if teil["rolle"] == "eigen"
                else "%s ist kein einzelner gültiger Körper." % datei_id
            )
            dateien.append({"id": datei_id, "name": name, "ok": False, "solid": info, "stl": str(stl), "fcstd": str(fcstd)})
            continue
        bauraum = _bauraum_fehler(info["bbox_mm"])
        soll_fehler = ""
        if haupt and teil["rolle"] in ("grundplatte", "box", "phase4", "eigen", "ersatzteil", "kabel", "gehaeuse"):
            soll_fehler = _passt_soll(info["bbox_mm"], soll)
        haupt = False
        if bauraum or soll_fehler:
            fehler.append(bauraum or soll_fehler)
            dateien.append({"id": datei_id, "name": name, "ok": False, "solid": info, "fehler": bauraum or soll_fehler})
            continue
        export_stl(shape, stl)
        if teil["rolle"] == "eigen":
            from sidecar.druckpruefung_geom import druckhinweise

            hinweise.extend("%s: %s" % (teil.get("name") or datei_id, h) for h in druckhinweise(shape))
        params = dict(teil["params"])
        formen_text = ""
        if teil["rolle"] == "eigen":
            # Das Tabellenblatt kennt nur Zahlen; die Formen stehen im Lesen-Text.
            formen_text = "\nFormen (mm, Draufsicht): " + json.dumps(params.pop("Formen", []), ensure_ascii=False)
            for schluessel, titel in (("Seitenloecher", "Seitenlöcher"), ("Profil", "Drehprofil (Radius, Höhe)")):
                eintrag = params.pop(schluessel, None)
                if eintrag:
                    formen_text += "\n%s: %s" % (titel, json.dumps(eintrag, ensure_ascii=False))
        if teil["rolle"] in ("ersatzteil", "kabel", "gehaeuse"):
            texte = {k: v for k, v in params.items() if not isinstance(v, (int, float))}
            for key in texte:
                params.pop(key)
            formen_text = "\n" + "\n".join("%s: %s" % (k, v) for k, v in texte.items())
        bemerkung = (
            "Hausraster 0.2-qs1, erzeugt von CAD Studio.\n"
            "Teil %s – %s.\n"
            "Masse im Tabellenblatt HIER_MASSE_AENDERN. Geometrie entsteht neu, "
            "wenn das Makro Hausraster_NeuBerechnen.FCMacro ausgeführt wird.\n"
            "Ursprungsplatten ohne QS1 nicht verwenden.\n"
            "Schubladenspiel und Verbinder-Spiel sind ungeprüfte Vorgaben."
            % (datei_id, teil.get("name") or name)
        ) + formen_text
        _speichern(App, fcstd, datei_id, params, {name: shape}, HAUSRASTER_SRC, bemerkung)
        mesh = _mesh_info(Mesh, stl)
        reload = _neu_laden(App, fcstd)
        mesh_bbox_ok = all(abs(mesh["bbox_mm"][i] - info["bbox_mm"][i]) <= 0.8 for i in range(3))
        ok = mesh.get("ok") and mesh_bbox_ok and reload.get("ok") and stl.stat().st_size > 200 and fcstd.stat().st_size > 200
        if not mesh_bbox_ok:
            fehler.append("%s: Mesh-Bounding-Box passt nicht zum Körper." % datei_id)
        if not mesh.get("ok"):
            fehler.append("%s: %s" % (datei_id, mesh.get("fehler") or "Mesh-Prüfung fehlgeschlagen"))
        if not reload.get("ok"):
            fehler.append("%s: %s" % (datei_id, reload.get("fehler")))
        platz = {"zentriert": bool(meta.get("zentriert")), "z_mm": 0.0}
        if teil.get("lage"):
            platz.update(teil["lage"])
        if teil["rolle"] == "besteck":
            seg = next((s for s in meta.get("segmente", []) if s["name"] == name), None)
            if seg and teil.get("lage"):
                platz = {
                    "zentriert": False,
                    "links_mm": teil["lage"]["links_mm"] + seg["x0"],
                    "vorne_mm": teil["lage"]["vorne_mm"] + seg["y0"],
                    "breite_mm": seg["breite"],
                    "tiefe_mm": seg["tiefe"],
                }
        dateien.append(
            {
                "id": datei_id,
                "name": name,
                "ok": ok,
                "stl": str(stl),
                "fcstd": str(fcstd),
                "bytes_stl": stl.stat().st_size,
                "bytes_fcstd": fcstd.stat().st_size,
                "solid": info,
                "mesh_freecad": mesh,
                "fcstd_erneut_geladen": reload,
                "platz": platz,
                "soll_mm": info["bbox_mm"],
            }
        )
    return {
        "id": teil["id"],
        "rolle": teil["rolle"],
        "name": teil.get("name"),
        "anzahl": teil.get("anzahl", 1),
        "anzahl_ist_vorschlag": bool(teil.get("anzahl_ist_vorschlag")),
        "ok": not fehler and all(d.get("ok") for d in dateien),
        "fehler": fehler,
        "hinweise": hinweise,
        "dateien": dateien,
    }


def baue_alles(payload: dict) -> dict:
    out_dir = Path(payload["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    status = Path(payload["status_file"]) if payload.get("status_file") else None
    ergebnisse = []
    teile = payload["teile"]
    for index, teil in enumerate(teile, 1):
        if status:
            status.write_text(
                json.dumps(
                    {"status": "laeuft", "schritt": index, "gesamt": len(teile), "teil": teil.get("name") or teil["id"]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        try:
            ergebnisse.append(baue_teil(teil, out_dir))
        except Exception as exc:
            ergebnisse.append(
                {
                    "id": teil.get("id"),
                    "rolle": teil.get("rolle"),
                    "name": teil.get("name"),
                    "ok": False,
                    "fehler": [str(exc)],
                    "dateien": [],
                    "trace": traceback.format_exc(),
                }
            )
    ok = all(item.get("ok") for item in ergebnisse) and len(ergebnisse) == len(teile)
    return {"ok": ok, "teile": ergebnisse}


def pruefe_dateien(payload: dict) -> dict:
    """Lädt FCStd erneut und prüft STL-Meshes. Für einen zweiten Prozess."""
    import FreeCAD as App
    import Mesh

    bericht = []
    ok = True
    for eintrag in payload.get("dateien") or []:
        fcstd = Path(eintrag["fcstd"])
        stl = Path(eintrag["stl"])
        item = {"id": eintrag.get("id"), "fcstd": str(fcstd), "stl": str(stl)}
        if not fcstd.is_file() or not stl.is_file() or fcstd.stat().st_size < 200 or stl.stat().st_size < 200:
            item["ok"] = False
            item["fehler"] = "Datei fehlt oder ist leer."
            ok = False
            bericht.append(item)
            continue
        try:
            geladen = _neu_laden(App, fcstd)
            mesh = _mesh_info(Mesh, stl)
            item["fcstd_erneut_geladen"] = geladen
            item["mesh_freecad"] = mesh
            item["ok"] = bool(geladen.get("ok") and mesh.get("ok"))
            if not item["ok"]:
                ok = False
                item["fehler"] = geladen.get("fehler") or mesh.get("fehler") or "Prüfung fehlgeschlagen"
        except Exception as exc:
            item["ok"] = False
            item["fehler"] = str(exc)
            ok = False
        bericht.append(item)
    return {"ok": ok, "dateien": bericht}


def vorschau_netze(anfrage: dict) -> dict:
    """Dreiecksnetze der Körper für die 3D-Ansicht (Koordinaten wie gezeichnet, z nach oben)."""
    from sidecar.druckpruefung_geom import druckhinweise

    toleranz = float(anfrage.get("toleranz") or 0.12)
    netze = []
    hinweise: list[str] = []
    for teil in anfrage.get("teile") or []:
        shapes, _meta = _shapes_fuer(teil)
        for name, shape in shapes.items():
            punkte, dreiecke = shape.tessellate(toleranz)
            bb = _genaue_bbox(shape)
            netze.append(
                {
                    "teil": teil.get("id"),
                    "name": "%s%s" % (teil.get("name") or teil.get("id"), "" if len(shapes) == 1 else " (%s)" % name),
                    "punkte": [round(c, 3) for v in punkte for c in (v.x, v.y, v.z)],
                    "dreiecke": [i for d in dreiecke for i in d],
                    "bbox_mm": [round(bb.XMin, 2), round(bb.YMin, 2), round(bb.ZMin, 2), round(bb.XMax, 2), round(bb.YMax, 2), round(bb.ZMax, 2)],
                    "volumen_mm3": round(shape.Volume, 1),
                }
            )
            if teil.get("rolle") == "eigen":
                hinweise.extend("%s: %s" % (teil.get("name") or teil.get("id"), h) for h in druckhinweise(shape))
    return {"netze": netze, "hinweise": hinweise}


def behandle(anfrage: dict) -> dict:
    cmd = anfrage.get("cmd")
    try:
        if cmd == "ping":
            import FreeCAD as App
            from hausraster_const import SYSTEM_VERSION

            version = ".".join(str(x) for x in list(App.Version())[:3])
            return _antwort(True, {"freecad": version, "hausraster": SYSTEM_VERSION})
        if cmd == "build_all":
            return _antwort(True, baue_alles(anfrage))
        if cmd == "vorschau":
            return _antwort(True, vorschau_netze(anfrage))
        if cmd == "verify_files":
            return _antwort(True, pruefe_dateien(anfrage))
        if cmd == "kabel_passung":
            from sidecar.kabel_geom import passung_geometrisch

            return _antwort(True, passung_geometrisch(anfrage.get("a") or {}, anfrage.get("b") or {}))
        if cmd == "gehaeuse_passung":
            from sidecar.gehaeuse_geom import passung as gehaeuse_passung

            return _antwort(True, gehaeuse_passung(anfrage.get("parameter") or {}))
        return _antwort(False, fehler="Unbekannter Befehl: %s" % cmd)
    except Exception as exc:
        return _antwort(False, fehler="%s\n%s" % (exc, traceback.format_exc()))


def serve():
    _src_auf_pfad()
    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    portfile = os.environ.get("CADSTUDIO_PORTFILE")
    if portfile:
        Path(portfile).write_text(str(port), encoding="utf-8")
    print("CADSTUDIO_READY %d" % port, flush=True)
    conn, _addr = sock.accept()
    mit_datei = conn.makefile("rwb")
    try:
        while True:
            zeile = mit_datei.readline()
            if not zeile:
                break
            anfrage = json.loads(zeile.decode("utf-8"))
            if anfrage.get("cmd") == "shutdown":
                mit_datei.write(json.dumps(_antwort(True, {"bye": True})).encode("utf-8") + b"\n")
                mit_datei.flush()
                break
            antwort = behandle(anfrage)
            mit_datei.write(json.dumps(antwort, ensure_ascii=False).encode("utf-8") + b"\n")
            mit_datei.flush()
    finally:
        try:
            conn.close()
        except Exception:
            pass
        sock.close()


if __name__ == "__main__":
    serve()
