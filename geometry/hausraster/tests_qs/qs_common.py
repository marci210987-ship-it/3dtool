# -*- coding: utf-8 -*-
"""Gemeinsame Hilfen der QS-Testsuite. Wird unter FreeCADCmd ausgeführt."""
from __future__ import annotations

import datetime
import hashlib
import json
import math
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart
import Part

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if not (ROOT / "01_rastersystem").exists():
    for cand in (Path("/workspace/ordnungssystem"), Path.cwd(), Path.cwd().parent):
        if (cand / "01_rastersystem").exists():
            ROOT = cand
            break

OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
TMP_STL = OUT / "_tmp_stl"
TMP_STL.mkdir(exist_ok=True)
GF_DIR = Path("/tmp/gf_ref")
BAURAUM = (256.0, 256.0, 256.0)
VOL_EPS = 1e-2
LEN_EPS = 0.05
COLLISION_EPS = 0.5

FREECAD_VERSION = getattr(App, "VersionString", None) or ".".join(str(x) for x in App.Version()[:4])

REPORT = {
    "titel": "QS-Audit Hausraster 0.2 (unabhängig)",
    "freecad_version": FREECAD_VERSION,
    "projektwurzel": str(ROOT),
    "gestartet_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "zeitzone_nutzer": "Europe/Berlin",
    "tests": [],
    "modelle": {},
    "fehler": [],
    "hinweise": [],
    "zusammenfassung": {},
}


def now_berlin():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1))).strftime(
        "%Y-%m-%d %H:%M:%S Europe/Berlin"
    )


def _rec(bereich, name, status, details=None, messwerte=None, modell=None):
    rec = {
        "bereich": bereich,
        "name": name,
        "status": status,
        "details": details or "",
        "messwerte": messwerte or {},
        "modell": modell,
        "zeit": now_berlin(),
    }
    REPORT["tests"].append(rec)
    return rec


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def shape_info(sh):
    if sh is None or sh.isNull():
        return {"null": True}
    bb = sh.BoundBox
    solids = list(sh.Solids) if sh.Solids else ([] if sh.ShapeType != "Solid" else [sh])
    vol = 0.0
    try:
        vol = float(sh.Volume)
    except Exception:
        vol = sum(float(s.Volume) for s in solids) if solids else 0.0
    closed = all(s.isClosed() for s in solids) if solids else False
    return {
        "null": False,
        "valid": bool(sh.isValid()),
        "closed": closed,
        "solids": len(solids),
        "faces": len(sh.Faces),
        "edges": len(sh.Edges),
        "volume_mm3": vol,
        "bbox": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
        "size": [bb.XLength, bb.YLength, bb.ZLength],
        "zmin": bb.ZMin,
        "zmax": bb.ZMax,
    }


def common_volume(a, b):
    try:
        c = a.common(b)
        if c is None or c.isNull():
            return 0.0
        return abs(float(c.Volume) or 0.0)
    except Exception:
        return float("nan")


def almost(a, b, tol=LEN_EPS):
    return abs(float(a) - float(b)) <= tol


def mesh_quality(mesh):
    info = {
        "points": mesh.CountPoints,
        "facets": mesh.CountFacets,
        "solid": None,
        "nonmanifold": None,
        "invalid_points": None,
        "volume_mm3": None,
        "size": None,
    }
    try:
        info["solid"] = bool(mesh.isSolid())
    except Exception as exc:
        info["solid_error"] = str(exc)
    try:
        info["nonmanifold"] = bool(mesh.hasNonManifolds())
    except Exception as exc:
        info["nonmanifold_error"] = str(exc)
    try:
        info["invalid_points"] = bool(mesh.hasInvalidPoints())
    except Exception:
        pass
    try:
        info["volume_mm3"] = float(mesh.Volume)
    except Exception:
        try:
            info["volume_mm3"] = float(mesh.getVolume())
        except Exception:
            pass
    try:
        bb = mesh.BoundBox
        info["size"] = [bb.XLength, bb.YLength, bb.ZLength]
    except Exception:
        pass
    return info


def export_and_reimport(shape, tag):
    path = TMP_STL / (tag + ".stl")
    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=0.08, AngularDeflection=0.174, Relative=False
    )
    mesh.write(str(path))
    mesh2 = Mesh.Mesh()
    mesh2.read(str(path))
    q = mesh_quality(mesh2)
    q["path"] = str(path)
    q["cad_volume_mm3"] = float(shape.Volume) if shape.Volume else 0.0
    if q["volume_mm3"] is not None and q["cad_volume_mm3"]:
        q["volume_rel_diff"] = abs(q["volume_mm3"] - q["cad_volume_mm3"]) / max(q["cad_volume_mm3"], 1e-6)
    else:
        q["volume_rel_diff"] = None
    return q


def object_states(doc):
    rows = []
    for obj in doc.Objects:
        st = list(getattr(obj, "State", []) or [])
        rows.append({"name": obj.Name, "type": obj.TypeId, "state": st, "label": obj.Label})
    return rows


def expressions_on_shapes(doc):
    found = []
    for obj in doc.Objects:
        if not hasattr(obj, "Shape"):
            continue
        ee = getattr(obj, "ExpressionEngine", None)
        if not ee:
            continue
        for item in ee:
            found.append({"objekt": obj.Name, "expression": list(item) if not isinstance(item, str) else item})
    return found


def load_existing_stl_quality(path: Path):
    mesh = Mesh.Mesh()
    mesh.read(str(path))
    q = mesh_quality(mesh)
    q["path"] = str(path)
    q["bytes"] = path.stat().st_size
    return q


def write_partial():
    REPORT["geschrieben"] = now_berlin()
    (OUT / "report_partial.json").write_text(
        json.dumps(REPORT, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )


def _bbox_matches(shape, sx, sy, sz, tol=0.15, label="", ignore_z=False):
    bb = shape.BoundBox
    ok_x = almost(bb.XLength, sx, tol)
    ok_y = almost(bb.YLength, sy, tol)
    ok_z = True if ignore_z else almost(bb.ZLength, sz, tol)
    status = "BESTANDEN" if (ok_x and ok_y and ok_z) else "FEHLERHAFT"
    _rec("Parametrik-Maß", label, status,
         messwerte={
             "soll": [sx, sy, sz],
             "ist": [bb.XLength, bb.YLength, bb.ZLength],
             "ursprung_min": [bb.XMin, bb.YMin, bb.ZMin],
             "volumen_mm3": float(shape.Volume),
             "valid": bool(shape.isValid()),
             "closed": all(s.isClosed() for s in shape.Solids),
         })
    return status == "BESTANDEN", shape_info(shape)


def _wall_probe(shape, p0, direction, max_dist=20.0):
    try:
        d = App.Vector(*direction)
        if d.Length < 1e-9:
            return None
        d.normalize()
        cyl = Part.makeCylinder(0.05, max_dist, App.Vector(*p0), d)
        c = shape.common(cyl)
        if c is None or c.isNull() or not c.Solids:
            return 0.0
        bb = c.BoundBox
        ax = abs(d.x), abs(d.y), abs(d.z)
        if ax[0] >= ax[1] and ax[0] >= ax[2]:
            return float(bb.XLength)
        if ax[1] >= ax[2]:
            return float(bb.YLength)
        return float(bb.ZLength)
    except Exception:
        return None


def _count_pockets_slice(shape, z, expect_min_area=20.0):
    try:
        bb = shape.BoundBox
        slab = Part.makeBox(bb.XLength + 20, bb.YLength + 20, 0.05,
                            App.Vector(bb.XMin - 10, bb.YMin - 10, z))
        sec = shape.common(slab)
        wires = 0
        if sec and not sec.isNull():
            for f in sec.Faces:
                if abs(f.Area) < expect_min_area:
                    continue
                if len(f.Wires) > 1:
                    wires += len(f.Wires) - 1
                else:
                    wires += 1
        return wires, float(sec.Volume) if sec and not sec.isNull() else 0.0
    except Exception as exc:
        return None, str(exc)


def _place(shape, x, y, z, rz=0):
    s = shape.copy()
    if rz:
        s.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), rz)
    s.translate(App.Vector(x, y, z))
    return s
