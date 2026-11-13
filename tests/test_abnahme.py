# -*- coding: utf-8 -*-
"""Verbindlicher Schubladenablauf mit echtem FreeCADCmd.

Der Test bricht ab, sobald ein Schritt fehlschlägt. Ein Export gilt nur als
bestanden, wenn die Dateien existieren, das Netz geschlossen ist und FreeCAD
die FCStd-Datei erneut als gültigen Körper lädt.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.engine import externe_dateipruefung, generiere  # noqa: E402
from sidecar.layout import Box, Projekt, Schublade, plan_ansicht, projekt_laden  # noqa: E402
from sidecar.stlcheck import pruefe_stl  # noqa: E402


def _freecad() -> str | None:
    env = os.environ.get("FREECADCMD")
    if env and Path(env).exists():
        return env
    apprun = Path("/tmp/freecad/squashfs-root/AppRun")
    if apprun.exists():
        return str(apprun)
    return None


class AbnahmeTest(unittest.TestCase):
    def test_schublade_480x420(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Test wurde nicht als bestanden gewertet.")

        os.environ["FREECADCMD"] = freecad
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            os.environ["CADSTUDIO_HOME"] = str(home)
            projekt = Projekt(
                name="Abnahme 480x420",
                schublade=Schublade(innenbreite_mm=480, innentiefe_mm=420, nutzhoehe_mm=80, spiel_mm=1.0, verbinder_spiel_mm=0.20),
                boxen=[],
            )
            ansicht = plan_ansicht(projekt)
            self.assertEqual(ansicht["einheiten_x"], 11)
            self.assertEqual(ansicht["einheiten_y"], 9)
            self.assertEqual(len(ansicht["platten"]), 4)
            self.assertTrue(all(p["passt_in_bauraum"] for p in ansicht["platten"]))

            projekt.boxen = [
                Box("B1", "Kleine Box", 0, 0, 1, 1, 3),
                Box("B2", "Mittlere Box", 2, 0, 2, 2, 3, fach_x=2, fach_y=2),
                Box("B3", "Besteckfach", 5, 0, 1, 3, 2, fach_x=1, fach_y=3),
                Box("B4", "Grosse Box", 0, 4, 2, 3, 3),
            ]
            self.assertTrue(plan_ansicht(projekt)["ok"])

            projekt.boxen[0].x, projekt.boxen[0].y = 8, 6
            projekt.boxen[2].rotation = 90
            self.assertTrue(plan_ansicht(projekt)["ok"], plan_ansicht(projekt)["fehler"])

            projekt.boxen[1].x, projekt.boxen[1].y = 0, 4
            konflikt = plan_ansicht(projekt)
            self.assertFalse(konflikt["ok"])
            self.assertTrue(konflikt["kollisionen"])
            ausgabe_konflikt = Path(tmp) / "konflikt"
            verweigert = generiere(projekt, ausgabe_konflikt, freecad_pfad=freecad)
            self.assertFalse(verweigert["ok"])
            self.assertFalse((ausgabe_konflikt / "manifest.json").read_text(encoding="utf-8").count('"ok": true'))

            projekt.boxen[1].x, projekt.boxen[1].y = 2, 0
            projekt.boxen[3].ez = 4
            self.assertTrue(plan_ansicht(projekt)["ok"], plan_ansicht(projekt)["fehler"])

            ziel = Path(tmp) / "abnahme.cadstudio.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            env["CADSTUDIO_HOME"] = str(home)
            env["PROJEKT"] = json.dumps(projekt.to_dict())
            env["ZIEL"] = str(ziel)
            speichern = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(
                    """
                    import json, os
                    from sidecar.engine import speichere_und_merke
                    speichere_und_merke(json.loads(os.environ["PROJEKT"]), os.environ["ZIEL"])
                    """
                )],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(speichern.returncode, 0, speichern.stderr)
            laden = subprocess.run(
                [sys.executable, "-c", textwrap.dedent(
                    """
                    import json, os
                    from sidecar.engine import lade_und_merke
                    print(json.dumps(lade_und_merke(os.environ["ZIEL"])))
                    """
                )],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(laden.returncode, 0, laden.stderr)
            neu = json.loads(laden.stdout.strip().splitlines()[-1])["projekt"]
            self.assertEqual(neu["schublade"]["innenbreite_mm"], 480)
            self.assertEqual(len(neu["boxen"]), 4)
            self.assertEqual(neu["boxen"][0]["x"], 8)
            self.assertEqual(neu["boxen"][2]["rotation"], 90)
            self.assertEqual(neu["boxen"][3]["ez"], 4)
            geladen = projekt_laden(ziel)
            self.assertEqual([b.ez for b in geladen.boxen], [3, 3, 2, 4])

            export = Path(tmp) / "export"
            ergebnis = generiere(geladen, export, freecad_pfad=freecad)
            self.assertTrue(ergebnis["ok"], json.dumps(ergebnis.get("fehler"), ensure_ascii=False)[:4000])
            self.assertGreaterEqual(len(ergebnis["teile"]), 6)
            dateien = []
            for teil in ergebnis["teile"]:
                self.assertTrue(teil["ok"], teil)
                for datei in teil["dateien"]:
                    stl = Path(datei["stl"])
                    fcstd = Path(datei["fcstd"])
                    self.assertTrue(stl.is_file() and stl.stat().st_size > 200, datei)
                    self.assertTrue(fcstd.is_file() and fcstd.stat().st_size > 200, datei)
                    mesh = pruefe_stl(stl, tuple(datei["soll_mm"]))
                    self.assertTrue(mesh["ok"], mesh)
                    self.assertTrue(datei["fcstd_erneut_geladen"]["ok"])
                    self.assertTrue(datei["mesh_freecad"]["ok"], datei["mesh_freecad"])
                    dateien.append({"id": datei["id"], "stl": str(stl), "fcstd": str(fcstd)})
            self.assertTrue((export / "Stueckliste.csv").is_file())
            self.assertTrue((export / "Montageuebersicht.html").is_file())
            self.assertTrue((export / "Montageuebersicht.pdf").stat().st_size > 500)
            self.assertTrue((export / "Montageuebersicht.png").stat().st_size > 500)
            zweit = externe_dateipruefung(freecad, dateien)
            self.assertTrue(zweit.get("ok"), json.dumps(zweit, ensure_ascii=False)[:3000])
            beispiel = ROOT / "examples"
            beispiel.mkdir(exist_ok=True)
            shutil.copyfile(ziel, beispiel / "schublade_480x420.cadstudio.json")
            (beispiel / "abnahme_manifest_auszug.json").write_text(
                json.dumps(
                    {
                        "ok": ergebnis["ok"],
                        "freecad": ergebnis.get("freecad"),
                        "ansicht": ergebnis.get("ansicht"),
                        "teile": [
                            {
                                "id": t["id"],
                                "ok": t["ok"],
                                "dateien": [
                                    {
                                        "id": d["id"],
                                        "bytes_stl": d.get("bytes_stl"),
                                        "bbox": (d.get("solid") or {}).get("bbox_mm"),
                                        "mesh": (d.get("mesh_unabhaengig") or {}).get("ok"),
                                    }
                                    for d in t["dateien"]
                                ],
                            }
                            for t in ergebnis["teile"]
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    unittest.main()
