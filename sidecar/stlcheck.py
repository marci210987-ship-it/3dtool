# -*- coding: utf-8 -*-
"""STL-Prüfung ohne CAD-Kernel.

Geschlossenes Dreiecksnetz: jede Kante kommt in genau zwei Facetten vor und
in entgegengesetzter Richtung (konsistente Orientierung). Zusätzlich
Bounding-Box gegen das Sollmass.
"""

from __future__ import annotations

import struct
from pathlib import Path


def _read_triangles(path: Path) -> list[tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]]:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("STL ist zu klein.")
    count = struct.unpack_from("<I", data, 80)[0]
    binary_len = 84 + count * 50
    # Binär, wenn die Dateigröße zur Dreieckszahl passt. Manche Binärdateien
    # beginnen trotzdem mit den Buchstaben "solid".
    if binary_len == len(data) or (binary_len < len(data) and abs(binary_len - len(data)) < 100 and count > 0):
        tris = []
        offset = 84
        for _ in range(count):
            nums = struct.unpack_from("<12fH", data, offset)
            a = (nums[3], nums[4], nums[5])
            b = (nums[6], nums[7], nums[8])
            c = (nums[9], nums[10], nums[11])
            tris.append((a, b, c))
            offset += 50
        return tris
    text = data.decode("utf-8", errors="replace")
    if "facet" not in text.lower():
        raise ValueError("STL ist weder gültiges Binär- noch ASCII-Format.")
    tris = []
    verts: list[tuple[float, float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.lower().startswith("vertex"):
            parts = line.split()
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            if len(verts) == 3:
                tris.append((verts[0], verts[1], verts[2]))
                verts = []
    if not tris:
        raise ValueError("ASCII-STL enthält keine Dreiecke.")
    return tris


def _key(v: tuple[float, float, float], scale: float = 10000.0) -> tuple[int, int, int]:
    return (int(round(v[0] * scale)), int(round(v[1] * scale)), int(round(v[2] * scale)))


def pruefe_stl(
    path: str | Path,
    soll_groesse: tuple[float, float, float] | None = None,
    tol_mm: float = 0.75,
    min_bytes: int = 200,
) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "fehler": "Datei fehlt: %s" % path}
    size = path.stat().st_size
    if size < min_bytes:
        return {"ok": False, "fehler": "Datei ist leer oder zu klein (%d Byte)." % size, "bytes": size}
    try:
        tris = _read_triangles(path)
    except Exception as exc:
        return {"ok": False, "fehler": "STL nicht lesbar: %s" % exc, "bytes": size}
    if len(tris) < 4:
        return {"ok": False, "fehler": "Zu wenige Dreiecke (%d)." % len(tris), "bytes": size}

    kanten: dict[tuple, int] = {}
    richtung: dict[tuple, int] = {}
    xmin = ymin = zmin = 1e99
    xmax = ymax = zmax = -1e99
    volumen = 0.0
    for a, b, c in tris:
        for v in (a, b, c):
            xmin, ymin, zmin = min(xmin, v[0]), min(ymin, v[1]), min(zmin, v[2])
            xmax, ymax, zmax = max(xmax, v[0]), max(ymax, v[1]), max(zmax, v[2])
        volumen += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + b[0] * (c[1] * a[2] - c[2] * a[1])
            + c[0] * (a[1] * b[2] - a[2] * b[1])
        )
        for u, w in ((a, b), (b, c), (c, a)):
            ku, kw = _key(u), _key(w)
            kante = (ku, kw) if ku <= kw else (kw, ku)
            kanten[kante] = kanten.get(kante, 0) + 1
            richtung[(ku, kw)] = richtung.get((ku, kw), 0) + 1
    volumen = abs(volumen) / 6.0
    offen = sum(1 for n in kanten.values() if n != 2)
    mehrfach = sum(1 for n in kanten.values() if n > 2)
    inkonsistent = 0
    for (u, w), n in list(richtung.items()):
        if u >= w:
            continue
        hin = n
        her = richtung.get((w, u), 0)
        if hin != 1 or her != 1:
            # Kante, die nicht genau einmal je Richtung vorkommt
            if kanten.get((u, w), 0) == 2:
                inkonsistent += 1
    bbox = [xmax - xmin, ymax - ymin, zmax - zmin]
    wasserdicht = offen == 0 and mehrfach == 0
    orientierung_ok = inkonsistent == 0
    mannigfaltig = wasserdicht and orientierung_ok
    groesse_ok = True
    groesse_fehler = ""
    if soll_groesse is not None:
        diffs = [abs(bbox[i] - float(soll_groesse[i])) for i in range(3)]
        if any(d > tol_mm for d in diffs):
            groesse_ok = False
            groesse_fehler = (
                "Bounding-Box %.3f × %.3f × %.3f mm weicht vom Soll "
                "%.3f × %.3f × %.3f mm ab (Toleranz %.2f mm)."
                % (bbox[0], bbox[1], bbox[2], soll_groesse[0], soll_groesse[1], soll_groesse[2], tol_mm)
            )
    if zmin < -0.2 or zmin > 0.6:
        groesse_ok = False
        groesse_fehler = (groesse_fehler + " " if groesse_fehler else "") + (
            "ZMin %.3f mm ist nicht plausibel für eine druckfertige Lage bei Z=0." % zmin
        )
    ok = mannigfaltig and groesse_ok and volumen > 1.0
    fehler = []
    if not wasserdicht:
        fehler.append("Netz ist nicht wasserdicht/mannigfaltig (offene oder mehrfache Kanten: %d)." % (offen + mehrfach))
    if not orientierung_ok:
        fehler.append("Dreiecksorientierung ist nicht konsistent (%d Kanten)." % inkonsistent)
    if not groesse_ok and groesse_fehler:
        fehler.append(groesse_fehler)
    if volumen <= 1.0:
        fehler.append("Volumen ist nicht plausibel (%.3f mm³)." % volumen)
    return {
        "ok": ok,
        "bytes": size,
        "dreiecke": len(tris),
        "wasserdicht": wasserdicht,
        "orientierung_ok": orientierung_ok,
        "mannigfaltig": mannigfaltig,
        "offene_oder_mehrfachkanten": offen + mehrfach,
        "volumen_mm3": volumen,
        "bbox_mm": [round(v, 4) for v in bbox],
        "zmin": zmin,
        "groesse_ok": groesse_ok,
        "fehler": " ".join(fehler),
    }
