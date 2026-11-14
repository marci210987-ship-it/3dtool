# -*- coding: utf-8 -*-
"""Schubladenlayout: Raster, Boxen, Kollision, Verbinder.

Die Plattenaufteilung kommt aus hausraster_plan.plane_schublade (0.2-qs1).
Die Platzierung der Boxen ist Anwendungslogik und existiert im Generator nicht.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

from sidecar.paths import HAUSRASTER_SRC

if str(HAUSRASTER_SRC) not in sys.path:
    sys.path.insert(0, str(HAUSRASTER_SRC))

from hausraster_const import (  # noqa: E402
    RASTER_MM,
    HOEHENEINHEIT_MM,
    LIPPE_HOEHE,
    BAURAUM_X,
    BAURAUM_Y,
    BAURAUM_Z,
    SCHUBLADENSPIEL_STANDARD,
    VERBINDER_SPIEL_STANDARD,
    BODEN_PLATTE_STANDARD,
    box_hoehe,
    plattenhoehe,
    kasten_aussen,
    default_params,
    pruefe_parameter,
)
from hausraster_plan import plane_schublade, plan_als_text  # noqa: E402
from sidecar.eigenteil import Eigenteil, eigen_params, eigenteil_hoehe, eigenteil_pruefen, eigenteil_rechteck_mm  # noqa: E402
from sidecar.ersatzteil import masse as ersatz_masse, pruefe as ersatz_pruefen, katalog_nach_id  # noqa: E402
from sidecar.kabel import (  # noqa: E402
    katalog_nach_id as kabel_katalog,
    nutzlaengen as kabel_laengen,
    stuecke as kabel_stuecke,
    system_meldungen as kabel_meldungen,
)


FORMAT = "cadstudio.projekt"
FORMAT_VERSION = 1


def neue_id(prefix: str = "B") -> str:
    return "%s-%s" % (prefix, uuid.uuid4().hex[:8])


@dataclass
class Schublade:
    innenbreite_mm: float = 480.0
    innentiefe_mm: float = 420.0
    nutzhoehe_mm: float = 80.0
    spiel_mm: float = SCHUBLADENSPIEL_STANDARD
    rand_links_mm: float = 0.0
    rand_rechts_mm: float = 0.0
    rand_vorne_mm: float = 0.0
    rand_hinten_mm: float = 0.0
    verbinder_spiel_mm: float = VERBINDER_SPIEL_STANDARD
    wandstaerke_mm: float = 1.2
    boden_platte_mm: float = BODEN_PLATTE_STANDARD
    material: str = "PLA"
    bauraum_mm: tuple = (BAURAUM_X, BAURAUM_Y, BAURAUM_Z)

    @staticmethod
    def from_dict(data: dict) -> "Schublade":
        known = {f.name for f in Schublade.__dataclass_fields__.values()}  # type: ignore
        raw = {k: v for k, v in (data or {}).items() if k in known}
        if "bauraum_mm" in raw and isinstance(raw["bauraum_mm"], list):
            raw["bauraum_mm"] = tuple(raw["bauraum_mm"])
        return Schublade(**raw)


@dataclass
class Box:
    id: str
    name: str
    x: int
    y: int
    ex: int
    ey: int
    ez: int = 3
    rotation: int = 0
    fach_x: int = 1
    fach_y: int = 1
    stapellippe: bool = True
    deckel: bool = False
    herausnehmbar: bool = False
    kabelkerben: bool = False
    art: str = "raster"  # raster | besteck
    notiz: str = ""

    @staticmethod
    def from_dict(data: dict) -> "Box":
        known = {f.name for f in Box.__dataclass_fields__.values()}  # type: ignore
        raw = {k: v for k, v in data.items() if k in known}
        return Box(**raw)


@dataclass
class Projekt:
    name: str = "Neue Schublade"
    schublade: Schublade = field(default_factory=Schublade)
    boxen: list = field(default_factory=list)
    eigene: list = field(default_factory=list)
    nur_eigene: bool = False  # nur gezeichnete Teile, ohne Schublade, Platten und Boxen
    ersatzteile: list = field(default_factory=list)
    nur_ersatz: bool = False  # nur Ersatzteile, ohne Schublade
    kabel: list = field(default_factory=list)
    nur_kabel: bool = False  # nur Kabelmanagement, ohne Schublade
    notiz: str = ""

    def to_dict(self) -> dict:
        return {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "name": self.name,
            "schublade": asdict(self.schublade),
            "boxen": [asdict(b) for b in self.boxen],
            "eigene": [e.to_dict() for e in self.eigene],
            "nur_eigene": bool(self.nur_eigene),
            "ersatzteile": list(self.ersatzteile),
            "nur_ersatz": bool(self.nur_ersatz),
            "kabel": list(self.kabel),
            "nur_kabel": bool(self.nur_kabel),
            "notiz": self.notiz,
        }

    @staticmethod
    def from_dict(data: dict) -> "Projekt":
        if data.get("format") not in (None, FORMAT):
            raise ValueError("Unbekanntes Projektdateiformat.")
        if int(data.get("version", 1)) > FORMAT_VERSION:
            raise ValueError("Die Projektdatei ist neuer als diese CAD-Studio-Version.")
        return Projekt(
            name=data.get("name") or "Schublade",
            schublade=Schublade.from_dict(data.get("schublade") or {}),
            boxen=[Box.from_dict(b) for b in data.get("boxen") or []],
            eigene=[Eigenteil.from_dict(e) for e in data.get("eigene") or []],
            nur_eigene=bool(data.get("nur_eigene", False)),
            ersatzteile=[dict(e) for e in data.get("ersatzteile") or []],
            nur_ersatz=bool(data.get("nur_ersatz", False)),
            kabel=[dict(k) for k in data.get("kabel") or []],
            nur_kabel=bool(data.get("nur_kabel", False)),
            notiz=data.get("notiz") or "",
        )


def footprint(box: Box) -> tuple[int, int, int, int]:
    """Zellenrechteck nach Drehung: x, y, breite, tiefe."""
    rot = int(box.rotation) % 360
    ex, ey = int(box.ex), int(box.ey)
    if rot in (90, 270):
        ex, ey = ey, ex
    return int(box.x), int(box.y), ex, ey


def faecher_orientiert(box: Box) -> tuple[int, int]:
    rot = int(box.rotation) % 360
    fx, fy = int(box.fach_x), int(box.fach_y)
    if rot in (90, 270):
        return fy, fx
    return fx, fy


def box_hoehe_mm(box: Box) -> float:
    if box.art == "besteck":
        # Besteckeinsatz: Einsatzhöhe ohne Gridfinity-Lippe, Füsse extra.
        return float(box.ez) * HOEHENEINHEIT_MM
    return box_hoehe(int(box.ez), bool(box.stapellippe))


def benoetigte_hoehe_mm(box: Box, boden_platte: float) -> float:
    """Höhe ab Schubladenboden.

    Der Boxfuss steht auf dem Taschenboden. Die Platte ragt nicht zusätzlich
    über die Box hinaus. Beim Besteckeinsatz mit Füssen kommen 4,75 mm dazu.
    """
    if box.art == "besteck":
        return box_hoehe_mm(box) + 4.75
    return box_hoehe_mm(box) + float(boden_platte)


def ueberlappung(a: Box, b: Box) -> bool:
    ax, ay, aw, ah = footprint(a)
    bx, by, bw, bh = footprint(b)
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def ausserhalb(box: Box, einheiten_x: int, einheiten_y: int) -> bool:
    x, y, w, h = footprint(box)
    if w <= 0 or h <= 0:
        return True
    return x < 0 or y < 0 or x + w > einheiten_x or y + h > einheiten_y


def box_rechteck_mm(box: Box, ox: float, oy: float) -> tuple[float, float, float, float]:
    """Belegte Fläche einer Box in Millimetern: x, y, Breite, Tiefe."""
    x, y, ex, ey = footprint(box)
    if box.art == "besteck":
        return (ox + x * RASTER_MM, oy + y * RASTER_MM, ex * RASTER_MM, ey * RASTER_MM)
    return (ox + x * RASTER_MM + 0.25, oy + y * RASTER_MM + 0.25, kasten_aussen(ex, 0.0), kasten_aussen(ey, 0.0))


def _rechtecke_schneiden(a, b, eps: float = 0.01) -> bool:
    return a[0] < b[0] + b[2] - eps and b[0] < a[0] + a[2] - eps and a[1] < b[1] + b[3] - eps and b[1] < a[1] + a[3] - eps


def platzierte_eigene_pruefen(projekt: "Projekt", plan) -> list[str]:
    """Prüft platzierte eigene Teile gegen Schublade, Höhe, Boxen und einander."""
    fehler: list[str] = []
    sch = projekt.schublade
    ox, oy = raster_ursprung_mm(sch, plan)
    boxen = [(box, box_rechteck_mm(box, ox, oy)) for box in projekt.boxen]
    links = float(sch.rand_links_mm) + float(sch.spiel_mm)
    vorne = float(sch.rand_vorne_mm) + float(sch.spiel_mm)
    rechts = float(sch.innenbreite_mm) - float(sch.rand_rechts_mm) - float(sch.spiel_mm)
    hinten = float(sch.innentiefe_mm) - float(sch.rand_hinten_mm) - float(sch.spiel_mm)
    belegt = []
    for eigen in projekt.eigene:
        rect = eigenteil_rechteck_mm(eigen)
        if rect is None:
            continue
        name = eigen.name or eigen.id
        x, y, w, d = rect
        if x < links - 1e-6 or y < vorne - 1e-6 or x + w > rechts + 1e-6 or y + d > hinten + 1e-6:
            fehler.append("%s liegt nicht vollständig in der Schublade." % name)
        hoehe = eigenteil_hoehe(eigen) + float(sch.boden_platte_mm)
        if hoehe > float(sch.nutzhoehe_mm) + 1e-6:
            fehler.append("%s braucht %.1f mm Höhe, die Schublade hat nur %.1f mm nutzbare Höhe." % (name, hoehe, sch.nutzhoehe_mm))
        for box, brect in boxen:
            if _rechtecke_schneiden(rect, brect):
                fehler.append("%s überlappt die Box %s." % (name, box.name or box.id))
        for andere, arect in belegt:
            if _rechtecke_schneiden(rect, arect):
                fehler.append("%s überlappt %s." % (name, andere.name or andere.id))
        belegt.append((eigen, rect))
    return fehler


def freie_zellen(boxen: list[Box], einheiten_x: int, einheiten_y: int) -> list[tuple[int, int]]:
    belegt = set()
    for box in boxen:
        x, y, w, h = footprint(box)
        for i in range(x, x + w):
            for j in range(y, y + h):
                if 0 <= i < einheiten_x and 0 <= j < einheiten_y:
                    belegt.add((i, j))
    frei = []
    for j in range(einheiten_y):
        for i in range(einheiten_x):
            if (i, j) not in belegt:
                frei.append((i, j))
    return frei


def plan_berechnen(schublade: Schublade):
    nutz_x = (
        float(schublade.innenbreite_mm)
        - float(schublade.rand_links_mm)
        - float(schublade.rand_rechts_mm)
    )
    nutz_y = (
        float(schublade.innentiefe_mm)
        - float(schublade.rand_vorne_mm)
        - float(schublade.rand_hinten_mm)
    )
    plan = plane_schublade(
        nutz_x,
        nutz_y,
        spiel_je_seite=float(schublade.spiel_mm),
        bauraum_x=float(schublade.bauraum_mm[0]),
        bauraum_y=float(schublade.bauraum_mm[1]),
        bodenstaerke=float(schublade.boden_platte_mm),
    )
    return plan


def raster_ursprung_mm(schublade: Schublade, plan) -> tuple[float, float]:
    """Linke/vordere Ecke von Zelle (0,0), nach Benutzer-Rand, Spiel und integriertem Plattenrand."""
    if not plan.platten:
        return (
            float(schublade.rand_links_mm) + float(schublade.spiel_mm),
            float(schublade.rand_vorne_mm) + float(schublade.spiel_mm),
        )
    # Der integrierte Rand liegt auf den Aussenplatten. Zelle (0,0) beginnt
    # hinter dem linken/vorderen Rand der Platte, die bei (0,0) liegt.
    links = 0.0
    vorne = 0.0
    for platte in plan.platten:
        if platte.pos_einheit_x == 0:
            links = float(platte.rand_x_links)
        if platte.pos_einheit_y == 0:
            vorne = float(platte.rand_y_vorne)
    return (
        float(schublade.rand_links_mm) + float(schublade.spiel_mm) + links,
        float(schublade.rand_vorne_mm) + float(schublade.spiel_mm) + vorne,
    )


def platte_lage_mm(schublade: Schublade, plan, platte) -> dict:
    """Lage der Platte in der Schublade, Ursprung vorne links, Y nach hinten."""
    ox, oy = raster_ursprung_mm(schublade, plan)
    left = ox + platte.pos_einheit_x * RASTER_MM - float(platte.rand_x_links)
    front = oy + platte.pos_einheit_y * RASTER_MM - float(platte.rand_y_vorne)
    return {
        "links_mm": round(left, 3),
        "vorne_mm": round(front, 3),
        "breite_mm": float(platte.breite_mm),
        "tiefe_mm": float(platte.tiefe_mm),
        "mitte_x_mm": round(left + float(platte.breite_mm) / 2.0, 3),
        "mitte_y_mm": round(front + float(platte.tiefe_mm) / 2.0, 3),
    }


def _rippen(start: int, anzahl: int) -> set[int]:
    if anzahl < 2:
        return set()
    return set(range(start + 1, start + anzahl))


def verbinder_zwischen(a, b) -> list[dict]:
    """Gemeinsame Rippen zweier Platten. Jede Rippe braucht einen Clip."""
    treffer = []
    # a rechts an b links
    if a.pos_einheit_x + a.einheiten_x == b.pos_einheit_x and a.rand_x_rechts <= 0.05 and b.rand_x_links <= 0.05:
        ys = _rippen(a.pos_einheit_y, a.einheiten_y) & _rippen(b.pos_einheit_y, b.einheiten_y)
        for y in sorted(ys):
            treffer.append({"richtung": "senkrecht", "x_zelle": a.pos_einheit_x + a.einheiten_x, "y_zelle": y})
    if b.pos_einheit_x + b.einheiten_x == a.pos_einheit_x and b.rand_x_rechts <= 0.05 and a.rand_x_links <= 0.05:
        ys = _rippen(b.pos_einheit_y, b.einheiten_y) & _rippen(a.pos_einheit_y, a.einheiten_y)
        for y in sorted(ys):
            treffer.append({"richtung": "senkrecht", "x_zelle": b.pos_einheit_x + b.einheiten_x, "y_zelle": y})
    if a.pos_einheit_y + a.einheiten_y == b.pos_einheit_y and a.rand_y_hinten <= 0.05 and b.rand_y_vorne <= 0.05:
        xs = _rippen(a.pos_einheit_x, a.einheiten_x) & _rippen(b.pos_einheit_x, b.einheiten_x)
        for x in sorted(xs):
            treffer.append({"richtung": "waagrecht", "x_zelle": x, "y_zelle": a.pos_einheit_y + a.einheiten_y})
    if b.pos_einheit_y + b.einheiten_y == a.pos_einheit_y and b.rand_y_hinten <= 0.05 and a.rand_y_vorne <= 0.05:
        xs = _rippen(b.pos_einheit_x, b.einheiten_x) & _rippen(a.pos_einheit_x, a.einheiten_x)
        for x in sorted(xs):
            treffer.append({"richtung": "waagrecht", "x_zelle": x, "y_zelle": b.pos_einheit_y + b.einheiten_y})
    return treffer


def verbinder_liste(plan) -> list[dict]:
    platten = list(plan.platten)
    alle = []
    for i, a in enumerate(platten):
        for b in platten[i + 1 :]:
            alle.extend(verbinder_zwischen(a, b))
    return alle


def kollisionen(boxen: list[Box]) -> list[dict]:
    fund = []
    for i, a in enumerate(boxen):
        for b in boxen[i + 1 :]:
            if ueberlappung(a, b):
                fund.append(
                    {
                        "art": "ueberlappung",
                        "boxen": [a.id, b.id],
                        "text": "%s und %s überlappen sich." % (a.name or a.id, b.name or b.id),
                    }
                )
    return fund


def _ersatz_ansicht(teile: list) -> dict:
    fehler = []
    hinweise = []
    if not teile:
        fehler.append("Noch kein Ersatzteil ausgewählt.")
    for teil in teile:
        for meldung in ersatz_pruefen(teil.get("art"), teil.get("parameter") or {}):
            fehler.append("%s: %s" % (teil.get("name") or teil.get("art"), meldung))
        eintrag = katalog_nach_id(teil.get("art"))
        if eintrag and not ersatz_pruefen(teil.get("art"), teil.get("parameter") or {}):
            hinweise.append("%s – %s" % (teil.get("name") or eintrag["name"], eintrag["druck"]))
    return {
        "ok": not fehler,
        "fehler": fehler,
        "hinweise": hinweise,
        "kollisionen": [],
        "text": "",
        "ungueltig": False,
        "platten": [],
        "randstreifen": [],
        "randstreifen_hinweis": "",
        "verbinder": [],
        "verbinder_anzahl": 0,
        "einheiten_x": 0,
        "einheiten_y": 0,
        "freie_zellen": [],
        "nutz_x": 0,
        "nutz_y": 0,
        "rest_x": 0,
        "rest_y": 0,
        "raster_mm": RASTER_MM,
        "plattenhoehe_mm": 0,
        "ursprung_x_mm": 0,
        "ursprung_y_mm": 0,
    }


def _kabel_ansicht(teile: list) -> dict:
    fehler = kabel_meldungen(teile)
    hinweise = []
    for teil in teile:
        eintrag = kabel_katalog(teil.get("art"))
        name = teil.get("name") or (eintrag["name"] if eintrag else teil.get("art"))
        eigene = [m for m in fehler if str(m).startswith("%s:" % name)]
        if eintrag and not eigene:
            hinweise.append("%s – %s" % (name, eintrag["druck"]))
        if teil.get("art") == "kanal":
            laengen = kabel_laengen(dict(teil.get("parameter") or {}, art="kanal"))
            if len(laengen) > 1:
                hinweise.append(
                    "%s wird in %d Stücke geteilt, damit jedes auf das 256-mm-Bett passt."
                    % (name, len(laengen))
                )
    if teile and not fehler:
        hinweise.append("Alle Teile nutzen dasselbe Verbindungsprofil. Das Spiel ist die Lücke im Modell, nicht am Druck geprüft.")
    return {
        "ok": not fehler,
        "fehler": fehler,
        "hinweise": hinweise,
        "kollisionen": [],
        "text": "",
        "ungueltig": False,
        "platten": [],
        "randstreifen": [],
        "randstreifen_hinweis": "",
        "verbinder": [],
        "verbinder_anzahl": 0,
        "einheiten_x": 0,
        "einheiten_y": 0,
        "freie_zellen": [],
        "nutz_x": 0,
        "nutz_y": 0,
        "rest_x": 0,
        "rest_y": 0,
        "raster_mm": RASTER_MM,
        "plattenhoehe_mm": 0,
        "ursprung_x_mm": 0,
        "ursprung_y_mm": 0,
    }


def layout_pruefen(projekt: Projekt, plan=None) -> dict:
    if projekt.nur_kabel:
        ansicht = _kabel_ansicht(projekt.kabel)
        return {"ok": ansicht["ok"], "fehler": ansicht["fehler"], "hinweise": ansicht["hinweise"], "kollisionen": []}
    if projekt.nur_ersatz:
        ansicht = _ersatz_ansicht(projekt.ersatzteile)
        return {"ok": ansicht["ok"], "fehler": ansicht["fehler"], "hinweise": ansicht["hinweise"], "kollisionen": []}
    if plan is None:
        plan = plan_berechnen(projekt.schublade)
    fehler = []
    hinweise = []
    if projekt.nur_eigene:
        for eigen in projekt.eigene:
            fehler.extend(eigenteil_pruefen(eigen, projekt.schublade.bauraum_mm))
        if not projekt.eigene:
            fehler.append("Es ist noch kein Teil gezeichnet.")
        return {"ok": not fehler, "fehler": fehler, "hinweise": [], "kollisionen": []}
    if plan.ungueltig:
        fehler.append("Für diese Schublade lässt sich kein Raster bilden.")
        fehler.extend(plan.hinweise)
    for box in projekt.boxen:
        if plan.einheiten_x and ausserhalb(box, plan.einheiten_x, plan.einheiten_y):
            fehler.append("%s ragt aus dem Raster heraus." % (box.name or box.id))
        hoehe = benoetigte_hoehe_mm(box, projekt.schublade.boden_platte_mm)
        if hoehe > float(projekt.schublade.nutzhoehe_mm) + 1e-6:
            fehler.append(
                "%s braucht %.1f mm Höhe, die Schublade hat nur %.1f mm nutzbare Höhe."
                % (box.name or box.id, hoehe, projekt.schublade.nutzhoehe_mm)
            )
        fx, fy = faecher_orientiert(box)
        if box.art == "raster":
            x, y, ex, ey = footprint(box)
            params = default_params(
                Einheiten_X=ex,
                Einheiten_Y=ey,
                Einheiten_Z=int(box.ez),
                Fachanzahl_X=fx,
                Fachanzahl_Y=fy,
                Stapellippe=1 if box.stapellippe else 0,
                Wandstaerke=float(projekt.schublade.wandstaerke_mm),
                Verbinder=0,
                Verriegelung=0,
            )
            for msg in pruefe_parameter(params):
                if "Bodenstaerke_Platte" in msg or msg.startswith("Platten"):
                    continue
                fehler.append("%s: %s" % (box.name or box.id, msg))
            aussen_x = kasten_aussen(ex, 0.0)
            aussen_y = kasten_aussen(ey, 0.0)
            bx, by, bz = projekt.schublade.bauraum_mm
            if aussen_x > bx + 1e-6 or aussen_y > by + 1e-6 or box_hoehe_mm(box) > bz + 1e-6:
                fehler.append("%s passt nicht in den Druck-Bauraum (256 mm)." % (box.name or box.id))
        elif box.art == "besteck":
            _besteck_vorpruefung(box, projekt, fehler, hinweise)
        else:
            fehler.append("%s hat die unbekannte Art „%s“." % (box.name or box.id, box.art))
    fehler.extend(item["text"] for item in kollisionen(projekt.boxen))
    for eigen in projekt.eigene:
        fehler.extend(eigenteil_pruefen(eigen, projekt.schublade.bauraum_mm))
    if not plan.ungueltig:
        fehler.extend(platzierte_eigene_pruefen(projekt, plan))
    if plan.randstreifen:
        hinweise.append(
            "Es bleiben Randstreifen übrig. Sie werden als einfache, glatte Füllplatten "
            "mit exportiert und lose neben die Grundplatten gelegt (ohne Verbinder)."
        )
    hinweise.append(
        "Schubladenspiel %.2f mm und Verbinder-Spiel %.2f mm sind ungeprüfte Vorgaben, keine Messwerte."
        % (projekt.schublade.spiel_mm, projekt.schublade.verbinder_spiel_mm)
    )
    return {
        "ok": not fehler and not plan.ungueltig,
        "fehler": fehler,
        "hinweise": hinweise,
        "kollisionen": kollisionen(projekt.boxen),
    }


def _besteck_vorpruefung(box: Box, projekt: Projekt, fehler: list, hinweise: list):
    from hausraster_phase3_plan import plane_besteck

    x, y, ex, ey = footprint(box)
    breite = ex * RASTER_MM
    tiefe = ey * RASTER_MM
    if breite < 230 or tiefe < 80:
        fehler.append(
            "%s: Ein Bestecksortierer braucht mindestens etwa 230 × 80 mm (rund 6 × 2 Felder), "
            "damit die Standardfächer hineinpassen." % (box.name or box.id)
        )
        return
    plan = plane_besteck(
        {
            "Schubladenbreite": breite,
            "Schubladentiefe": tiefe,
            "Schubladenspiel": 0.0,
            "Verfuegbare_Hoehe": float(projekt.schublade.nutzhoehe_mm),
            "Einsatzhoehe": max(20.0, float(box.ez) * HOEHENEINHEIT_MM),
            "Wandstaerke": float(projekt.schublade.wandstaerke_mm),
            "Fuesse": 1,
            "Verbinder_Spiel": float(projekt.schublade.verbinder_spiel_mm),
            "Max_Segmentmass": min(250.0, float(projekt.schublade.bauraum_mm[0]) - 6.0),
        }
    )
    if plan.ungueltig:
        fehler.append("%s: %s" % (box.name or box.id, "; ".join(plan.hinweise)))
    else:
        hinweise.append(
            "%s wird als Bestecksortierer in %d Segment(e) geteilt, nicht als Gridfinity-Box."
            % (box.name or box.id, len(plan.segmente))
        )


def plan_ansicht(projekt: Projekt) -> dict:
    if projekt.nur_kabel:
        return _kabel_ansicht(projekt.kabel)
    if projekt.nur_ersatz:
        return _ersatz_ansicht(projekt.ersatzteile)
    plan = plan_berechnen(projekt.schublade)
    pruefung = layout_pruefen(projekt, plan)
    ox, oy = raster_ursprung_mm(projekt.schublade, plan)
    platten = []
    for index, platte in enumerate(plan.platten, 1):
        lage = platte_lage_mm(projekt.schublade, plan, platte)
        platten.append(
            {
                "id": "P%d" % index,
                "einheiten_x": platte.einheiten_x,
                "einheiten_y": platte.einheiten_y,
                "pos_x": platte.pos_einheit_x,
                "pos_y": platte.pos_einheit_y,
                "rand_links": platte.rand_x_links,
                "rand_rechts": platte.rand_x_rechts,
                "rand_vorne": platte.rand_y_vorne,
                "rand_hinten": platte.rand_y_hinten,
                "breite_mm": platte.breite_mm,
                "tiefe_mm": platte.tiefe_mm,
                "passt_in_bauraum": platte.passt_in_bauraum,
                "lage": lage,
                "hinweis": platte.hinweis,
            }
        )
    verbinder = []
    for item in verbinder_liste(plan):
        verbinder.append(
            {
                **item,
                "x_mm": round(ox + item["x_zelle"] * RASTER_MM, 3),
                "y_mm": round(oy + item["y_zelle"] * RASTER_MM, 3),
            }
        )
    frei = []
    if not plan.ungueltig:
        frei = [{"x": x, "y": y} for x, y in freie_zellen(projekt.boxen, plan.einheiten_x, plan.einheiten_y)]
    return {
        "ok": pruefung["ok"],
        "fehler": pruefung["fehler"],
        "hinweise": list(plan.hinweise) + pruefung["hinweise"],
        "kollisionen": pruefung["kollisionen"],
        "text": plan_als_text(plan),
        "ungueltig": plan.ungueltig,
        "nutz_x": plan.nutz_x,
        "nutz_y": plan.nutz_y,
        "einheiten_x": plan.einheiten_x,
        "einheiten_y": plan.einheiten_y,
        "rest_x": plan.rest_x,
        "rest_y": plan.rest_y,
        "raster_mm": plan.raster_mm,
        "plattenhoehe_mm": plan.plattenhoehe_mm,
        "randstreifen": [asdict(s) for s in plan.randstreifen],
        "randstreifen_geometrie": True,
        "randstreifen_hinweis": (
            "Randstreifen werden als glatte Füllplatten in Plattenhöhe erzeugt. "
            "Sie haben keine Verbinder und werden lose eingelegt; die Passung ist ungeprüft."
            if plan.randstreifen
            else ""
        ),
        "ursprung_x_mm": ox,
        "ursprung_y_mm": oy,
        "platten": platten,
        "verbinder": verbinder,
        "verbinder_anzahl": len(verbinder),
        "freie_zellen": frei,
        "belegte_zellen": plan.einheiten_x * plan.einheiten_y - len(frei) if not plan.ungueltig else 0,
        "zellen_gesamt": plan.einheiten_x * plan.einheiten_y,
        "boxen_mm": [
            {"id": b.id, "name": b.name, "links_mm": r[0], "vorne_mm": r[1], "breite_mm": r[2], "tiefe_mm": r[3]}
            for b in projekt.boxen
            for r in [box_rechteck_mm(b, ox, oy)]
        ],
        "eigene_mm": [
            {"id": e.id, "name": e.name, "links_mm": r[0], "vorne_mm": r[1], "breite_mm": r[2], "tiefe_mm": r[3]}
            for e in projekt.eigene
            for r in [eigenteil_rechteck_mm(e)]
            if r is not None
        ],
    }


def bauteil_sollgroesse(part: dict) -> tuple[float, float, float] | None:
    soll = part.get("soll_mm")
    if not soll:
        return None
    return (float(soll[0]), float(soll[1]), float(soll[2]))


def _eigen_lage(eigen: Eigenteil, projekt: Projekt) -> dict | None:
    rect = eigenteil_rechteck_mm(eigen)
    if rect is None:
        return None
    return {
        "links_mm": round(rect[0], 3),
        "vorne_mm": round(rect[1], 3),
        "mitte_x_mm": round(rect[0] + rect[2] / 2.0, 3),
        "mitte_y_mm": round(rect[1] + rect[3] / 2.0, 3),
        "z_mm": round(float(projekt.schublade.boden_platte_mm), 3),
        "drehung": int(eigen.drehung) % 360,
    }


def auftrag_bauen(projekt: Projekt) -> dict:
    """Beschreibt alle Körper, ohne sie zu erzeugen."""
    if projekt.nur_kabel:
        ansicht = _kabel_ansicht(projekt.kabel)
        if not ansicht["ok"]:
            return {"ok": False, "fehler": ansicht["fehler"], "ansicht": ansicht, "teile": []}
        teile = []
        for teil in projekt.kabel:
            for stueck in kabel_stuecke(teil):
                teile.append(
                    {
                        "id": stueck["id"],
                        "rolle": "kabel",
                        "name": stueck["name"],
                        "params": stueck["params"],
                        "soll_mm": [round(float(v), 3) for v in stueck["soll"]],
                        "lage": None,
                        "anzahl": 1,
                        "passt_in_bauraum": True,
                    }
                )
        return {"ok": True, "fehler": [], "ansicht": ansicht, "teile": teile}
    if projekt.nur_ersatz:
        ansicht = _ersatz_ansicht(projekt.ersatzteile)
        if not ansicht["ok"]:
            return {"ok": False, "fehler": ansicht["fehler"], "ansicht": ansicht, "teile": []}
        teile = []
        for teil in projekt.ersatzteile:
            params = dict(teil.get("parameter") or {})
            params["art"] = teil.get("art")
            soll = ersatz_masse(teil.get("art"), params)
            teile.append(
                {
                    "id": teil.get("id") or "ET",
                    "rolle": "ersatzteil",
                    "name": teil.get("name") or teil.get("art"),
                    "params": params,
                    "soll_mm": [round(v, 3) for v in soll],
                    "lage": None,
                    "anzahl": 1,
                    "passt_in_bauraum": True,
                }
            )
        return {"ok": True, "fehler": [], "ansicht": ansicht, "teile": teile}
    if projekt.nur_eigene:
        fehler = layout_pruefen(projekt)["fehler"]
        ansicht = {
            "fehler": fehler, "ungueltig": False, "hinweise": [], "randstreifen": [], "platten": [],
            "verbinder_anzahl": 0, "einheiten_x": 0, "einheiten_y": 0,
        }
        if fehler:
            return {"ok": False, "fehler": fehler, "ansicht": ansicht, "teile": []}
        teile = [
            {
                "id": e.id, "rolle": "eigen", "name": e.name,
                "params": eigen_params(e),
                "soll_mm": None, "lage": None, "anzahl": int(e.anzahl), "passt_in_bauraum": True,
            }
            for e in projekt.eigene
        ]
        return {"ok": True, "fehler": [], "ansicht": ansicht, "teile": teile}
    ansicht = plan_ansicht(projekt)
    if ansicht["ungueltig"] or ansicht["fehler"]:
        return {
            "ok": False,
            "fehler": ansicht["fehler"] or ansicht["hinweise"],
            "ansicht": ansicht,
            "teile": [],
        }
    teile = []
    for platte in ansicht["platten"]:
        params = default_params(
            Einheiten_X=platte["einheiten_x"],
            Einheiten_Y=platte["einheiten_y"],
            Rand_X_links=platte["rand_links"],
            Rand_X_rechts=platte["rand_rechts"],
            Rand_Y_vorne=platte["rand_vorne"],
            Rand_Y_hinten=platte["rand_hinten"],
            Verbinder_Spiel=float(projekt.schublade.verbinder_spiel_mm),
            Bodenstaerke_Platte=float(projekt.schublade.boden_platte_mm),
            Wandstaerke=float(projekt.schublade.wandstaerke_mm),
            Verbinder=1,
            Verriegelung=1,
        )
        teile.append(
            {
                "id": platte["id"],
                "rolle": "grundplatte",
                "name": "Grundplatte %d×%d" % (platte["einheiten_x"], platte["einheiten_y"]),
                "params": params,
                "soll_mm": [
                    platte["breite_mm"],
                    platte["tiefe_mm"],
                    round(plattenhoehe(float(projekt.schublade.boden_platte_mm)), 3),
                ],
                "lage": platte["lage"],
                "anzahl": 1,
                "passt_in_bauraum": platte["passt_in_bauraum"],
            }
        )
    for box in projekt.boxen:
        x, y, ex, ey = footprint(box)
        fx, fy = faecher_orientiert(box)
        if box.art == "besteck":
            teile.append(
                {
                    "id": box.id,
                    "rolle": "besteck",
                    "name": box.name,
                    "params": {
                        "Schubladenbreite": ex * RASTER_MM,
                        "Schubladentiefe": ey * RASTER_MM,
                        "Schubladenspiel": 0.0,
                        "Verfuegbare_Hoehe": float(projekt.schublade.nutzhoehe_mm),
                        "Einsatzhoehe": max(20.0, float(box.ez) * HOEHENEINHEIT_MM),
                        "Wandstaerke": float(projekt.schublade.wandstaerke_mm),
                        "Fuesse": 1,
                        "Verbinder_Spiel": float(projekt.schublade.verbinder_spiel_mm),
                        "Max_Segmentmass": min(250.0, float(projekt.schublade.bauraum_mm[0]) - 6.0),
                        "Zellen_X": ex,
                        "Zellen_Y": ey,
                        "Zelle_X": x,
                        "Zelle_Y": y,
                    },
                    "soll_mm": None,
                    "lage": {
                        "links_mm": round(ansicht["ursprung_x_mm"] + x * RASTER_MM, 3),
                        "vorne_mm": round(ansicht["ursprung_y_mm"] + y * RASTER_MM, 3),
                        "mitte_x_mm": round(ansicht["ursprung_x_mm"] + (x + ex / 2.0) * RASTER_MM, 3),
                        "mitte_y_mm": round(ansicht["ursprung_y_mm"] + (y + ey / 2.0) * RASTER_MM, 3),
                    },
                    "anzahl": 1,
                    "passt_in_bauraum": True,
                }
            )
            continue
        params = default_params(
            Einheiten_X=ex,
            Einheiten_Y=ey,
            Einheiten_Z=int(box.ez),
            Fachanzahl_X=fx,
            Fachanzahl_Y=fy,
            Stapellippe=1 if box.stapellippe or box.deckel else 0,
            Wandstaerke=float(projekt.schublade.wandstaerke_mm),
            Verbinder_Spiel=float(projekt.schublade.verbinder_spiel_mm),
            Verbinder=0,
            Verriegelung=0,
            Bodenstaerke_Platte=float(projekt.schublade.boden_platte_mm),
        )
        if box.deckel or box.herausnehmbar or box.kabelkerben:
            params = dict(params)
            params["Deckel"] = 1 if box.deckel else 0
            params["Herausnehmbare_Trennwaende"] = 1 if box.herausnehmbar else 0
            params["Kabelkerben"] = 1 if box.kabelkerben else 0
            # Verriegelungsart 1 und 2 erzwingen in make_phase4_box die Stapellippe.
            # Ohne gewünschte Lippe bleibt Art 0, sonst weicht die Sollhöhe vom Körper ab.
            if box.deckel:
                params["Verriegelungsart"] = 2
                params["Stapellippe"] = 1
            elif params["Stapellippe"]:
                params["Verriegelungsart"] = 1
            else:
                params["Verriegelungsart"] = 0
            rolle = "phase4"
        else:
            rolle = "box"
        teile.append(
            {
                "id": box.id,
                "rolle": rolle,
                "name": box.name,
                "params": params,
                "soll_mm": [
                    round(kasten_aussen(ex, 0.0), 3),
                    round(kasten_aussen(ey, 0.0), 3),
                    round(box_hoehe(int(box.ez), bool(params["Stapellippe"])), 3),
                ],
                "lage": {
                    "links_mm": round(ansicht["ursprung_x_mm"] + x * RASTER_MM + 0.25, 3),
                    "vorne_mm": round(ansicht["ursprung_y_mm"] + y * RASTER_MM + 0.25, 3),
                    "mitte_x_mm": round(ansicht["ursprung_x_mm"] + (x + ex / 2.0) * RASTER_MM, 3),
                    "mitte_y_mm": round(ansicht["ursprung_y_mm"] + (y + ey / 2.0) * RASTER_MM, 3),
                    "z_mm": round(float(projekt.schublade.boden_platte_mm), 3),
                },
                "anzahl": 1,
                "passt_in_bauraum": True,
                "deckel": bool(box.deckel),
            }
        )
    for nr, streifen in enumerate(ansicht["randstreifen"], 1):
        stuecke = max(1, int(streifen["teile"]))
        laenge = round(float(streifen["laenge_mm"]) / stuecke, 3)
        breite = round(float(streifen["breite_mm"]), 3)
        hoehe = round(plattenhoehe(float(projekt.schublade.boden_platte_mm)), 3)
        teile.append(
            {
                "id": "S%d" % nr,
                "rolle": "eigen",
                "name": "Randstreifen %d" % nr,
                "params": {
                    "Hoehe": hoehe,
                    "Boden": 0.0,
                    "Formen": [{"typ": "rechteck", "x": 0.0, "y": 0.0, "b": breite, "t": laenge, "loch": False}],
                },
                "soll_mm": [breite, laenge, hoehe],
                "lage": None,
                "anzahl": stuecke,
                "passt_in_bauraum": breite <= BAURAUM_X and laenge <= BAURAUM_Y,
            }
        )
    for eigen in projekt.eigene:
        teile.append(
            {
                "id": eigen.id,
                "rolle": "eigen",
                "name": eigen.name,
                "params": eigen_params(eigen),
                "soll_mm": None,
                "lage": _eigen_lage(eigen, projekt),
                "anzahl": int(eigen.anzahl),
                "passt_in_bauraum": True,
            }
        )
    if ansicht["verbinder_anzahl"]:
        teile.append(
            {
                "id": "V",
                "rolle": "verbinder",
                "name": "Plattenverbinder",
                "params": default_params(
                    Verbinder_Spiel=float(projekt.schublade.verbinder_spiel_mm),
                    Bodenstaerke_Platte=float(projekt.schublade.boden_platte_mm),
                ),
                "soll_mm": None,
                "lage": None,
                "anzahl": ansicht["verbinder_anzahl"],
                "positionen": ansicht["verbinder"],
                "passt_in_bauraum": True,
            }
        )
    teile.append(
        {
            "id": "R",
            "rolle": "rastclip",
            "name": "Rastclip",
            "params": default_params(
                Einheiten_Z=3,
                Stapellippe=1,
                Bodenstaerke_Platte=float(projekt.schublade.boden_platte_mm),
            ),
            "soll_mm": None,
            "lage": None,
            "anzahl": max(4, 4 * len(ansicht["platten"])),
            "anzahl_ist_vorschlag": True,
            "passt_in_bauraum": True,
        }
    )
    for teil in teile:
        soll = teil.get("soll_mm")
        if soll and (soll[0] > BAURAUM_X + 1e-6 or soll[1] > BAURAUM_Y + 1e-6 or soll[2] > BAURAUM_Z + 1e-6):
            teil["passt_in_bauraum"] = False
    return {"ok": True, "fehler": [], "ansicht": ansicht, "teile": teile}


def projekt_speichern(projekt: Projekt, pfad: Path) -> None:
    import json

    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(projekt.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def projekt_laden(pfad: Path) -> Projekt:
    import json

    data = json.loads(Path(pfad).read_text(encoding="utf-8"))
    return Projekt.from_dict(data)
