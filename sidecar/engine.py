# -*- coding: utf-8 -*-
"""Auftragserzeugung, FreeCAD-Sitzung und Projektdateien.

Erfolg gibt es nur, wenn jede Exportdatei existiert und die Mesh-Prüfung
sowie das erneute Laden der FCStd-Datei bestanden haben.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

from sidecar.detect_freecad import detect, freecad_command
from sidecar.layout import (
    Projekt,
    auftrag_bauen,
    plan_ansicht,
    projekt_laden,
    projekt_speichern,
)
from sidecar.montage import _masse_g, schreibe_stueckliste, schreibe_uebersicht
from sidecar.paths import HAUSRASTER_SRC, ROOT, app_home
from sidecar.stlcheck import pruefe_stl


def _settings_path() -> Path:
    return app_home() / "settings.json"


def settings_laden() -> dict:
    pfad = _settings_path()
    daten = {
        "freecad_pfad": "",
        "material": "PLA",
        "schubladenspiel_mm": 1.0,
        "verbinder_spiel_mm": 0.20,
        "wandstaerke_mm": 1.2,
        "boden_platte_mm": 0.8,
        "bauraum_mm": [256, 256, 256],
        "nutzhoehe_mm": 80,
    }
    if pfad.is_file():
        daten.update(json.loads(pfad.read_text(encoding="utf-8")))
    return daten


def settings_speichern(daten: dict) -> dict:
    aktuell = settings_laden()
    aktuell.update(daten or {})
    _settings_path().write_text(json.dumps(aktuell, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return aktuell


def _recent_path() -> Path:
    return app_home() / "recent.json"


def recent_liste() -> list[dict]:
    pfad = _recent_path()
    if not pfad.is_file():
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    vorhanden = []
    for eintrag in daten:
        if eintrag.get("pfad") and Path(eintrag["pfad"]).is_file():
            vorhanden.append(eintrag)
    return vorhanden


def recent_merken(pfad: Path, name: str) -> list[dict]:
    eintrag = {"pfad": str(Path(pfad).resolve()), "name": name, "geaendert": time.strftime("%Y-%m-%dT%H:%M:%S")}
    alt = [e for e in recent_liste() if e.get("pfad") != eintrag["pfad"]]
    neu = [eintrag, *alt][:8]
    _recent_path().write_text(json.dumps(neu, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return neu


class FreeCADSession:
    def __init__(self, befehl: list[str]):
        self.befehl = befehl
        self.proc = None
        self.sock = None
        self.datei = None
        self.portfile = None

    def start(self, timeout: float = 180.0):
        import tempfile

        handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="cadstudio-port-", suffix=".txt")
        self.portfile = Path(handle.name)
        handle.close()
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        env["CADSTUDIO_SRC"] = str(HAUSRASTER_SRC)
        env["CADSTUDIO_ROOT"] = str(ROOT)
        env["CADSTUDIO_PORTFILE"] = str(self.portfile)
        worker = ROOT / "sidecar" / "fc_worker.py"
        bootstrap = (
            "import os, runpy\n"
            "runpy.run_path(os.environ['CADSTUDIO_WORKER'], run_name='__main__')\n"
        )
        env["CADSTUDIO_WORKER"] = str(worker)
        self.proc = subprocess.Popen(
            self.befehl,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )
        self._log: list[bytes] = []

        def _lesen():
            try:
                if not self.proc or not self.proc.stdout:
                    return
                for zeile in self.proc.stdout:
                    self._log.append(zeile)
                    if len(self._log) > 400:
                        del self._log[:-200]
            except (ValueError, OSError):
                return

        threading.Thread(target=_lesen, daemon=True).start()
        assert self.proc.stdin is not None
        self.proc.stdin.write(bootstrap.encode("utf-8"))
        self.proc.stdin.close()
        deadline = time.time() + timeout
        port = None
        while time.time() < deadline:
            if self.proc.poll() is not None:
                rest = b"".join(self._log).decode("utf-8", errors="replace")
                raise RuntimeError("FreeCADCmd wurde beendet, bevor der Worker bereit war.\n" + rest[-4000:])
            if self.portfile.is_file():
                text = self.portfile.read_text(encoding="utf-8").strip()
                if text.isdigit():
                    port = int(text)
                    break
            time.sleep(0.2)
        if port is None:
            raise TimeoutError("FreeCADCmd hat nicht rechtzeitig geantwortet.")
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=30)
        self.sock.settimeout(None)
        self.datei = self.sock.makefile("rwb")
        ping = self.request({"cmd": "ping"}, timeout=180)
        if not ping.get("ok"):
            raise RuntimeError(ping.get("fehler") or "FreeCAD-Ping fehlgeschlagen")
        return ping["result"]

    def request(self, payload: dict, timeout: float = 1200.0) -> dict:
        if self.datei is None:
            raise RuntimeError("Keine FreeCAD-Sitzung.")
        self.sock.settimeout(timeout)
        self.datei.write(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
        self.datei.flush()
        zeile = self.datei.readline()
        if not zeile:
            raise RuntimeError("FreeCAD-Worker hat die Verbindung geschlossen.")
        return json.loads(zeile.decode("utf-8"))

    def close(self):
        try:
            if self.datei:
                self.request({"cmd": "shutdown"}, timeout=30)
        except Exception:
            pass
        try:
            if self.datei:
                self.datei.close()
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.portfile and self.portfile.exists():
            try:
                self.portfile.unlink()
            except OSError:
                pass


def freecad_befehl(user_path: str | None = None) -> tuple[list[str] | None, dict]:
    info = detect(user_path=user_path or None, probe=True)
    if not info.get("gefunden"):
        return None, info
    return freecad_command(Path(info["pfad"])), info


def generiere(projekt: Projekt, out_dir: Path, freecad_pfad: str | None = None, status_file: Path | None = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    auftrag = auftrag_bauen(projekt)
    if not auftrag["ok"]:
        ergebnis = {
            "ok": False,
            "fehler": auftrag["fehler"],
            "hinweis": "Es wurde nichts als erfolgreich exportiert.",
            "teile": [],
        }
        (out_dir / "manifest.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ergebnis
    for teil in auftrag["teile"]:
        if teil.get("passt_in_bauraum") is False:
            ergebnis = {
                "ok": False,
                "fehler": ["%s passt nicht in den Bauraum des Druckers." % teil["name"]],
                "teile": [],
            }
            (out_dir / "manifest.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return ergebnis

    befehl, info = freecad_befehl(freecad_pfad or settings_laden().get("freecad_pfad") or None)
    if not befehl:
        ergebnis = {
            "ok": False,
            "fehler": [info.get("hinweis") or "FreeCAD fehlt."],
            "freecad": info,
            "teile": [],
        }
        (out_dir / "manifest.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ergebnis

    session = FreeCADSession(befehl)
    try:
        version = session.start()
        if not str(version.get("freecad", "")).startswith("1.1"):
            return {
                "ok": False,
                "fehler": ["FreeCAD %s ist nicht 1.1.x." % version.get("freecad")],
                "teile": [],
            }
        roh = session.request(
            {
                "cmd": "build_all",
                "teile": auftrag["teile"],
                "out_dir": str(out_dir),
                "status_file": str(status_file) if status_file else "",
            },
            timeout=3600,
        )
    finally:
        session.close()

    if not roh.get("ok"):
        ergebnis = {"ok": False, "fehler": [roh.get("fehler") or "FreeCAD-Auftrag fehlgeschlagen"], "teile": [], "freecad": info}
        (out_dir / "manifest.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ergebnis

    gebaut = roh["result"]
    teile_ausgabe = []
    fehler = []
    if not gebaut.get("ok"):
        fehler.append("Mindestens ein Körper wurde nicht gültig erzeugt.")
    for teil in gebaut.get("teile") or []:
        if not teil.get("ok"):
            fehler.extend(teil.get("fehler") or ["%s fehlgeschlagen" % teil.get("id")])
            if teil.get("trace"):
                fehler.append(teil["trace"][-1500:])
        dateien_ok = []
        for datei in teil.get("dateien") or []:
            stl = datei.get("stl")
            pruefung = None
            if stl and Path(stl).is_file():
                pruefung = pruefe_stl(stl, soll_groesse=tuple(datei["soll_mm"]) if datei.get("soll_mm") else None)
                datei["mesh_unabhaengig"] = {k: pruefung[k] for k in ("ok", "wasserdicht", "mannigfaltig", "bbox_mm", "volumen_mm3", "fehler", "dreiecke")}
                if not pruefung["ok"]:
                    fehler.append("%s: %s" % (datei.get("id"), pruefung.get("fehler") or "unabhängige Mesh-Prüfung fehlgeschlagen"))
                    datei["ok"] = False
            else:
                datei["ok"] = False
                fehler.append("%s: STL fehlt." % datei.get("id"))
            fcstd = datei.get("fcstd")
            if not fcstd or not Path(fcstd).is_file() or Path(fcstd).stat().st_size < 200:
                datei["ok"] = False
                fehler.append("%s: FCStd fehlt." % datei.get("id"))
            if not datei.get("fcstd_erneut_geladen", {}).get("ok"):
                datei["ok"] = False
            dateien_ok.append(datei)
        teil["dateien"] = dateien_ok
        teil["ok"] = bool(teil.get("ok")) and all(d.get("ok") for d in dateien_ok) and len(dateien_ok) > 0
        if not teil["ok"] and not teil.get("fehler"):
            fehler.append("%s hat die Exportprüfung nicht bestanden." % teil.get("id"))
        teile_ausgabe.append(teil)

    ok = not fehler and all(t.get("ok") for t in teile_ausgabe)
    stueck = []
    for teil in teile_ausgabe:
        for datei in teil.get("dateien") or []:
            solid = datei.get("solid") or {}
            bbox = solid.get("bbox_mm") or [None, None, None]
            masse = _masse_g(float(solid.get("volume_mm3") or 0), projekt.schublade.material)
            stueck.append(
                {
                    "Teil": datei.get("id"),
                    "Bezeichnung": "%s (%s)" % (teil.get("name") or "", datei.get("name") or ""),
                    "Anzahl": teil.get("anzahl", 1) if datei.get("name") in ("Plattenverbinder", "Rastclip", "Grundplatte", "Box") or teil["rolle"] not in ("verbinder", "rastclip") else 1,
                    "Breite_mm": None if bbox[0] is None else round(bbox[0], 2),
                    "Tiefe_mm": None if bbox[1] is None else round(bbox[1], 2),
                    "Hoehe_mm": None if bbox[2] is None else round(bbox[2], 2),
                    "Material": projekt.schublade.material,
                    "Masse_geschaetzt_g": masse if masse is not None else "",
                    "Bauraum": "ja" if (bbox[0] or 0) <= 256 and (bbox[1] or 0) <= 256 and (bbox[2] or 0) <= 256 else "nein",
                    "STL": datei.get("stl") or "",
                    "FCStd": datei.get("fcstd") or "",
                    "Pruefung": "bestanden" if datei.get("ok") else "fehlgeschlagen",
                }
            )
    # Verbinder und Rastclip: Anzahl aus dem Auftrag, nicht je Datei 1
    for zeile in stueck:
        for teil in teile_ausgabe:
            if zeile["Teil"] == teil["id"] or str(zeile["Teil"]).startswith(str(teil["id"]) + "_"):
                if teil["rolle"] in ("verbinder", "rastclip") and zeile["Teil"] == teil["id"]:
                    zeile["Anzahl"] = teil.get("anzahl", 1)
    hinweise = list(auftrag["ansicht"].get("hinweise") or [])
    if auftrag["ansicht"].get("randstreifen"):
        hinweise.append(auftrag["ansicht"].get("randstreifen_hinweis") or "")
    hinweise.append("Masse in Gramm ist eine Schätzung über das CAD-Volumen, kein gewogenes Teil.")
    if any(t.get("anzahl_ist_vorschlag") for t in teile_ausgabe):
        hinweise.append("Die Anzahl der Rastclips ist ein Vorschlag, keine gemessene Empfehlung.")

    schreibe_stueckliste(out_dir / "Stueckliste.json", out_dir / "Stueckliste.csv", stueck, hinweise)
    if projekt.nur_eigene:
        uebersicht = {}
    else:
        boxen_zeichnung = _boxen_zeichnung(projekt, auftrag["ansicht"])
        uebersicht = schreibe_uebersicht(
            out_dir,
            projekt.name,
            {
                "innenbreite_mm": projekt.schublade.innenbreite_mm,
                "innentiefe_mm": projekt.schublade.innentiefe_mm,
                "nutzhoehe_mm": projekt.schublade.nutzhoehe_mm,
                "spiel_mm": projekt.schublade.spiel_mm,
            },
            auftrag["ansicht"],
            boxen_zeichnung,
            hinweise,
        )
    ergebnis = {
        "ok": ok,
        "fehler": fehler,
        "freecad": {"pfad": info.get("pfad"), "version": version.get("freecad"), "hausraster": version.get("hausraster")},
        "teile": teile_ausgabe,
        "stueckliste": str(out_dir / "Stueckliste.json"),
        "montage": uebersicht,
        "hinweise": hinweise,
        "ansicht": {
            "einheiten_x": auftrag["ansicht"]["einheiten_x"],
            "einheiten_y": auftrag["ansicht"]["einheiten_y"],
            "platten": len(auftrag["ansicht"]["platten"]),
            "verbinder": auftrag["ansicht"]["verbinder_anzahl"],
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ergebnis


def _boxen_zeichnung(projekt: Projekt, ansicht: dict) -> list[dict]:
    from sidecar.layout import footprint
    from hausraster_const import RASTER_MM, kasten_aussen

    zeilen = []
    for box in projekt.boxen:
        x, y, ex, ey = footprint(box)
        if box.art == "besteck":
            breite = ex * RASTER_MM
            tiefe = ey * RASTER_MM
            links = ansicht["ursprung_x_mm"] + x * RASTER_MM
            vorne = ansicht["ursprung_y_mm"] + y * RASTER_MM
        else:
            breite = kasten_aussen(ex, 0.0)
            tiefe = kasten_aussen(ey, 0.0)
            links = ansicht["ursprung_x_mm"] + x * RASTER_MM + 0.25
            vorne = ansicht["ursprung_y_mm"] + y * RASTER_MM + 0.25
        zeilen.append(
            {
                "id": box.id,
                "name": box.name,
                "links_mm": links,
                "vorne_mm": vorne,
                "breite_mm": breite,
                "tiefe_mm": tiefe,
            }
        )
    return zeilen


def externe_dateipruefung(freecad_pfad: str | None, dateien: list[dict]) -> dict:
    """Zweiter FreeCAD-Prozess, der die gespeicherten Dateien nur lädt."""
    befehl, info = freecad_befehl(freecad_pfad)
    if not befehl:
        return {"ok": False, "fehler": info.get("hinweis"), "dateien": []}
    session = FreeCADSession(befehl)
    try:
        session.start()
        antwort = session.request({"cmd": "verify_files", "dateien": dateien}, timeout=1200)
    finally:
        session.close()
    if not antwort.get("ok"):
        return {"ok": False, "fehler": antwort.get("fehler"), "dateien": []}
    return antwort["result"]


def plane(projekt_dict: dict) -> dict:
    projekt = Projekt.from_dict(projekt_dict)
    return plan_ansicht(projekt)


def projekt_ziel(pfad: str, name: str) -> Path:
    """Leere und relative Pfade liegen im Benutzerordner, nicht im Programmordner."""
    ordner = app_home() / "projekte"
    ordner.mkdir(parents=True, exist_ok=True)
    text = (pfad or "").strip()
    if not text:
        basis = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (name or ""))
        basis = basis.strip("_") or "schublade"
        return ordner / ("%s.cadstudio.json" % basis)
    ziel = Path(text)
    if not ziel.is_absolute():
        ziel = ordner / ziel
    return ziel


def speichere_und_merke(projekt_dict: dict, pfad: str) -> dict:
    projekt = Projekt.from_dict(projekt_dict)
    ziel = projekt_ziel(pfad, projekt.name)
    projekt_speichern(projekt, ziel)
    recent_merken(ziel, projekt.name)
    return {"ok": True, "pfad": str(ziel.resolve())}


def lade_und_merke(pfad: str) -> dict:
    ziel = Path(pfad)
    projekt = projekt_laden(ziel)
    recent_merken(ziel, projekt.name)
    return {"ok": True, "pfad": str(ziel.resolve()), "projekt": projekt.to_dict()}
