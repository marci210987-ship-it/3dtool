# -*- coding: utf-8 -*-
"""Kabelmanagement: Prüfung ohne FreeCAD und Export plus Passung mit FreeCADCmd."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.kabel import (  # noqa: E402
    KATALOG,
    masse,
    nutzlaengen,
    pruefe,
    standard_parameter,
    stuecke,
    system_meldungen,
    teil_anlegen,
)
from sidecar.layout import Projekt, auftrag_bauen  # noqa: E402
from sidecar.stlcheck import pruefe_stl  # noqa: E402


def _freecad() -> str | None:
    env = os.environ.get("FREECADCMD")
    if env and Path(env).exists():
        return env
    apprun = Path("/tmp/freecad/squashfs-root/AppRun")
    return str(apprun) if apprun.exists() else None


EXTREM = {
    "innenbreite_mm": 36.0,
    "innenhoehe_mm": 18.0,
    "wand_mm": 2.4,
    "spiel_mm": 0.35,
    "zapfen_mm": 12.0,
}


class KabelPruefung(unittest.TestCase):
    def test_katalog_hat_kanal_und_begleiter(self):
        ids = [e["id"] for e in KATALOG]
        self.assertEqual(ids[0], "kanal")
        for noetig in ("kanal", "ecke", "endkappe", "halter", "auslass"):
            self.assertIn(noetig, ids)

    def test_standard_und_extrem_sind_gueltig(self):
        extras = {
            "kanal": {"laenge_mm": 80, "deckel": "ja"},
            "ecke": {"schenkel_mm": 80},
            "endkappe": {"passt_auf": "buchse"},
            "halter": {"laenge_mm": 40, "loch_mm": 5},
            "auslass": {"laenge_mm": 60, "auslass_mm": 14},
        }
        for eintrag in KATALOG:
            self.assertEqual(pruefe(eintrag["id"], standard_parameter(eintrag["id"])), [], eintrag["id"])
            self.assertEqual(pruefe(eintrag["id"], {**EXTREM, **extras[eintrag["id"]]}), [], eintrag["id"])

    def test_ungueltige_werte_auf_deutsch(self):
        faelle = {
            "kanal": {"wand_mm": 0.4, "laenge_mm": 120},
            "ecke": {"schenkel_mm": 20},
            "endkappe": {"spiel_mm": 2},
            "halter": {"loch_mm": 16},
            "auslass": {"auslass_mm": 22, "innenbreite_mm": 20, "laenge_mm": 50},
        }
        for art, werte in faelle.items():
            fehler = pruefe(art, werte)
            self.assertTrue(fehler, art)
            self.assertTrue(any("außerhalb" in text or "zu " in text or "Rand" in text for text in fehler), fehler)

    def test_langer_kanal_wird_geteilt(self):
        params = {**standard_parameter("kanal"), "laenge_mm": 400}
        laengen = nutzlaengen({**params, "art": "kanal"})
        self.assertGreaterEqual(len(laengen), 2)
        self.assertAlmostEqual(sum(laengen), 400, places=2)
        teile = stuecke(teil_anlegen("kanal", params, id_="L"))
        self.assertGreaterEqual(len(teile), 2)
        for stueck in teile:
            self.assertLessEqual(max(stueck["soll"]), 250.0)

    def test_unterschiedliches_profil_wird_abgelehnt(self):
        a = teil_anlegen("kanal", id_="K1")
        b = teil_anlegen("kanal", {"innenbreite_mm": 40}, id_="K2", name="Zweiter Kanal")
        meldungen = system_meldungen([a, b])
        self.assertTrue(any("passen nicht" in text and "Innenbreite" in text for text in meldungen), meldungen)
        auftrag = auftrag_bauen(Projekt(name="Konflikt", nur_kabel=True, kabel=[a, b]))
        self.assertFalse(auftrag["ok"])

    def test_altes_projekt_ohne_kabel_laedt(self):
        projekt = Projekt.from_dict({"format": "cadstudio.projekt", "version": 1, "name": "Alt"})
        self.assertEqual(projekt.kabel, [])
        self.assertFalse(projekt.nur_kabel)
        hin = teil_anlegen("ecke")
        wieder = Projekt.from_dict(Projekt(name="Kabel", nur_kabel=True, kabel=[hin]).to_dict())
        self.assertTrue(wieder.nur_kabel)
        self.assertEqual(wieder.kabel[0]["art"], "ecke")

    def test_breite_aendert_das_aussenmass(self):
        schmal = masse("kanal", standard_parameter("kanal"))
        breit = masse("kanal", {**standard_parameter("kanal"), "innenbreite_mm": 36})
        self.assertGreater(breit[1], schmal[1] + 10)


class KabelExport(unittest.TestCase):
    def test_standard_extrem_und_teilung(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Export wurde nicht als bestanden gewertet.")
        os.environ["FREECADCMD"] = freecad
        from sidecar.engine import generiere

        def exportiere(name, teile):
            projekt = Projekt(name=name, nur_kabel=True, kabel=teile)
            with tempfile.TemporaryDirectory() as tmp:
                ergebnis = generiere(projekt, Path(tmp), freecad_pfad=freecad)
                self.assertTrue(ergebnis["ok"], ergebnis.get("fehler"))
                kaesten = {}
                for teil in ergebnis["teile"]:
                    self.assertTrue(teil["ok"], teil)
                    for datei in teil["dateien"]:
                        stl = Path(datei["stl"])
                        fcstd = Path(datei["fcstd"])
                        self.assertTrue(stl.is_file() and stl.stat().st_size > 200, datei["id"])
                        self.assertTrue(fcstd.is_file() and fcstd.stat().st_size > 200, datei["id"])
                        mesh = pruefe_stl(stl, tuple(datei["soll_mm"]))
                        self.assertTrue(mesh["ok"], (datei["id"], mesh))
                        self.assertTrue(mesh["wasserdicht"] and mesh["mannigfaltig"], mesh)
                        self.assertEqual(datei["solid"]["solids"], 1)
                        self.assertTrue(datei["solid"]["valid"])
                        self.assertGreater(datei["solid"]["volume_mm3"], 1)
                        self.assertTrue(datei["mesh_freecad"]["ok"], datei.get("mesh_freecad"))
                        self.assertTrue(datei["fcstd_erneut_geladen"]["ok"])
                        kaesten[datei["id"]] = mesh["bbox_mm"]
                return kaesten

        standard = []
        for eintrag in KATALOG:
            standard.append(teil_anlegen(eintrag["id"], id_="S" + eintrag["id"][:3]))
        standard.append(teil_anlegen("kanal", {"laenge_mm": 400, "deckel": "ja"}, id_="L", name="Lange Strecke"))
        kaesten = exportiere("Standard", standard)
        self.assertIn("L_1", kaesten)
        self.assertIn("L_2", kaesten)
        self.assertIn("L_1_deckel", kaesten)
        self.assertLessEqual(max(kaesten["L_1"]), 250.0)
        self.assertLessEqual(max(kaesten["L_2"]), 250.0)

        extras = {
            "kanal": {"laenge_mm": 80, "deckel": "ja"},
            "ecke": {"schenkel_mm": 80},
            "endkappe": {"passt_auf": "buchse"},
            "halter": {"laenge_mm": 40, "loch_mm": 5},
            "auslass": {"laenge_mm": 60, "auslass_mm": 14},
        }
        extrem = [teil_anlegen(art, {**EXTREM, **extra}, id_="X" + art[:3]) for art, extra in extras.items()]
        weit = exportiere("Extrem", extrem)
        self.assertGreater(weit["Xkan"][1], kaesten["Skan"][1] + 5)

    def test_zwei_kanaele_passen_und_ein_zu_grosser_stecker_nicht(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Export wurde nicht als bestanden gewertet.")
        os.environ["FREECADCMD"] = freecad
        from sidecar.detect_freecad import freecad_command
        from sidecar.engine import FreeCADSession

        session = FreeCADSession(freecad_command(Path(freecad)))
        session.start()
        try:
            a = teil_anlegen("kanal", {"laenge_mm": 80}, id_="A")
            b = teil_anlegen("kanal", {"laenge_mm": 90}, id_="B")
            passung = session.request({"cmd": "kabel_passung", "a": a, "b": b})["result"]
            self.assertTrue(passung["ok"], passung)
            self.assertLess(passung["schnittvolumen_mm3"], 0.05)
            self.assertTrue(all(abs(wert - 0.2) <= 0.08 for wert in passung["luecken_mm"]), passung)

            eng = {**standard_parameter("kanal"), "spiel_mm": 0.35, "laenge_mm": 70}
            gemessen = session.request({"cmd": "kabel_passung", "a": teil_anlegen("kanal", eng, id_="A"), "b": teil_anlegen("kanal", eng, id_="B")})["result"]
            self.assertTrue(gemessen["ok"], gemessen)
            self.assertTrue(all(abs(wert - 0.35) <= 0.08 for wert in gemessen["luecken_mm"]), gemessen)

            gross = teil_anlegen("kanal", {"laenge_mm": 80, "innenbreite_mm": 40}, id_="G")
            klein = teil_anlegen("kanal", {"laenge_mm": 80, "innenbreite_mm": 20}, id_="K")
            schnitt = session.request({"cmd": "kabel_passung", "a": gross, "b": klein})["result"]
            self.assertFalse(schnitt["ok"], schnitt)
            self.assertGreater(schnitt["schnittvolumen_mm3"], 1.0)
            self.assertIn("passen nicht", schnitt["meldung"])

            lose = session.request({"cmd": "kabel_passung", "a": klein, "b": gross})["result"]
            self.assertFalse(lose["ok"], lose)
            self.assertTrue(any(abs(wert - 0.2) > 0.5 for wert in lose["luecken_mm"]), lose)

            strecken = stuecke(teil_anlegen("kanal", {"laenge_mm": 400}, id_="L"))
            kette = session.request(
                {
                    "cmd": "kabel_passung",
                    "a": {"art": strecken[0]["art"], "parameter": strecken[0]["params"]},
                    "b": {"art": strecken[1]["art"], "parameter": strecken[1]["params"]},
                }
            )["result"]
            self.assertTrue(kette["ok"], kette)
            self.assertLess(kette["schnittvolumen_mm3"], 0.05)
            ecke = teil_anlegen("ecke", id_="E")
            ecke_stecker = session.request({"cmd": "kabel_passung", "a": ecke, "b": a})["result"]
            ecke_buchse = session.request({"cmd": "kabel_passung", "a": a, "b": ecke})["result"]
            self.assertTrue(ecke_stecker["ok"] and ecke_buchse["ok"], (ecke_stecker, ecke_buchse))
            halter = session.request({"cmd": "kabel_passung", "a": teil_anlegen("halter", id_="H"), "b": a})["result"]
            self.assertTrue(halter["ok"], halter)
            self.assertLess(halter["schnittvolumen_mm3"], 0.05)
            self.assertTrue(all(abs(wert - 0.2) <= 0.08 for wert in halter["luecken_mm"]), halter)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
