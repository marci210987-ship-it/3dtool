"""Gerichtete Skizzenbedingungen für Rechtecke und Kreise, ohne FreeCAD."""
from copy import deepcopy
from math import isfinite


def anwenden(formen, regeln):
    if not regeln:
        return formen
    formen = deepcopy(formen)
    ids = {}
    for f in formen:
        if f.get("fid"):
            if f["fid"] in ids:
                raise ValueError("Formkennungen sind doppelt vorhanden.")
            ids[f["fid"]] = f
    belegt = set()
    for r in regeln:
        if r.get("art") not in ("mittig", "abstand", "gleich", "parallel"):
            raise ValueError("Unbekannte Skizzenbedingung.")
        if r.get("quelle") not in ids or r.get("ziel") not in ids:
            raise ValueError("Bezugsform fehlt.")
        if r["quelle"] == r["ziel"]:
            raise ValueError("Eine Form kann nicht ihr eigener Bezug sein.")
        key = (r["ziel"], "lage" if r["art"] in ("mittig", "abstand") else r["art"])
        if key in belegt:
            raise ValueError("Mehrere Bedingungen für dieselbe Eigenschaft.")
        belegt.add(key)
    fertig, besucht = set(), set()

    def mitte(f):
        if f["typ"] == "kreis":
            return float(f["x"]), float(f["y"])
        if f["typ"] == "rechteck":
            return float(f["x"]) + float(f["b"]) / 2, float(f["y"]) + float(f["t"]) / 2
        raise ValueError("Bedingungen unterstützen Rechtecke und Kreise.")

    def loese(fid):
        if fid in fertig:
            return
        if fid in besucht:
            raise ValueError("Kreisbezug in Skizzenbedingungen.")
        besucht.add(fid)
        z = ids[fid]
        for r in sorted((r for r in regeln if r["ziel"] == fid), key=lambda r: r["art"] in ("mittig", "abstand")):
            loese(r["quelle"])
            q = ids[r["quelle"]]
            mitte(q), mitte(z)
            if r["art"] == "gleich":
                if q["typ"] != z["typ"]:
                    raise ValueError("Gleiche Größe benötigt gleiche Formtypen.")
                if z["typ"] == "kreis":
                    z["r"] = q["r"]
                else:
                    z["b"], z["t"] = q["b"], q["t"]
                    if z.get("radius"):
                        z["radius"] = min(z["radius"], z["b"] / 2, z["t"] / 2)
            elif r["art"] == "parallel":
                if q["typ"] != "rechteck" or z["typ"] != "rechteck":
                    raise ValueError("Parallel benötigt zwei Rechtecke.")
                z["winkel"] = q.get("winkel") or 0
            else:
                dx, dy = (float(r.get("dx", 0)), float(r.get("dy", 0))) if r["art"] == "abstand" else (0, 0)
                if not isfinite(dx) or not isfinite(dy):
                    raise ValueError("Abstände müssen endliche Zahlen sein.")
                x, y = mitte(q)
                z["x"] = x + dx - (float(z["b"]) / 2 if z["typ"] == "rechteck" else 0)
                z["y"] = y + dy - (float(z["t"]) / 2 if z["typ"] == "rechteck" else 0)
        besucht.remove(fid)
        fertig.add(fid)

    for fid in ids:
        loese(fid)
    return formen
