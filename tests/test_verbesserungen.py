"""Regressionen für Skizzenbedingungen, Vorschau und abbrechbare Aufträge."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from sidecar.bedingungen import anwenden
from sidecar.eigenteil import Eigenteil
from sidecar import engine, server


class BedingungenTest(unittest.TestCase):
    def setUp(self):
        self.formen = [
            {"fid": "a", "typ": "rechteck", "x": 0, "y": 0, "b": 40, "t": 20, "loch": False},
            {"fid": "b", "typ": "kreis", "x": 1, "y": 1, "r": 2, "loch": True},
            {"fid": "c", "typ": "kreis", "x": 2, "y": 2, "r": 1, "loch": True},
        ]

    def test_kette_und_projekt_roundtrip(self):
        regeln = [{"art": "abstand", "quelle": "b", "ziel": "c", "dx": 10, "dy": -2}, {"art": "mittig", "quelle": "a", "ziel": "b"}]
        teil = Eigenteil.from_dict({"id": "E1", "formen": self.formen, "bedingungen": regeln})
        self.assertEqual((teil.formen[2]["x"], teil.formen[2]["y"]), (30, 8))
        roh = json.loads(json.dumps(teil.to_dict()))
        roh["formen"][0]["b"] = 60
        neu = Eigenteil.from_dict(roh)
        self.assertEqual(neu.formen[2]["x"], 40)
        self.assertEqual(neu.bedingungen, regeln)
        self.assertEqual(self.formen[1]["x"], 1)

    def test_kreisbezug_und_mehrfachbelegung(self):
        for regeln in [
            [{"art": "mittig", "quelle": "a", "ziel": "b"}, {"art": "mittig", "quelle": "b", "ziel": "a"}],
            [{"art": "mittig", "quelle": "a", "ziel": "b"}, {"art": "abstand", "quelle": "c", "ziel": "b"}],
            [{"art": "abstand", "quelle": "a", "ziel": "b", "dx": float("nan")}],
        ]:
            with self.assertRaises(ValueError):
                anwenden(self.formen, regeln)

    def test_groesse_parallel_und_mitte(self):
        self.formen[1] = {"fid": "b", "typ": "rechteck", "x": 100, "y": 100, "b": 10, "t": 5}
        self.formen[0]["winkel"] = 35
        f = anwenden(self.formen, [{"art": art, "quelle": "a", "ziel": "b"} for art in ("mittig", "gleich", "parallel")])[1]
        self.assertEqual([f[k] for k in ("x", "y", "b", "t", "winkel")], [0, 0, 40, 20, 35])


class VorschauTest(unittest.TestCase):
    def test_alle_teile_cache_und_veraltete_anfrage(self):
        teile = [{"id": str(i), "rolle": "box", "name": str(i)} for i in range(10)]
        class Proc:
            def poll(self): return None
        class Session:
            def __init__(self, *args): pass
            proc = Proc()
            def request(self, req, **kw):
                calls.append(req)
                return {"ok": True, "result": {"netze": [{"teil": req["teile"][0]["id"]}], "hinweise": []}}
        calls = []
        with patch.object(engine, "_VORSCHAU", {"sitzung": Session(), "pfad": "test", "timer": None}), patch.object(engine, "_VORSCHAU_CACHE", engine.OrderedDict()), patch.object(engine, "_VORSCHAU_ANFRAGEN", {}), patch.object(engine, "auftrag_bauen", return_value={"ok": True, "teile": teile}), patch.object(engine.threading, "Timer"):
            r = engine.vorschau_bauen({}, freecad_pfad="test", kanal="a", folge=2)
            self.assertEqual(len(r["netze"]), 10)
            self.assertEqual(r["teile_gezeigt"], 10)
            engine.vorschau_bauen({}, freecad_pfad="test", kanal="a", folge=3)
            self.assertEqual(len(calls), 10)
            self.assertFalse(engine.vorschau_bauen({}, freecad_pfad="test", kanal="a", folge=1)["ok"])


class AbbruchTest(unittest.TestCase):
    def test_abgebrochener_auftrag_wird_nicht_registriert(self):
        gestartet, weiter = threading.Event(), threading.Event()
        def fake(*args, abbrechen, **kwargs):
            gestartet.set()
            abbrechen.wait(2)
            weiter.set()
            return {"ok": True, "teile": []}
        with tempfile.TemporaryDirectory() as tmp, patch.object(server, "app_home", return_value=Path(tmp)), patch.object(server, "generiere", side_effect=fake), patch.object(server, "_registrieren") as registrieren:
            job = server._job_starten({}, tmp, None)
            self.assertTrue(gestartet.wait(1))
            with server.JOBS_LOCK: server.ABBRUECHE[job].set()
            self.assertTrue(weiter.wait(2))
            for _ in range(100):
                with server.JOBS_LOCK: status = server.JOBS[job]["status"]
                if status == "abgebrochen": break
                time.sleep(0.01)
            self.assertEqual(status, "abgebrochen")
            registrieren.assert_not_called()

class BauraumTest(unittest.TestCase):
    def test_stueckliste_nutzt_projektgrenzen(self):
        from sidecar.layout import Projekt, Schublade
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp)
            stl, fcstd = ziel / "teil.stl", ziel / "teil.FCStd"
            stl.write_text("mesh")
            fcstd.write_text("x" * 300)
            datei = {"id": "E1", "name": "Teil", "stl": str(stl), "fcstd": str(fcstd), "ok": True, "fcstd_erneut_geladen": {"ok": True}, "solid": {"bbox_mm": [200, 20, 10], "volume_mm3": 4000}}
            built = {"ok": True, "result": {"ok": True, "teile": [{"id": "E1", "rolle": "eigen", "name": "Teil", "ok": True, "dateien": [datei]}]}}
            mesh = dict(ok=True, wasserdicht=True, mannigfaltig=True, bbox_mm=[200, 20, 10], volumen_mm3=4000, fehler=[], dreiecke=12)
            auftrag = {"ok": True, "teile": [], "ansicht": {"hinweise": [], "einheiten_x": 0, "einheiten_y": 0, "platten": [], "verbinder_anzahl": 0}}
            with patch.object(engine, "auftrag_bauen", return_value=auftrag), patch.object(engine, "freecad_befehl", return_value=(["fake"], {})), patch.object(engine, "FreeCADSession") as session, patch.object(engine, "pruefe_stl", return_value=mesh):
                session.return_value.start.return_value = {"freecad": "1.1.4"}
                session.return_value.request.return_value = built
                projekt = Projekt(nur_eigene=True, schublade=Schublade(bauraum_mm=(180, 200, 220)))
                self.assertFalse(engine.generiere(projekt, ziel, freecad_pfad="fake")["ok"])
                zeile = json.loads((ziel / "Stueckliste.json").read_text())
                # Die Stückliste speichert Metadaten und die Zeilen getrennt.
                self.assertIn('"Bauraum": "nein"', (ziel / "Stueckliste.json").read_text())

    def test_abbruch_beendet_laufenden_freecad_prozess(self):
        from sidecar.layout import Projekt
        cancelled = threading.Event()
        class Proc:
            def poll(self): return None
            def kill(self): killed.set()
        class Session:
            def __init__(self, *args): pass
            proc = Proc()
            def start(self): return {"freecad": "1.1.4"}
            def request(self, *args, **kwargs):
                cancelled.set()
                if not killed.wait(2): raise AssertionError("FreeCAD wurde nicht beendet")
                raise RuntimeError("Worker beendet")
            def close(self): pass
        killed = threading.Event()
        with tempfile.TemporaryDirectory() as tmp, patch.object(engine, "auftrag_bauen", return_value={"ok": True, "teile": []}), patch.object(engine, "freecad_befehl", return_value=(["fake"], {})), patch.object(engine, "FreeCADSession", Session):
            with self.assertRaises(RuntimeError): engine.generiere(Projekt(), Path(tmp), freecad_pfad="fake", abbrechen=cancelled)
        self.assertTrue(killed.is_set())
