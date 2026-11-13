# -*- coding: utf-8 -*-
"""Besteck- und Gewuerztests."""
from __future__ import annotations

import traceback

import FreeCAD as App
import Part

from qs_common import REPORT, _rec, shape_info, almost, common_volume
from hausraster_phase3_geom import besteck_teile, stufen_teile, schraege_teile, halter_teile, default_besteck_params
from hausraster_phase3_plan import plane_besteck, plane_stufenregal, plane_schraege, plane_halter
from hausraster_phase3_schale import stufen_schale_teile, schraege_schale_teile


def test_besteck():
    faelle = [
        ("350x300_standard", dict(Schubladenbreite=350, Schubladentiefe=300, Schubladenspiel=1.0)),
        ("450x400_standard", dict(Schubladenbreite=450, Schubladentiefe=400, Schubladenspiel=1.0)),
        ("500x450_standard", dict(Schubladenbreite=500, Schubladentiefe=450, Schubladenspiel=1.0)),
        ("450x350_referenz", dict(Schubladenbreite=450, Schubladentiefe=350, Schubladenspiel=1.0)),
        ("500x400_referenz", dict(Schubladenbreite=500, Schubladentiefe=400, Schubladenspiel=1.0)),
        ("350x300_mehr_faecher", dict(Schubladenbreite=350, Schubladentiefe=300, Schubladenspiel=1.0,
                                       Fachanzahl_Messer=2, Fachanzahl_Gabeln=2, Fachanzahl_Essloeffel=2,
                                       Fachanzahl_Teeloeffel=2)),
    ]
    for name, kw in faelle:
        p = default_besteck_params(**kw)
        try:
            plan = plane_besteck(p)
        except Exception as exc:
            _rec("Besteck-Plan", name, "FEHLERHAFT", details=str(exc))
            continue
        if getattr(plan, "ungueltig", False):
            _rec("Besteck-Plan", name, "FEHLERHAFT", details="; ".join(plan.hinweise))
            continue
        spiel = float(p.get("Schubladenspiel", 1.0))
        soll_w = float(kw["Schubladenbreite"]) - 2 * spiel
        soll_d = float(kw["Schubladentiefe"]) - 2 * spiel
        ist_w = getattr(plan, "breite", None) or getattr(plan, "nutzbreite", None)
        ist_d = getattr(plan, "tiefe", None) or getattr(plan, "nutztiefe", None)
        if ist_w is None and hasattr(plan, "parameter"):
            ist_w = plan.parameter.get("Nutzbreite") or plan.parameter.get("Breite")
            ist_d = plan.parameter.get("Nutztiefe") or plan.parameter.get("Tiefe")
        for cand_w, cand_d in (
            (getattr(plan, "nutz_x", None), getattr(plan, "nutz_y", None)),
            (getattr(plan, "width", None), getattr(plan, "depth", None)),
        ):
            if ist_w is None and cand_w is not None:
                ist_w, ist_d = cand_w, cand_d
        ok_mass = ist_w is not None and almost(ist_w, soll_w, 0.2) and almost(ist_d, soll_d, 0.2)
        _rec("Besteck-Mass", name, "BESTANDEN" if ok_mass else "FEHLERHAFT",
             messwerte={"soll_nutz": [soll_w, soll_d], "ist": [ist_w, ist_d],
                        "felder": sorted(getattr(plan, "__dict__", {}).keys())})
        try:
            _plan, shapes = besteck_teile(p)
        except Exception:
            _rec("Besteck-Geometrie", name, "FEHLERHAFT", details=traceback.format_exc())
            continue
        segs = {k: v for k, v in shapes.items() if "Segment" in k and "verbinder" not in k.lower()}
        verb = {k: v for k, v in shapes.items() if "verbinder" in k.lower() or "Verbinder" in k or "Clip" in k}
        wall_ok = True
        bauraum_ok = True
        seg_infos = {}
        for k, sh in shapes.items():
            info = shape_info(sh)
            seg_infos[k] = info
            if not info.get("valid") or not info.get("closed") or info.get("volume_mm3", 0) <= 0:
                wall_ok = False
            sx, sy, sz = info["size"]
            if max(sx, sy, sz) > 256 + 0.2:
                bauraum_ok = False
        _rec("Besteck-Koerper", name, "BESTANDEN" if wall_ok and bauraum_ok else "FEHLERHAFT",
             messwerte={"teile": seg_infos, "n_segmente": len(segs), "n_verbinder": len(verb),
                        "bauraum_ok": bauraum_ok})
        if len(segs) > 1 and not verb:
            _rec("Besteck-Segmentierung", name, "EINGESCHRAENKT",
                 details="Mehrere Segmente, aber kein Verbinderkoerper im shapes-Dict.")
        elif len(segs) > 1:
            _rec("Besteck-Segmentierung", name, "BESTANDEN",
                 messwerte={"segmente": list(segs), "verbinder": list(verb)})
        else:
            _rec("Besteck-Segmentierung", name, "BESTANDEN",
                 details="einteilig, keine Teilung noetig", messwerte={"segmente": list(segs)})


def _pruefe_teile(label, shapes, soll_bbox=None, tol=1.2):
    ok = True
    infos = {}
    union = None
    for k, sh in shapes.items():
        info = shape_info(sh)
        infos[k] = info
        if not info.get("valid") or not info.get("closed") or info.get("volume_mm3", 0) <= 0:
            ok = False
            _rec("Gewuerz-Koerper", label + "/" + k, "FEHLERHAFT", messwerte=info)
        else:
            _rec("Gewuerz-Koerper", label + "/" + k, "BESTANDEN", messwerte=info)
        if "Segment" in k or k in ("Koerper", "Halter", "Regal", "Schraege"):
            union = sh if union is None else union.fuse(sh)
    if soll_bbox and union is not None:
        bb = union.BoundBox
        sx, sy, sz = soll_bbox
        match = (almost(bb.XLength, sx, tol) or bb.XLength < sx + tol) and almost(bb.YLength, sy, max(tol, sy * 0.05))
        nseg = sum(1 for k in shapes if "Segment" in k)
        if nseg > 1:
            _rec("Gewuerz-Mass", label, "EINGESCHRAENKT",
                 details="Mehrere Segmente werden jeweils lokal bei (0,0) erzeugt; eine zusammengesetzte BBox ohne Verschieben ist nicht das Gesamtmass.",
                 messwerte={"union_size": [bb.XLength, bb.YLength, bb.ZLength], "soll": soll_bbox, "nseg": nseg})
        else:
            _rec("Gewuerz-Mass", label, "BESTANDEN" if match else "FEHLERHAFT",
                 messwerte={"ist": [bb.XLength, bb.YLength, bb.ZLength], "soll": soll_bbox})
            if not match:
                ok = False
                REPORT["fehler"].append({
                    "id": "GEWUERZ_BBOX", "modell": label,
                    "ist": [bb.XLength, bb.YLength, bb.ZLength], "soll": soll_bbox, "schwere": "mittel",
                })
    return ok, infos


def test_gewuerz():
    stufen_saetze = [
        ("stufen_klein_180", dict(Gesamtbreite=180, Gesamttiefe=120, Ebenenanzahl=3, Glasdurchmesser=45)),
        ("stufen_standard_250", dict(Gesamtbreite=250, Gesamttiefe=150, Ebenenanzahl=3, Glasdurchmesser=55)),
        ("stufen_gross_400", dict(Gesamtbreite=400, Gesamttiefe=180, Ebenenanzahl=4, Glasdurchmesser=55, Stufenhoehe=40)),
        ("stufen_ungerade", dict(Gesamtbreite=233, Gesamttiefe=137, Ebenenanzahl=3, Glasdurchmesser=48, Glasabstand=5)),
        ("stufen_grenz_2eben", dict(Gesamtbreite=160, Gesamttiefe=90, Ebenenanzahl=2, Glasdurchmesser=40, Stufenhoehe=25)),
    ]
    for name, kw in stufen_saetze:
        plan = plane_stufenregal(kw)
        if plan.ungueltig:
            _rec("Gewuerz-Plan", name, "FEHLERHAFT", details="; ".join(plan.hinweise))
            continue
        soll = (plan.breite, plan.tiefe, plan.hoehe)
        try:
            _p, shapes = stufen_teile(kw)
            _pruefe_teile(name, shapes, soll)
        except Exception:
            _rec("Gewuerz-Geometrie", name, "FEHLERHAFT", details=traceback.format_exc())
        try:
            _p, sh_s = stufen_schale_teile(kw)
            _pruefe_teile(name + "_Schale", sh_s, soll)
        except Exception:
            _rec("Gewuerz-Geometrie", name + "_Schale", "FEHLERHAFT", details=traceback.format_exc())

    schraege_saetze = [
        ("schraege_200x200_15", dict(Schubladenbreite=200, Schubladentiefe=200, Neigungswinkel=15, Glasdurchmesser=55, Glaslange=110)),
        ("schraege_300x250_15", dict(Schubladenbreite=300, Schubladentiefe=250, Neigungswinkel=15, Glasdurchmesser=55, Glaslange=110)),
        ("schraege_450x350_15", dict(Schubladenbreite=450, Schubladentiefe=350, Neigungswinkel=15, Glasdurchmesser=55, Glaslange=110)),
        ("schraege_200x200_winkel10", dict(Schubladenbreite=200, Schubladentiefe=200, Neigungswinkel=10, Glasdurchmesser=45, Glaslange=90)),
        ("schraege_280x210_winkel22", dict(Schubladenbreite=280, Schubladentiefe=210, Neigungswinkel=22, Glasdurchmesser=70, Glaslange=130)),
    ]
    for name, kw in schraege_saetze:
        plan = plane_schraege(kw)
        if plan.ungueltig:
            _rec("Gewuerz-Plan", name, "FEHLERHAFT", details="; ".join(plan.hinweise))
            continue
        soll = (plan.breite, plan.tiefe, plan.hoehe)
        try:
            _p, shapes = schraege_teile(kw)
            ok, infos = _pruefe_teile(name, shapes, soll, tol=2.0)
            if "450" in name:
                _rec("Gewuerz-Mass", "Explizit: Schraege 450x350 Soll-gegen-Ist", "HINWEIS",
                     messwerte={"soll": soll, "infos": infos, "plan_hinweise": plan.hinweise})
        except Exception:
            _rec("Gewuerz-Geometrie", name, "FEHLERHAFT", details=traceback.format_exc())
        try:
            _p, sh_s = schraege_schale_teile(kw)
            _pruefe_teile(name + "_Schale", sh_s, soll, tol=2.0)
        except Exception:
            _rec("Gewuerz-Geometrie", name + "_Schale", "FEHLERHAFT", details=traceback.format_exc())

    for d in (45, 55, 70, 38, 100):
        name = "halter_D%d" % d
        plan = plane_halter({"Glasdurchmesser": d})
        if plan.ungueltig:
            _rec("Gewuerz-Plan", name, "FEHLERHAFT" if d >= 20 else "BESTANDEN", details="; ".join(plan.hinweise))
            continue
        try:
            _p, shapes = halter_teile({"Glasdurchmesser": d})
            soll = (plan.breite, plan.tiefe, plan.hoehe)
            _pruefe_teile(name, shapes, soll, tol=0.4)
            body = None
            for k, sh in shapes.items():
                if "Halter" in k or k == "Halter":
                    body = sh
                    break
            if body is None and shapes:
                body = list(shapes.values())[0]
            innen = float(plan.parameter["Innen_D"])
            hoehe = plan.hoehe
            air = Part.makeCylinder(innen / 2.0 - 0.2, max(2.0, hoehe - 4.0), App.Vector(0, 0, 2.0))
            bb = body.BoundBox
            air.translate(App.Vector((bb.XMin + bb.XMax) / 2.0, (bb.YMin + bb.YMax) / 2.0, 0))
            v_air = common_volume(body, air)
            _rec("Gewuerz-Oeffnung", name, "BESTANDEN" if v_air < 50 else "FEHLERHAFT",
                 messwerte={"common_innen_mm3": v_air, "innen_d": innen,
                            "aussen": [bb.XLength, bb.YLength, bb.ZLength]})
        except Exception:
            _rec("Gewuerz-Geometrie", name, "FEHLERHAFT", details=traceback.format_exc())

    try:
        _, voll = stufen_teile(dict(Gesamtbreite=180, Gesamttiefe=120, Ebenenanzahl=3, Glasdurchmesser=55))
        _, schale = stufen_schale_teile(dict(Gesamtbreite=180, Gesamttiefe=120, Ebenenanzahl=3, Glasdurchmesser=55))
        vv = sum(float(sh.Volume) for k, sh in voll.items() if "verbinder" not in k.lower())
        vs = sum(float(sh.Volume) for k, sh in schale.items() if "verbinder" not in k.lower())
        ratio = vs / vv if vv else None
        st = "BESTANDEN" if ratio is not None and ratio < 0.40 else "FEHLERHAFT"
        _rec("Gewuerz-Schale", "Volumen Schale/Vollkoerper Stufen 180x120", st,
             messwerte={"voll_mm3": vv, "schale_mm3": vs, "ratio": ratio})
    except Exception:
        _rec("Gewuerz-Schale", "Volumenvergleich", "FEHLERHAFT", details=traceback.format_exc())
