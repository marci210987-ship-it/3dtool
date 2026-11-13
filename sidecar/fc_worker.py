# -*- coding: utf-8 -*-
"""FreeCAD-Worker. Läuft nur innerhalb von FreeCADCmd.

Protokoll: eine JSON-Zeile je Anfrage über einen lokalen TCP-Socket.
FreeCADCmd liest das Startskript von stdin; der Socket bleibt danach frei.
"""

from __future__ import annotations

import json
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


def _eigen_shape(params: dict):
    """Extrudiert die gezeichneten Formen. Löcher schneiden ab der Bodenhöhe."""
    import FreeCAD as App
    import Part

    hoehe = float(params["Hoehe"])
    boden = float(params.get("Boden") or 0.0)
    plus = None
    minus = []
    for form in params["Formen"]:
        typ = form["typ"]
        if typ == "rechteck":
            x, y, b, t = float(form["x"]), float(form["y"]), float(form["b"]), float(form["t"])
            draht = _rechteck_draht(x, y, b, t, float(form.get("radius") or 0.0))
        elif typ == "kreis":
            draht = Part.Wire(Part.makeCircle(float(form["r"]), App.Vector(float(form["x"]), float(form["y"]), 0), App.Vector(0, 0, 1)))
        else:
            pts = [App.Vector(float(px), float(py), 0) for px, py in form["punkte"]]
            draht = Part.makePolygon(pts + [pts[0]])
        flaeche = Part.Face(draht)
        if form.get("loch"):
            # Loch: Standard ab Boden bis über die Oberkante, mit z_mm/h_mm auch als Tasche an beliebiger Höhe
            z0 = float(form["z_mm"]) if form.get("z_mm") not in (None, "") else boden
            h0 = float(form["h_mm"]) if form.get("h_mm") not in (None, "") else hoehe - z0 + 1.0
            koerper = flaeche.extrude(App.Vector(0, 0, h0))
            koerper.translate(App.Vector(0, 0, z0))
            minus.append(koerper)
        else:
            z0 = float(form.get("z_mm") or 0.0)
            h0 = float(form["h_mm"]) if form.get("h_mm") not in (None, "") else hoehe - z0
            koerper = flaeche.extrude(App.Vector(0, 0, h0))
            koerper.translate(App.Vector(0, 0, z0))
            plus = koerper if plus is None else plus.fuse(koerper)
    if plus is None:
        raise ValueError("Keine Form, die Material hinzufügt.")
    for loch in minus:
        plus = plus.cut(loch)
    plus = plus.removeSplitter()
    plus = _kante_bearbeiten(plus, True, int(params.get("KanteObenArt") or 0), float(params.get("KanteObenMm") or 0.0), "Obere Kante")
    plus = _kante_bearbeiten(plus, False, 1, float(params.get("KanteUntenMm") or 0.0), "Untere Fase")
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
        if haupt and teil["rolle"] in ("grundplatte", "box", "phase4", "eigen"):
            soll_fehler = _passt_soll(info["bbox_mm"], soll)
        haupt = False
        if bauraum or soll_fehler:
            fehler.append(bauraum or soll_fehler)
            dateien.append({"id": datei_id, "name": name, "ok": False, "solid": info, "fehler": bauraum or soll_fehler})
            continue
        export_stl(shape, stl)
        params = dict(teil["params"])
        formen_text = ""
        if teil["rolle"] == "eigen":
            # Das Tabellenblatt kennt nur Zahlen; die Formen stehen im Lesen-Text.
            formen_text = "\nFormen (mm, Draufsicht): " + json.dumps(params.pop("Formen", []), ensure_ascii=False)
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
        if cmd == "verify_files":
            return _antwort(True, pruefe_dateien(anfrage))
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
