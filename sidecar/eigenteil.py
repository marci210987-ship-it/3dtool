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
TYPEN = ("rechteck", "kreis", "polygon", "text")
SENK_ARTEN = ("keine", "senkung", "gegenbohrung", "sechskant")
SEITEN = ("vorne", "hinten", "links", "rechts")


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
    # Bohrungen und Schlitze von der Seite (Wand vorne/hinten/links/rechts)
    seitenloecher: list = field(default_factory=list)
    # Drehprofil: Punkte (Radius, Höhe), wird um die senkrechte Achse bei (dreh_x_mm, dreh_y_mm) gedreht
    profil: list = field(default_factory=list)
    dreh_x_mm: float = 0.0
    dreh_y_mm: float = 0.0

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
        "Seitenloecher": teil.seitenloecher,
        "Profil": teil.profil,
        "DrehX": float(teil.dreh_x_mm),
        "DrehY": float(teil.dreh_y_mm),
    }


def form_hoehen(form: dict, teil_hoehe: float) -> tuple[float, float]:
    """Starthöhe z und Höhe h einer hinzufügenden Form.

    Ohne Angabe: Start bei 0 und bis zur Teilhöhe. Mit ``z_mm`` ohne ``h_mm``: ab z bis zur Teilhöhe.
    """
    z = float(form.get("z_mm") or 0.0)
    h = form.get("h_mm")
    h = float(h) if h not in (None, "") else float(teil_hoehe) - z
    return z, h


def form_oberkante(form: dict, teil_hoehe: float) -> float:
    """Höchster Punkt einer hinzufügenden Form (bei einem Keil die hintere, höhere Kante)."""
    z, h = form_hoehen(form, teil_hoehe)
    keil = float(form.get("keil_mm") or 0.0) if form.get("typ") == "rechteck" else 0.0
    return z + h + max(0.0, keil)


def eigenteil_hoehe(teil: "Eigenteil") -> float:
    """Gesamthöhe: höchste Oberkante aller Formen, die Material hinzufügen."""
    hoechste = 0.0
    for form in teil.formen:
        if form.get("loch"):
            continue
        try:
            hoechste = max(hoechste, form_oberkante(form, float(teil.hoehe_mm)))
        except (TypeError, ValueError):
            continue
    for punkt in teil.profil or []:
        try:
            hoechste = max(hoechste, float(punkt[1]))
        except (TypeError, ValueError, IndexError):
            continue
    return hoechste if hoechste > 0 else float(teil.hoehe_mm)


def form_zusatz_pruefen(form: dict, marke: str, hoehe_form: float | None) -> list[str]:
    """Prüft Kante, Schräge und Keil einer Form. hoehe_form: Höhe der Form (bei Material), sonst None."""
    fehler: list[str] = []
    loch = bool(form.get("loch"))
    typ = form.get("typ")
    try:
        art = form.get("kante_art") or "keine"
        kante = float(form.get("kante_mm") or 0.0)
        schraege = float(form.get("schraege_mm") or 0.0)
        keil = float(form.get("keil_mm") or 0.0)
        x0, y0, x1, y1 = form_bbox(form)
        klein = min(x1 - x0, y1 - y0)
    except (TypeError, ValueError):
        return ["%s: Kante, Schräge oder Keil ist keine Zahl." % marke]
    if art not in KANTEN_ARTEN:
        fehler.append("%s: Unbekannte Kantenart „%s“." % (marke, art))
    if kante < 0 or schraege < 0:
        fehler.append("%s: Kante und Schräge dürfen nicht negativ sein." % marke)
    if art == "keine" and kante > 0:
        fehler.append("%s: Für die Kante ist keine Art gewählt." % marke)
    if art != "keine" and kante > 0:
        if kante > klein / 2.0 + 1e-9:
            fehler.append("%s: Kante darf höchstens die halbe kleinste Seite (%.1f mm) betragen." % (marke, klein / 2.0))
        if hoehe_form is not None and kante > hoehe_form / 2.0 + 1e-9:
            fehler.append("%s: Kante darf höchstens die halbe Höhe der Form (%.1f mm) betragen." % (marke, hoehe_form / 2.0))
        if schraege > 0:
            fehler.append("%s: Kante und Schräge lassen sich an einer Form nicht kombinieren." % marke)
        if keil != 0:
            fehler.append("%s: Kante und Keil lassen sich an einer Form nicht kombinieren." % marke)
    if schraege > 0:
        if not loch and schraege >= klein / 2.0 - 1e-9:
            fehler.append("%s: Die Schräge muss kleiner als die halbe kleinste Seite (%.1f mm) sein, sonst läuft die Form spitz zu." % (marke, klein / 2.0))
        if loch and schraege > 100:
            fehler.append("%s: Die Aufweitung des Lochs ist zu groß." % marke)
        if typ == "polygon" and not loch and schraege >= klein / 4.0:
            fehler.append("%s: Bei einem Vieleck darf die Schräge höchstens ein Viertel der kleinsten Seite (%.1f mm) betragen." % (marke, klein / 4.0))
    if keil != 0:
        if typ != "rechteck" or loch:
            fehler.append("%s: Ein Keil ist nur an einem Rechteck möglich, das Material hinzufügt." % marke)
        else:
            if schraege > 0 or float(form.get("radius") or 0.0) > 0:
                fehler.append("%s: Ein Keil lässt sich nicht mit Schräge oder Eckenradius kombinieren." % marke)
            if float(form.get("winkel") or 0.0) % 360 != 0:
                fehler.append("%s: Ein Keil lässt sich nicht drehen." % marke)
            if hoehe_form is not None and hoehe_form + keil < MIN_MASS_MM:
                fehler.append("%s: Die Höhe vorn plus Keil ist zu klein." % marke)
    return fehler


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
        b = _zahl(form.get("b"), "b")
        t = _zahl(form.get("t"), "t")
        winkel = _zahl(form.get("winkel") or 0, "Drehwinkel")
        if winkel % 180 == 0:
            return x, y, x + b, y + t
        # Gedrehtes Rechteck (um seine Mitte): exakte Bounding-Box, auch mit abgerundeten Ecken
        r = _zahl(form.get("radius") or 0, "Eckenradius")
        w = math.radians(winkel)
        c, s = abs(math.cos(w)), abs(math.sin(w))
        hx = (b / 2 - r) * c + (t / 2 - r) * s + r
        hy = (b / 2 - r) * s + (t / 2 - r) * c + r
        mx, my = x + b / 2, y + t / 2
        return round(mx - hx, 6), round(my - hy, 6), round(mx + hx, 6), round(my + hy, 6)
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
    if typ == "text":
        from sidecar.pixelschrift import text_groesse

        x = _zahl(form.get("x"), "x")
        y = _zahl(form.get("y"), "y")
        b, t = text_groesse(str(form.get("text") or ""), _zahl(form.get("schrift_mm"), "Schrifthöhe"))
        return x, y, x + b, y + t
    raise ValueError("Unbekannte Form „%s“." % typ)


def profil_bbox(teil: "Eigenteil") -> tuple[float, float, float, float] | None:
    """x0, y0, x1, y1 des Drehteils (None ohne Profil)."""
    if not teil.profil:
        return None
    rmax = max(float(p[0]) for p in teil.profil)
    dx, dy = float(teil.dreh_x_mm), float(teil.dreh_y_mm)
    return dx - rmax, dy - rmax, dx + rmax, dy + rmax


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


def _senkung_pruefen(form: dict, marke: str, gesamt: float) -> list[str]:
    """Senkung, Gegenbohrung oder Sechskant-Tasche an einem runden Loch."""
    art = form.get("senk_art") or "keine"
    if art not in SENK_ARTEN:
        return ["%s: Unbekannte Senkungsart „%s“." % (marke, art)]
    if art == "keine":
        return []
    if not form.get("loch"):
        return ["%s: Senkung, Gegenbohrung und Sechskant gibt es nur an Löchern." % marke]
    try:
        d = 2 * float(form.get("r"))
        gross = _zahl(form.get("senk_d_mm"), "Senkungsdurchmesser")
        tief = _zahl(form.get("senk_t_mm") or 0, "Senkungstiefe")
    except (TypeError, ValueError) as exc:
        return ["%s: %s" % (marke, exc)]
    if form.get("senk_seite") not in (None, "oben", "unten"):
        return ["%s: Die Seite der Senkung muss oben oder unten sein." % marke]
    fehler = []
    if gross <= d + 0.2:
        fehler.append("%s: Der Durchmesser der Senkung (%.1f mm) muss größer als das Loch (%.1f mm) sein." % (marke, gross, d))
        return fehler
    if art == "senkung":
        tief = (gross - d) / 2.0  # 90° Senkwinkel
    elif tief < MIN_MASS_MM:
        fehler.append("%s: Die Tiefe der Senkung ist zu klein." % marke)
    if tief >= gesamt - 0.4:
        fehler.append("%s: Die Senkung (%.1f mm tief) lässt kein Material von der Teilhöhe %.1f mm übrig." % (marke, tief, gesamt))
    return fehler


def _text_pruefen(form: dict, marke: str) -> list[str]:
    from sidecar.pixelschrift import MAX_ZEICHEN, MIN_PIXEL_MM, normalisiert, unbekannte_zeichen

    text = str(form.get("text") or "")
    if not text.strip():
        return ["%s: Der Text ist leer." % marke]
    if len(normalisiert(text)) > MAX_ZEICHEN:
        return ["%s: Der Text ist zu lang (höchstens %d Zeichen)." % (marke, MAX_ZEICHEN)]
    fehler = []
    fremd = unbekannte_zeichen(text)
    if fremd:
        fehler.append("%s: Diese Zeichen gibt es in der Schrift nicht: %s" % (marke, " ".join(fremd)))
    try:
        schrift = _zahl(form.get("schrift_mm"), "Schrifthöhe")
    except ValueError as exc:
        return fehler + ["%s: %s" % (marke, exc)]
    if schrift / 7.0 < MIN_PIXEL_MM - 1e-9:
        fehler.append("%s: Die Schrift ist zu klein, mindestens %.1f mm Höhe (Pixel %.1f mm)." % (marke, MIN_PIXEL_MM * 7, MIN_PIXEL_MM))
    if form.get("kante_art") not in (None, "keine") or form.get("schraege_mm") or form.get("keil_mm"):
        fehler.append("%s: Text lässt sich nicht mit Kante, Schräge oder Keil kombinieren." % marke)
    return fehler


def _profil_pruefen(teil: "Eigenteil", name: str, bauraum_mm) -> list[str]:
    if not teil.profil:
        return []
    marke = "%s, Drehprofil" % name
    try:
        punkte = [(_zahl(p[0], "Radius"), _zahl(p[1], "Höhe")) for p in teil.profil]
        _zahl(teil.dreh_x_mm, "Mitte x")
        _zahl(teil.dreh_y_mm, "Mitte y")
    except (ValueError, TypeError, IndexError) as exc:
        return ["%s: %s" % (marke, exc)]
    if len(punkte) < 3:
        return ["%s: Das Profil braucht mindestens 3 Punkte." % marke]
    if len(punkte) > 60:
        return ["%s: Zu viele Profilpunkte (höchstens 60)." % marke]
    if any(r < 0 or z < 0 for r, z in punkte):
        return ["%s: Radius und Höhe dürfen nicht negativ sein." % marke]
    if polygon_selbstschnitt(punkte):
        return ["%s: Das Profil überschneidet sich selbst." % marke]
    if abs(_flaeche_polygon(punkte)) < 0.1:
        return ["%s: Das Profil hat keine Fläche." % marke]
    if max(r for r, _ in punkte) * 2 > min(bauraum_mm[0], bauraum_mm[1]) + 1e-6:
        return ["%s: Der Durchmesser passt nicht in den Bauraum." % marke]
    if max(z for _, z in punkte) > float(bauraum_mm[2]) + 1e-6:
        return ["%s: Die Höhe liegt über dem Bauraum." % marke]
    if max(r for r, _ in punkte) < MIN_MASS_MM:
        return ["%s: Das Profil ist zu schmal." % marke]
    if teil.dreh_x_mm - max(r for r, _ in punkte) < -1e-9 or teil.dreh_y_mm - max(r for r, _ in punkte) < -1e-9:
        return ["%s: Das Drehteil ragt über den Nullpunkt hinaus; Mitte x und y größer als der größte Radius wählen." % marke]
    return []


def _seitenloecher_pruefen(teil: "Eigenteil", name: str, bbox, gesamt: float) -> list[str]:
    fehler = []
    if len(teil.seitenloecher or []) > 40:
        return ["%s: Zu viele Seitenlöcher (höchstens 40)." % name]
    x0, y0, x1, y1 = bbox
    for i, s in enumerate(teil.seitenloecher or [], 1):
        marke = "%s, Seitenloch %d" % (name, i)
        try:
            seite = s.get("seite")
            art = s.get("art") or "rund"
            pos = _zahl(s.get("pos_mm"), "Position")
            z = _zahl(s.get("z_mm"), "Höhe")
            tiefe = _zahl(s.get("tiefe_mm") or 0, "Tiefe")
            if art == "rund":
                b = h = _zahl(s.get("d_mm"), "Durchmesser")
            elif art == "schlitz":
                b, h = _zahl(s.get("b_mm"), "Breite"), _zahl(s.get("h_mm"), "Höhe des Schlitzes")
            else:
                fehler.append("%s: Unbekannte Art „%s“." % (marke, art))
                continue
        except (ValueError, TypeError) as exc:
            fehler.append("%s: %s" % (marke, exc))
            continue
        if seite not in SEITEN:
            fehler.append("%s: Unbekannte Seite „%s“." % (marke, seite))
            continue
        if b < MIN_MASS_MM or h < MIN_MASS_MM:
            fehler.append("%s: Das Maß ist kleiner als %.1f mm." % (marke, MIN_MASS_MM))
            continue
        laenge_wand = (x1 - x0) if seite in ("vorne", "hinten") else (y1 - y0)
        anfang = x0 if seite in ("vorne", "hinten") else y0
        tief_max = (y1 - y0) if seite in ("vorne", "hinten") else (x1 - x0)
        if pos - b / 2 < anfang - 1e-9 or pos + b / 2 > anfang + laenge_wand + 1e-9:
            fehler.append("%s: Die Position liegt nicht an der Wand (%.1f bis %.1f mm)." % (marke, anfang, anfang + laenge_wand))
        if z - h / 2 < -1e-9 or z + h / 2 > gesamt + 1e-9:
            fehler.append("%s: Das Loch liegt nicht innerhalb der Teilhöhe (0 bis %.1f mm)." % (marke, gesamt))
        if tiefe < 0 or tiefe > tief_max + 1e-9:
            fehler.append("%s: Tiefe muss zwischen 0 (durchgehend) und %.1f mm liegen." % (marke, tief_max))
    return fehler


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
    if not teil.formen and not teil.profil:
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
    gesamt = eigenteil_hoehe(teil)
    if oben + unten > gesamt / 2.0 + 1e-9 and (oben > 0 or unten > 0):
        fehler.append("%s: Obere und untere Kante zusammen dürfen höchstens die halbe Höhe (%.1f mm) betragen." % (name, gesamt / 2.0))
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
                _zahl(form.get("winkel") or 0, "Drehwinkel")
                radius = _zahl(form.get("radius") or 0, "Eckenradius")
                grenze = min(_zahl(form.get("b"), "Breite"), _zahl(form.get("t"), "Tiefe")) / 2.0
                if radius < 0 or radius > grenze + 1e-9:
                    fehler.append("%s: Eckenradius muss zwischen 0 und %.1f mm liegen." % (marke, grenze))
                    continue
            elif typ == "kreis":
                if _zahl(form.get("r"), "Radius") * 2 < MIN_MASS_MM:
                    fehler.append("%s: Kreis ist kleiner als %.1f mm." % (marke, MIN_MASS_MM))
                    continue
                fehler.extend(_senkung_pruefen(form, marke, gesamt))
            elif typ == "text":
                fehler.extend(_text_pruefen(form, marke))
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
                eckenradius = _zahl(form.get("radius") or 0, "Eckenradius")
                if eckenradius < 0:
                    fehler.append("%s: Eckenradius darf nicht negativ sein." % marke)
                    continue
                if eckenradius > 0:
                    if form.get("kante_art") not in (None, "keine"):
                        fehler.append("%s: Abgerundete Ecken lassen sich nicht mit Fase oder Rundung der Kante kombinieren." % marke)
                    kuerzeste = min(math.dist(koords[i], koords[(i + 1) % len(koords)]) for i in range(len(koords)))
                    if eckenradius > kuerzeste / 2.0 + 1e-9:
                        fehler.append("%s: Eckenradius darf höchstens die halbe kürzeste Seite (%.1f mm) betragen." % (marke, kuerzeste / 2.0))
            bx0, by0, bx1, by1 = form_bbox(form)
        except (ValueError, TypeError, IndexError) as exc:
            fehler.append("%s: %s" % (marke, exc))
            continue
        try:
            z0 = float(form.get("z_mm") or 0.0)
            hh = form.get("h_mm")
            if z0 < 0:
                fehler.append("%s: Starthöhe darf nicht negativ sein." % marke)
            elif not form.get("loch"):
                z0, hh = form_hoehen(form, hoehe)
                if hh < MIN_MASS_MM:
                    fehler.append("%s: Die Höhe der Form (%.1f mm) ist zu klein; Starthöhe und Höhe prüfen." % (marke, hh))
                elif form_oberkante(form, hoehe) > float(bauraum_mm[2]) + 1e-6:
                    fehler.append("%s: Oberkante bei %.1f mm liegt über dem Bauraum." % (marke, form_oberkante(form, hoehe)))
            elif hh not in (None, "") and float(hh) < MIN_MASS_MM:
                fehler.append("%s: Die Höhe des Lochs ist zu klein." % marke)
            fehler.extend(form_zusatz_pruefen(form, marke, hh if (not form.get("loch") and isinstance(hh, float)) else None))
        except (TypeError, ValueError):
            fehler.append("%s: Starthöhe oder Höhe ist keine Zahl." % marke)
            continue
        if not form.get("loch"):
            additiv += 1
            x0, y0, x1, y1 = min(x0, bx0), min(y0, by0), max(x1, bx1), max(y1, by1)
    if teil.kante_oben_art != "keine" and any(f.get("keil_mm") for f in teil.formen if isinstance(f, dict)):
        fehler.append("%s: Die obere Teilkante lässt sich nicht mit einem Keil kombinieren (die Oberseite ist schräg)." % name)
    fehler.extend(_profil_pruefen(teil, name, bauraum_mm))
    if teil.profil and not fehler:
        additiv += 1
        pb = profil_bbox(teil)
        if pb:
            x0, y0, x1, y1 = min(x0, pb[0]), min(y0, pb[1]), max(x1, pb[2]), max(y1, pb[3])
    if additiv == 0 and not fehler:
        fehler.append("%s: Es gibt nur Löcher, aber keine Form, die Material hinzufügt." % name)
    if not fehler:
        fehler.extend(_seitenloecher_pruefen(teil, name, (x0, y0, x1, y1), gesamt))
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
    pb = profil_bbox(teil)
    if pb:
        x0, y0, x1, y1 = min(x0, pb[0]), min(y0, pb[1]), max(x1, pb[2]), max(y1, pb[3])
    if x0 == math.inf:
        return None
    return [round(x1 - x0, 3), round(y1 - y0, 3), round(eigenteil_hoehe(teil), 3)]


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
