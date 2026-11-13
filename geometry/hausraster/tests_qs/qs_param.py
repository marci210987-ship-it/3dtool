# -*- coding: utf-8 -*-
"""Parametrische Belastungstests und Ungültig-Prüfungen."""
from __future__ import annotations

import math
from qs_common import (
    App, Part, _rec, _bbox_matches, _wall_probe, _count_pockets_slice,
    BAURAUM, VOL_EPS, almost, shape_info, REPORT,
)

from hausraster_const import default_params, pruefe_parameter, box_hoehe, FUSS_PROFIL_HOEHE
from hausraster_geom import make_plate_shape, make_box_shape, plate_outer_size, box_outer_size
from hausraster_phase3_plan import plane_stufenregal, plane_schraege, plane_halter


def _expect_raise_or_errors(fn, args=None, kwargs=None, label=""):
    kwargs = kwargs or {}
    args = args or []
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        msg = str(exc)
        _rec("Ungültige Parameter", label, "BESTANDEN" if msg.strip() else "FEHLERHAFT",
             details="Exception: " + msg)
        return True, msg
    if hasattr(result, "ungueltig") and result.ungueltig:
        hints = getattr(result, "hinweise", [])
        _rec("Ungültige Parameter", label, "BESTANDEN",
             details="Plan als ungültig gemeldet: " + "; ".join(hints) if hints else "ungueltig=True ohne Text")
        return True, hints
    if isinstance(result, (list, tuple)) and result and isinstance(result[0], str):
        _rec("Ungültige Parameter", label, "BESTANDEN", details="; ".join(result))
        return True, result
    _rec("Ungültige Parameter", label, "FEHLERHAFT",
         details="Keine verständliche Fehlermeldung, Ergebnistyp: %r" % (type(result),))
    return False, result


def test_param_plates():
    sets = [
        ("klein_1x1", dict(Einheiten_X=1, Einheiten_Y=1, Verbinder=1, Verriegelung=1)),
        ("standard_3x3", dict(Einheiten_X=3, Einheiten_Y=3)),
        ("gross_6x6", dict(Einheiten_X=6, Einheiten_Y=6)),
        ("ungerade_2x5_rand", dict(Einheiten_X=2, Einheiten_Y=5,
                                   Rand_X_links=3.7, Rand_X_rechts=5.3,
                                   Rand_Y_vorne=2.2, Rand_Y_hinten=4.8)),
        ("grenz_6x6_duenn", dict(Einheiten_X=6, Einheiten_Y=6,
                                 Bodenstaerke_Platte=0.6, Verbinder_Spiel=0.08)),
    ]
    vols = []
    for name, kw in sets:
        p = default_params(**kw)
        sh = make_plate_shape(p)
        sx, sy, sz = plate_outer_size(p)
        ok, info = _bbox_matches(sh, sx, sy, sz, label="Platte " + name)
        vols.append(info["volume_mm3"])
        nx, ny = int(p["Einheiten_X"]), int(p["Einheiten_Y"])
        raster = float(p["Raster_mm"])
        boden = float(p["Bodenstaerke_Platte"])
        cx0 = -sx / 2.0 + float(p["Rand_X_links"]) + 0.5 * raster
        cy0 = -sy / 2.0 + float(p["Rand_Y_vorne"]) + 0.5 * raster
        leer = voll = 0
        for i in range(nx):
            for j in range(ny):
                cx, cy = cx0 + i * raster, cy0 + j * raster
                probe = Part.makeBox(2, 2, 0.4, App.Vector(cx - 1, cy - 1, boden + 0.3))
                from qs_common import common_volume
                v = common_volume(sh, probe)
                if v < VOL_EPS:
                    leer += 1
                else:
                    voll += 1
        steg_ok = True
        if nx > 1:
            from qs_common import common_volume
            cx, cy = cx0 + 0.5 * raster, cy0
            probe = Part.makeBox(1, 1, 0.4, App.Vector(cx - 0.5, cy - 0.5, boden + 0.3))
            v = common_volume(sh, probe)
            steg_ok = v > VOL_EPS
        status = "BESTANDEN" if leer == nx * ny and voll == 0 and steg_ok else "FEHLERHAFT"
        _rec("Rasterabstand", "Platte " + name, status,
             messwerte={"zellen_luft": leer, "zellen_material": voll, "soll_zellen": nx * ny,
                        "steg_hat_material": steg_ok, "raster_mm": raster})
    if vols and max(vols) > min(vols) * 1.5:
        _rec("Parametrik-Volumen", "Plattenvolumen ändert sich mit der Größe", "BESTANDEN",
             messwerte={"volumina": vols})
    else:
        _rec("Parametrik-Volumen", "Plattenvolumen ändert sich mit der Größe", "FEHLERHAFT",
             messwerte={"volumina": vols})


def test_param_boxes():
    sets = [
        ("klein_1x1x1_ohne_lippe", dict(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=1, Stapellippe=0)),
        ("standard_2x2x3", dict(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3, Stapellippe=1)),
        ("gross_5x4x6", dict(Einheiten_X=5, Einheiten_Y=4, Einheiten_Z=6, Stapellippe=1)),
        ("ungerade_3x1x4_spiel", dict(Einheiten_X=3, Einheiten_Y=1, Einheiten_Z=4,
                                      Passungsspiel=0.15, Wandstaerke=1.6, Stapellippe=1)),
        ("grenz_6x6x12", dict(Einheiten_X=6, Einheiten_Y=6, Einheiten_Z=12, Stapellippe=1,
                              Wandstaerke=0.8, Bodenstaerke_Box=1.2)),
    ]
    prev_vol = None
    for name, kw in sets:
        p = default_params(**kw)
        errs = pruefe_parameter(p)
        if errs:
            _rec("Parametrik-Box", name + ": Parameterprüfung schlug fehl", "FEHLERHAFT", details="; ".join(errs))
            continue
        sh = make_box_shape(p)
        sx, sy, sz = box_outer_size(p)
        _bbox_matches(sh, sx, sy, sz, label="Box " + name)
        wand = float(p["Wandstaerke"])
        z_mid = float(p["Bodenstaerke_Box"]) + FUSS_PROFIL_HOEHE + 1.5
        probe_len = _wall_probe(sh, (sx / 2.0 - 0.05, 0.0, z_mid), (-1, 0, 0), max_dist=8.0)
        if probe_len is None:
            _rec("Wandsonde", "Box " + name, "EINGESCHRAENKT", details="Sonde konnte nicht ausgewertet werden")
        else:
            status = "BESTANDEN" if abs(probe_len - wand) <= 0.35 else "FEHLERHAFT"
            _rec("Wandsonde", "Box " + name, status, messwerte={"gemessen_mm": probe_len, "soll_mm": wand})
        vol = float(sh.Volume)
        if prev_vol is not None and abs(vol - prev_vol) < 1e-3:
            _rec("Parametrik-Volumen", "Box " + name + " Volumen unverändert", "FEHLERHAFT",
                 messwerte={"vol": vol, "prev": prev_vol})
        prev_vol = vol
        fits = sx <= BAURAUM[0] + 1e-6 and sy <= BAURAUM[1] + 1e-6 and sz <= BAURAUM[2] + 1e-6
        margin = min(BAURAUM[0] - sx, BAURAUM[1] - sy)
        st = "BESTANDEN" if fits else "FEHLERHAFT"
        if fits and margin < 8.0:
            st = "EINGESCHRAENKT"
        _rec("Bauraum", "Box " + name, st, messwerte={"size": [sx, sy, sz], "rand_mm": margin})


def test_param_faecher():
    sets = [
        ("1x1", 1, 1, 2, 2),
        ("2x2", 2, 2, 3, 3),
        ("3x2", 3, 2, 4, 3),
        ("4x3", 4, 3, 5, 4),
        ("grenz_6x5_in_6x6", 6, 5, 6, 6),
    ]
    for name, fx, fy, ex, ey in sets:
        p = default_params(Einheiten_X=ex, Einheiten_Y=ey, Einheiten_Z=4,
                           Fachanzahl_X=fx, Fachanzahl_Y=fy, Stapellippe=1)
        errs = pruefe_parameter(p)
        if errs:
            _rec("Fächer", name, "FEHLERHAFT", details="; ".join(errs))
            continue
        sh = make_box_shape(p)
        sx, sy, sz = box_outer_size(p)
        z = box_hoehe(int(p["Einheiten_Z"]), True) * 0.55
        n, extra = _count_pockets_slice(sh, z)
        if n is None:
            _rec("Fächer", name, "EINGESCHRAENKT", details=str(extra))
        else:
            soll = fx * fy
            st = "BESTANDEN" if n >= soll else "FEHLERHAFT"
            _rec("Fächer", name, st, messwerte={"gezählt": n, "soll": soll, "extra": extra,
                                                 "aussen": [sx, sy, sz]})


def test_invalid_params():
    e = pruefe_parameter(default_params(Wandstaerke=1.3))
    if e and any(("Wandstaerke" in x) or ("Vielfaches" in x) or ("0,4" in x) or ("0.4" in x) for x in e):
        _rec("Ungültige Parameter", "Wandstaerke 1,3 mm", "BESTANDEN", details="; ".join(e))
    else:
        _rec("Ungültige Parameter", "Wandstaerke 1,3 mm", "FEHLERHAFT", details="Keine verständliche Meldung: %r" % e)
    e = pruefe_parameter(default_params(Einheiten_X=2, Einheiten_Y=2, Fachanzahl_X=8, Fachanzahl_Y=8))
    if e:
        _rec("Ungültige Parameter", "8x8 Fächer in 2x2-Box", "BESTANDEN", details="; ".join(e))
    else:
        _rec("Ungültige Parameter", "8x8 Fächer in 2x2-Box", "FEHLERHAFT", details="nicht erkannt")
    e = pruefe_parameter(default_params(Einheiten_X=7, Einheiten_Y=1))
    if e:
        _rec("Ungültige Parameter", "7 Rastereinheiten", "BESTANDEN", details="; ".join(e))
    else:
        _rec("Ungültige Parameter", "7 Rastereinheiten", "FEHLERHAFT", details="nicht erkannt")
    e = pruefe_parameter(default_params(Raster_mm=40.0))
    if e:
        _rec("Ungültige Parameter", "Raster 40 mm", "BESTANDEN", details="; ".join(e))
    else:
        _rec("Ungültige Parameter", "Raster 40 mm", "FEHLERHAFT", details="nicht erkannt")
    _expect_raise_or_errors(make_plate_shape, [default_params(Einheiten_X=9)], label="Platte 9x1 Bauraum")
    _expect_raise_or_errors(make_box_shape, [default_params(Wandstaerke=1.3)], label="Box Wand 1,3 mm erzeugen")
    plan = plane_stufenregal({"Ebenenanzahl": 1, "Gesamtbreite": 180, "Gesamttiefe": 120})
    if getattr(plan, "ungueltig", False) and plan.hinweise:
        _rec("Ungültige Parameter", "Stufenregal Ebenenanzahl=1", "BESTANDEN", details="; ".join(plan.hinweise))
    else:
        _rec("Ungültige Parameter", "Stufenregal Ebenenanzahl=1", "FEHLERHAFT",
             details=str(getattr(plan, "hinweise", plan)))
    plan = plane_schraege({"Schubladenbreite": 200, "Schubladentiefe": 200, "Neigungswinkel": 50})
    if getattr(plan, "ungueltig", False) and plan.hinweise:
        _rec("Ungültige Parameter", "Schraege Winkel 50 Grad", "BESTANDEN", details="; ".join(plan.hinweise))
    else:
        _rec("Ungültige Parameter", "Schraege Winkel 50 Grad", "FEHLERHAFT",
             details=str(getattr(plan, "hinweise", plan)))
    plan = plane_halter({"Glasdurchmesser": 5})
    if getattr(plan, "ungueltig", False) and plan.hinweise:
        _rec("Ungültige Parameter", "Halter Glas 5 mm", "BESTANDEN", details="; ".join(plan.hinweise))
    else:
        _rec("Ungültige Parameter", "Halter Glas 5 mm", "FEHLERHAFT",
             details=str(getattr(plan, "hinweise", plan)))
