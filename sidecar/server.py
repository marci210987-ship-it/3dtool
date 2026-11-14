# -*- coding: utf-8 -*-
"""Lokaler HTTP-Dienst für die Oberfläche. Kein Netz nach außen."""

from __future__ import annotations

import json
import os
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sidecar.detect_freecad import detect
from sidecar.engine import (
    generiere,
    lade_und_merke,
    plane,
    recent_liste,
    settings_laden,
    settings_speichern,
    speichere_und_merke,
)
from sidecar.layout import Projekt
from sidecar.paths import app_home


JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
ERLAUBTE_DATEIEN: set[Path] = set()
ERLAUBTE_URSPRUNGE = {
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
}
TOKEN = ""


def sitzungstoken() -> str:
    global TOKEN
    if TOKEN:
        return TOKEN
    TOKEN = os.environ.get("CADSTUDIO_TOKEN") or secrets.token_hex(16)
    ziel = app_home() / "sitzung.token"
    ziel.write_text(TOKEN + "\n", encoding="utf-8")
    try:
        os.chmod(ziel, 0o600)
    except OSError:
        pass
    return TOKEN


def _ursprung_ok(handler: BaseHTTPRequestHandler) -> bool:
    ursprung = handler.headers.get("Origin")
    if not ursprung:
        return True
    return ursprung in ERLAUBTE_URSPRUNGE


def _token_ok(handler: BaseHTTPRequestHandler) -> bool:
    erwartet = sitzungstoken()
    geliefert = handler.headers.get("X-CADStudio-Token") or ""
    if not geliefert:
        werte = parse_qs(urlparse(handler.path).query).get("token") or []
        geliefert = werte[0] if werte else ""
    if len(geliefert) != len(erwartet):
        return False
    return secrets.compare_digest(geliefert, erwartet)


def _cors(handler: BaseHTTPRequestHandler) -> None:
    ursprung = handler.headers.get("Origin")
    if ursprung and ursprung in ERLAUBTE_URSPRUNGE:
        handler.send_header("Access-Control-Allow-Origin", ursprung)
        handler.send_header("Vary", "Origin")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-CADStudio-Token")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")


def _json(handler: BaseHTTPRequestHandler, code: int, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(data)


def _verboten(handler: BaseHTTPRequestHandler):
    _json(handler, 403, {"ok": False, "fehler": "Dieser Aufruf ist nicht erlaubt."})


def _registrieren(ergebnis: dict):
    for teil in ergebnis.get("teile") or []:
        for datei in teil.get("dateien") or []:
            for key in ("stl", "fcstd"):
                if datei.get(key):
                    ERLAUBTE_DATEIEN.add(Path(datei[key]).resolve())
    montage = ergebnis.get("montage") or {}
    for key in ("svg", "html", "png", "pdf"):
        if montage.get(key):
            ERLAUBTE_DATEIEN.add(Path(montage[key]).resolve())
    if ergebnis.get("stueckliste"):
        ERLAUBTE_DATEIEN.add(Path(ergebnis["stueckliste"]).resolve())
        csv_pfad = Path(ergebnis["stueckliste"]).with_suffix(".csv")
        if csv_pfad.is_file():
            ERLAUBTE_DATEIEN.add(csv_pfad.resolve())


def _job_starten(projekt_dict: dict, out_dir: str, freecad_pfad: str | None) -> str:
    job_id = uuid.uuid4().hex[:12]
    status = app_home() / "jobs" / ("%s.json" % job_id)
    status.parent.mkdir(parents=True, exist_ok=True)
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "laeuft", "schritt": 0, "gesamt": 0, "teil": "", "ergebnis": None}

    def lauf():
        try:
            projekt = Projekt.from_dict(projekt_dict)
            ergebnis = generiere(projekt, Path(out_dir), freecad_pfad=freecad_pfad or None, status_file=status)
            _registrieren(ergebnis)
            with JOBS_LOCK:
                JOBS[job_id] = {"status": "fertig" if ergebnis.get("ok") else "fehler", "ergebnis": ergebnis}
        except Exception as exc:
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "status": "fehler",
                    "ergebnis": {"ok": False, "fehler": [str(exc)], "teile": []},
                }

    threading.Thread(target=lauf, daemon=True).start()
    return job_id


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_OPTIONS(self):
        if not _ursprung_ok(self):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        _cors(self)
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        if not _ursprung_ok(self):
            _verboten(self)
            return
        if url.path == "/health":
            _json(self, 200, {"ok": True, "dienst": "cad-studio"})
            return
        if url.path == "/sitzung":
            _json(self, 200, {"ok": True, "token": sitzungstoken()})
            return
        if not _token_ok(self):
            _verboten(self)
            return
        if url.path == "/api/job":
            job_id = parse_qs(url.query).get("id", [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                _json(self, 404, {"ok": False, "fehler": "Auftrag unbekannt."})
                return
            status_pfad = app_home() / "jobs" / ("%s.json" % job_id)
            fortschritt = {}
            if status_pfad.is_file():
                try:
                    fortschritt = json.loads(status_pfad.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    fortschritt = {}
            _json(self, 200, {"ok": True, "job": job_id, **job, "fortschritt": fortschritt})
            return
        if url.path == "/datei":
            roh = parse_qs(url.query).get("pfad", [""])[0]
            ziel = Path(roh).resolve() if roh else None
            if ziel is None or ziel not in ERLAUBTE_DATEIEN or not ziel.is_file():
                _json(self, 404, {"ok": False, "fehler": "Datei ist nicht freigegeben."})
                return
            data = ziel.read_bytes()
            art = "application/octet-stream"
            if ziel.suffix.lower() == ".stl":
                art = "model/stl"
            elif ziel.suffix.lower() == ".html":
                art = "text/html; charset=utf-8"
            elif ziel.suffix.lower() == ".svg":
                art = "image/svg+xml"
            elif ziel.suffix.lower() == ".png":
                art = "image/png"
            elif ziel.suffix.lower() == ".pdf":
                art = "application/pdf"
            elif ziel.suffix.lower() == ".json":
                art = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", art)
            self.send_header("Content-Length", str(len(data)))
            _cors(self)
            self.end_headers()
            self.wfile.write(data)
            return
        _json(self, 404, {"ok": False, "fehler": "Unbekannter Pfad."})

    def do_POST(self):
        if not _ursprung_ok(self) or not _token_ok(self):
            _verboten(self)
            return
        url = urlparse(self.path)
        if url.path != "/api":
            _json(self, 404, {"ok": False, "fehler": "Unbekannter Pfad."})
            return
        laenge = int(self.headers.get("Content-Length") or "0")
        try:
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            _json(self, 400, {"ok": False, "fehler": "Ungültiges JSON."})
            return
        cmd = anfrage.get("cmd")
        try:
            if cmd == "detect":
                _json(self, 200, {"ok": True, "result": detect(anfrage.get("user_path") or None, probe=bool(anfrage.get("probe", True)))})
                return
            if cmd == "settings_get":
                _json(self, 200, {"ok": True, "result": settings_laden()})
                return
            if cmd == "settings_set":
                _json(self, 200, {"ok": True, "result": settings_speichern(anfrage.get("settings") or {})})
                return
            if cmd == "recent":
                _json(self, 200, {"ok": True, "result": recent_liste()})
                return
            if cmd == "plane":
                _json(self, 200, {"ok": True, "result": plane(anfrage.get("projekt") or {})})
                return
            if cmd == "vorlagen":
                from sidecar.vorlagen import vorlagen_laden

                _json(self, 200, {"ok": True, "result": vorlagen_laden()})
                return
            if cmd == "vorlage_save":
                from sidecar.vorlagen import vorlage_speichern

                _json(self, 200, {"ok": True, "result": vorlage_speichern(str(anfrage.get("name") or ""), anfrage.get("teil") or {})})
                return
            if cmd == "vorlage_delete":
                from sidecar.vorlagen import vorlage_loeschen

                _json(self, 200, {"ok": True, "result": vorlage_loeschen(str(anfrage.get("id") or ""))})
                return
            if cmd == "ersatz_katalog":
                from sidecar.ersatzteil import KATALOG

                _json(self, 200, {"ok": True, "result": KATALOG})
                return
            if cmd == "ersatz_pruefen":
                from sidecar.ersatzteil import masse as ersatz_masse, pruefe as ersatz_pruefen

                art = str(anfrage.get("art") or "")
                parameter = anfrage.get("parameter") or {}
                meldungen = ersatz_pruefen(art, parameter)
                soll = ersatz_masse(art, {**parameter, "art": art}) if not meldungen else None
                _json(self, 200, {"ok": not meldungen, "fehler": meldungen, "soll_mm": soll})
                return
            if cmd == "autofill":
                from sidecar.autofill import auto_bestuecken
                from sidecar.layout import Projekt

                projekt = Projekt.from_dict(anfrage.get("projekt") or {})
                antwort = auto_bestuecken(
                    projekt,
                    int(anfrage.get("max_zellen") or 3),
                    wuensche=anfrage.get("wuensche") or None,
                    rest_fuellen=bool(anfrage.get("rest_fuellen", True)),
                    stil=str(anfrage.get("stil") or "einheitlich"),
                )
                _json(self, 200, {"ok": antwort["ok"], "fehler": "; ".join(antwort["fehler"]), "result": antwort, "projekt": projekt.to_dict()})
                return
            if cmd == "save":
                _json(self, 200, speichere_und_merke(anfrage.get("projekt") or {}, anfrage.get("path") or ""))
                return
            if cmd == "load":
                _json(self, 200, lade_und_merke(anfrage.get("path") or ""))
                return
            if cmd == "generate":
                out_dir = anfrage.get("out_dir") or str(app_home() / "export" / uuid.uuid4().hex[:8])
                job_id = _job_starten(anfrage.get("projekt") or {}, out_dir, anfrage.get("freecad_pfad"))
                _json(self, 200, {"ok": True, "job": job_id, "out_dir": out_dir})
                return
            _json(self, 400, {"ok": False, "fehler": "Unbekannter Befehl."})
        except Exception as exc:
            _json(self, 200, {"ok": False, "fehler": str(exc)})


def baue_server(host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    sitzungstoken()
    host = host or os.environ.get("CADSTUDIO_HOST", "127.0.0.1")
    if port is None:
        port = int(os.environ.get("CADSTUDIO_PORT", "47321"))
    return ThreadingHTTPServer((host, port), Handler)


def main():
    server = baue_server()
    host, port = server.server_address[:2]
    print("CADSTUDIO_HTTP http://%s:%d" % (host, port), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
