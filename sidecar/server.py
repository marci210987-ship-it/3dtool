# -*- coding: utf-8 -*-
"""Lokaler HTTP-Dienst für die Oberfläche. Kein Netz nach außen."""

from __future__ import annotations

import json
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


def _json(handler: BaseHTTPRequestHandler, code: int, payload: dict):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(data)


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
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            _json(self, 200, {"ok": True, "dienst": "cad-studio"})
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
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            return
        _json(self, 404, {"ok": False, "fehler": "Unbekannter Pfad."})

    def do_POST(self):
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


def main():
    import os

    host = os.environ.get("CADSTUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("CADSTUDIO_PORT", "47321"))
    server = ThreadingHTTPServer((host, port), Handler)
    print("CADSTUDIO_HTTP http://%s:%d" % (host, port), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
