# -*- coding: utf-8 -*-
"""Eigene Vorlagen: gezeichnete Teile, die als Startpunkt für neue Teile gespeichert werden.

Die Vorlagen liegen in ``vorlagen.json`` im Programmordner des Benutzers (neben den Einstellungen).
Nur gültige Teile lassen sich speichern. Position in der Schublade wird nicht mitgespeichert.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from sidecar.eigenteil import Eigenteil, eigenteil_pruefen
from sidecar.paths import app_home

MAX_VORLAGEN = 200
MAX_NAME = 60


def _pfad() -> Path:
    return app_home() / "vorlagen.json"


def vorlagen_laden() -> list[dict]:
    """Liste der gespeicherten Vorlagen. Eine fehlende oder beschädigte Datei ergibt eine leere Liste."""
    pfad = _pfad()
    if not pfad.is_file():
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(daten, list):
        return []
    ergebnis = []
    for eintrag in daten:
        if isinstance(eintrag, dict) and isinstance(eintrag.get("id"), str) and isinstance(eintrag.get("teil"), dict):
            ergebnis.append({"id": eintrag["id"], "name": str(eintrag.get("name") or "Vorlage"), "teil": eintrag["teil"]})
    return ergebnis


def _schreiben(liste: list[dict]) -> None:
    pfad = _pfad()
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(liste, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def vorlage_speichern(name: str, teil: dict, bauraum_mm=(256.0, 256.0, 256.0)) -> list[dict]:
    """Speichert ein Teil als Vorlage. Gleicher Name ersetzt die vorhandene Vorlage."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Die Vorlage braucht einen Namen.")
    if len(name) > MAX_NAME:
        raise ValueError("Der Name darf höchstens %d Zeichen haben." % MAX_NAME)
    eigen = Eigenteil.from_dict({**(teil or {}), "id": "V", "platziert": False, "x_mm": 0.0, "y_mm": 0.0, "drehung": 0})
    fehler = eigenteil_pruefen(eigen, bauraum_mm)
    if fehler:
        raise ValueError("Das Teil ist noch nicht gültig: " + " ".join(fehler))
    inhalt = eigen.to_dict()
    inhalt.pop("id", None)
    inhalt["name"] = name
    liste = vorlagen_laden()
    for eintrag in liste:
        if eintrag["name"].casefold() == name.casefold():
            eintrag["teil"] = inhalt
            break
    else:
        if len(liste) >= MAX_VORLAGEN:
            raise ValueError("Es sind höchstens %d Vorlagen möglich." % MAX_VORLAGEN)
        liste.append({"id": "v-" + uuid.uuid4().hex[:8], "name": name, "teil": inhalt})
    _schreiben(liste)
    return liste


def vorlage_loeschen(vorlage_id: str) -> list[dict]:
    liste = [e for e in vorlagen_laden() if e["id"] != vorlage_id]
    _schreiben(liste)
    return liste
