# -*- coding: utf-8 -*-
"""Eigene Teile: einfache 2D-Formen, die zu einem Körper extrudiert werden.

Ein Eigenteil besteht aus Formen in Millimetern (Draufsicht, Ursprung links
vorne). Normale Formen fügen Material hinzu, Formen mit ``loch`` schneiden es
wieder weg. Der Körper wird in FreeCAD erzeugt (siehe fc_worker, Rolle
``eigen``). Dieses Modul enthält nur reine Datenlogik ohne FreeCAD.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

from sidecar.paths import HAUSRASTER_SRC  # noqa: F401  (stellt sys.path sicher)

MIN_MASS_MM = 0.4
MAX_FORMEN = 200
TYPEN = ("rechteck", "kreis", "polygon")


@dataclass
class Eigenteil:
    id: str
    name: str = "Eigenes Teil"
    hoehe_mm: float = 10.0
    boden_mm: float = 0.0  # Löcher schneiden erst ab dieser Höhe; 0 = durchgehend
    anzahl: int = 1
    formen: list = field(default_factory=list)
    notiz: str = ""
    # Lage in der Schublade (Ursprung vorne links, Millimeter). Nur wirksam bei platziert=True.
    platziert: bool = False
    x_mm: float = 0.0
    y_mm: float = 0.0
    drehung: int = 0  # 0 oder 90 Grad
    # Kanten: obere Außenkante als Fase oder Rundung, untere Außenkante als Fase (gegen Elefantenfuß)
    kante_oben_art: str = "keine"  # keine | fase | rund
    kante_oben_mm: float = 0.0
    kante_unten_mm: float = 0.0

    @staticmethod
    def from_dict(data: dict) -> "Eigenteil":
        known = {f.name for f in Eigenteil.__dataclass_fields__.values()}  # type: ignore
        raw = {k: v for k, v in data.items() if k in known}
        return Eigenteil(**raw)

    def to_dict(self) -> dict:
        return asdict(self)


KANTEN_ARTEN = {"keine": 0, "fase": 1, "rund": 2}


def eigen_params(teil: "Eigenteil") -> dict:
    """Zahlenparameter für den FreeCAD-Worker (das Tabellenblatt kennt nur Zahlen)."""
    return {
        "Hoehe": float(teil.hoehe_mm),
        "Boden": float(teil.boden_mm),
        "Formen": teil.formen,
        "KanteObenArt": KANTEN_ARTEN.get(teil.kante_oben_art, 0),
        "KanteObenMm": float(teil.kante_oben_mm),
        "KanteUntenMm": float(teil.kante_unten_mm),
    }


def _zahl(wert, name: str) -> float:
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        raise ValueError("%s ist keine Zahl." % name)
    if not math.isfinite(zahl):
        raise ValueError("%s ist keine endliche Zahl." % name)
    return zahl


def form_bbox(form: dict) -> tuple[float, float, float, float]:
    """x0, y0, x1, y1 einer Form."""
    typ = form.get("typ")
    if typ == "rechteck":
        x = _zahl(form.get("x"), "x")
        y = _zahl(form.get("y"), "y")
        return x, y, x + _zahl(form.get("b"), "b"), y + _zahl(form.get("t"), "t")
    if typ == "kreis":
        x = _zahl(form.get("x"), "x")
        y = _zahl(form.get("y"), "y")
        r = _zahl(form.get("r"), "r")
        return x - r, y - r, x + r, y + r
    if typ == "polygon":
        punkte = form.get("punkte") or []
        xs = [_zahl(p[0], "x") for p in punkte]
        ys = [_zahl(p[1], "y") for p in punkte]
        return min(xs), min(ys), max(xs), max(ys)
    raise ValueError("Unbekannte Form „%s“." % typ)


def _flaeche_polygon(punkte) -> float:
    s = 0.0
    n = len(punkte)
    for i in range(n):
        x1, y1 = punkte[i]
        x2, y2 = punkte[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _strecken_schneiden(a, b, c, d) -> bool:
    def ori(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1, o2, o3, o4 = ori(a, b, c), ori(a, b, d), ori(c, d, a), ori(c, d, b)
    return (o1 * o2 < -1e-9) and (o3 * o4 < -1e-9)


def polygon_selbstschnitt(punkte) -> bool:
    n = len(punkte)
    for i in range(n):
        a, b = punkte[i], punkte[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            c, d = punkte[j], punkte[(j + 1) % n]
            if _strecken_schneiden(a, b, c, d):
                return True
    return False


def eigenteil_pruefen(teil: Eigenteil, bauraum_mm=(256.0, 256.0, 256.0)) -> list[str]:
    """Liefert deutsche Fehlertexte. Leere Liste = in Ordnung."""
    fehler: list[str] = []
    name = teil.name or teil.id
    try:
        hoehe = float(teil.hoehe_mm)
        boden = float(teil.boden_mm)
    except (TypeError, ValueError):
        return ["%s: Höhe oder Boden ist keine Zahl." % name]
    if not (MIN_MASS_MM <= hoehe <= float(bauraum_mm[2])):
        fehler.append("%s: Höhe muss zwischen %.1f und %.0f mm liegen." % (name, MIN_MASS_MM, bauraum_mm[2]))
    if boden < 0 or boden >= hoehe:
        fehler.append("%s: Boden muss kleiner als die Höhe sein." % name)
    if int(teil.anzahl) < 1:
        fehler.append("%s: Anzahl muss mindestens 1 sein." % name)
    if not teil.formen:
        return fehler + ["%s: Es ist noch keine Form gezeichnet." % name]
    if teil.kante_oben_art not in KANTEN_ARTEN:
        fehler.append("%s: Unbekannte Kantenart „%s“." % (name, teil.kante_oben_art))
    try:
        oben, unten = float(teil.kante_oben_mm), float(teil.kante_unten_mm)
    except (TypeError, ValueError):
        return fehler + ["%s: Kantenmaß ist keine Zahl." % name]
    if oben < 0 or unten < 0:
        fehler.append("%s: Kantenmaße dürfen nicht negativ sein." % name)
    if teil.kante_oben_art == "keine" and oben > 0:
        fehler.append("%s: Für die obere Kante ist keine Art gewählt." % name)
    if oben + unten > hoehe / 2.0 + 1e-9 and (oben > 0 or unten > 0):
        fehler.append("%s: Obere und untere Kante zusammen dürfen höchstens die halbe Höhe (%.1f mm) betragen." % (name, hoehe / 2.0))
    if len(teil.formen) > MAX_FORMEN:
        return fehler + ["%s: Zu viele Formen (höchstens %d)." % (name, MAX_FORMEN)]
    additiv = 0
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    for index, form in enumerate(teil.formen, 1):
        marke = "%s, Form %d" % (name, index)
        try:
            typ = form.get("typ")
            if typ not in TYPEN:
                fehler.append("%s: unbekannte Art „%s“." % (marke, typ))
                continue
            if typ == "rechteck":
                if _zahl(form.get("b"), "Breite") < MIN_MASS_MM or _zahl(form.get("t"), "Tiefe") < MIN_MASS_MM:
                    fehler.append("%s: Rechteck ist kleiner als %.1f mm." % (marke, MIN_MASS_MM))
                    continue
                radius = _zahl(form.get("radius") or 0, "Eckenradius")
                grenze = min(_zahl(form.get("b"), "Breite"), _zahl(form.get("t"), "Tiefe")) / 2.0
                if radius < 0 or radius > grenze + 1e-9:
                    fehler.append("%s: Eckenradius muss zwischen 0 und %.1f mm liegen." % (marke, grenze))
                    continue
            elif typ == "kreis":
                if _zahl(form.get("r"), "Radius") * 2 < MIN_MASS_MM:
                    fehler.append("%s: Kreis ist kleiner als %.1f mm." % (marke, MIN_MASS_MM))
                    continue
            else:
                punkte = form.get("punkte") or []
                if len(punkte) < 3:
                    fehler.append("%s: Ein Vieleck braucht mindestens 3 Punkte." % marke)
                    continue
                koords = [(_zahl(p[0], "x"), _zahl(p[1], "y")) for p in punkte]
                if polygon_selbstschnitt(koords):
                    fehler.append("%s: Das Vieleck überschneidet sich selbst." % marke)
                    continue
                if abs(_flaeche_polygon(koords)) < 0.1:
                    fehler.append("%s: Das Vieleck hat keine Fläche." % marke)
                    continue
            bx0, by0, bx1, by1 = form_bbox(form)
        except (ValueError, TypeError, IndexError) as exc:
            fehler.append("%s: %s" % (marke, exc))
            continue
        if not form.get("loch"):
            additiv += 1
            x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    if additiv == 0 and not fehler:
        fehler.append("%s: Es gibt nur Löcher, aber keine Form, die Material hinzufügt." % name)
    if additiv and not fehler:
        if (x1 - x0) > bauraum_mm[0] + 1e-6 or (y1 - y0) > bauraum_mm[1] + 1e-6:
            fehler.append(
                "%s: %.1f × %.1f mm passt nicht in den Druck-Bauraum %.0f × %.0f mm."
                % (name, x1 - x0, y1 - y0, bauraum_mm[0], bauraum_mm[1])
            )
    return fehler


def eigenteil_sollgroesse(teil: Eigenteil) -> list[float] | None:
    """Außenmaß (Breite, Tiefe, Höhe) aus den hinzufügenden Formen."""
    x0 = y0 = math.inf
    x1 = y1 = -math.inf
    for form in teil.formen:
        if form.get("loch"):
            continue
        bx0, by0, bx1, by1 = form_bbox(form)
        x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    if x0 == math.inf:
        return None
    return [round(x1 - x0, 3), round(y1 - y0, 3), round(float(teil.hoehe_mm), 3)]


def eigenteil_rechteck_mm(teil: Eigenteil) -> tuple[float, float, float, float] | None:
    """Belegte Fläche in der Schublade: x, y, Breite, Tiefe (nach Drehung). None, wenn nicht platziert."""
    if not teil.platziert:
        return None
    soll = eigenteil_sollgroesse(teil)
    if soll is None:
        return None
    breite, tiefe = soll[0], soll[1]
    if int(teil.drehung) % 180 == 90:
        breite, tiefe = tiefe, breite
    return (float(teil.x_mm), float(teil.y_mm), float(breite), float(tiefe))
