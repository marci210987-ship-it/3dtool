# -*- coding: utf-8 -*-
"""Lokaler Dienst: fremde Webseiten dürfen nicht schreiben, relative Pfade bleiben im Benutzerordner."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CADSTUDIO_HOME"] = self.tmp.name
        os.environ["CADSTUDIO_TOKEN"] = "a" * 32
        import sidecar.server as server

        server.TOKEN = ""
        self.server = server
        self.httpd = server.baue_server("127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.tmp.cleanup()

    def _rufen(self, methode: str, pfad: str, koerper=None, ursprung: str | None = None, token: str | None = None):
        daten = None if koerper is None else json.dumps(koerper).encode("utf-8")
        anfrage = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, pfad),
            data=daten,
            method=methode,
        )
        anfrage.add_header("Content-Type", "application/json")
        if ursprung:
            anfrage.add_header("Origin", ursprung)
        if token:
            anfrage.add_header("X-CADStudio-Token", token)
        try:
            with urllib.request.urlopen(anfrage) as antwort:
                return antwort.status, json.loads(antwort.read().decode("utf-8"))
        except urllib.error.HTTPError as fehler:
            roh = fehler.read().decode("utf-8")
            try:
                inhalt = json.loads(roh)
            except json.JSONDecodeError:
                inhalt = {"roh": roh}
            return fehler.code, inhalt

    def test_fremde_website_darf_nicht_speichern(self):
        code, _inhalt = self._rufen(
            "POST",
            "/api",
            {"cmd": "save", "path": str(Path(self.tmp.name) / "fremd.json"), "projekt": {"name": "Fremd", "schublade": {}, "boxen": []}},
            ursprung="https://evil.example",
            token="a" * 32,
        )
        self.assertEqual(code, 403)
        self.assertFalse((Path(self.tmp.name) / "fremd.json").exists())

    def test_sitzung_nur_fuer_die_oberflaeche(self):
        code, _inhalt = self._rufen("GET", "/sitzung", ursprung="https://evil.example")
        self.assertEqual(code, 403)
        code, inhalt = self._rufen("GET", "/sitzung", ursprung="http://localhost:1420")
        self.assertEqual(code, 200)
        self.assertEqual(inhalt["token"], "a" * 32)

    def test_ohne_token_kein_schreiben(self):
        code, _inhalt = self._rufen(
            "POST",
            "/api",
            {"cmd": "save", "path": "schublade.cadstudio.json", "projekt": {"name": "Ohne", "schublade": {}, "boxen": []}},
            ursprung="http://localhost:1420",
        )
        self.assertEqual(code, 403)
        self.assertFalse((Path(self.tmp.name) / "projekte" / "schublade.cadstudio.json").exists())

    def test_relativer_pfad_landet_im_benutzerordner(self):
        code, inhalt = self._rufen(
            "POST",
            "/api",
            {"cmd": "save", "path": "kueche.cadstudio.json", "projekt": {"name": "Kueche", "schublade": {}, "boxen": []}},
            ursprung="http://127.0.0.1:1420",
            token="a" * 32,
        )
        self.assertEqual(code, 200, inhalt)
        ziel = Path(inhalt["pfad"])
        self.assertTrue(ziel.is_file())
        self.assertEqual(ziel.parent, (Path(self.tmp.name) / "projekte").resolve())
        self.assertFalse((Path.cwd() / "kueche.cadstudio.json").exists())

    def test_leerer_pfad_nutzt_den_projektnamen(self):
        code, inhalt = self._rufen(
            "POST",
            "/api",
            {"cmd": "save", "path": "", "projekt": {"name": "Neue Schublade", "schublade": {}, "boxen": []}},
            token="a" * 32,
        )
        self.assertEqual(code, 200, inhalt)
        self.assertTrue(Path(inhalt["pfad"]).name.startswith("Neue_Schublade"))
        self.assertEqual(Path(inhalt["pfad"]).parent, (Path(self.tmp.name) / "projekte").resolve())


if __name__ == "__main__":
    unittest.main()
