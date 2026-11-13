# -*- coding: utf-8 -*-
"""Projekt speichern, frischer Prozess, erneut öffnen."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.layout import Box, Projekt, Schublade, projekt_laden  # noqa: E402


class ProjektTest(unittest.TestCase):
    def test_neustart_laedt_dieselbe_datei(self):
        projekt = Projekt(
            name="Kueche",
            schublade=Schublade(
                innenbreite_mm=480,
                innentiefe_mm=420,
                nutzhoehe_mm=70,
                spiel_mm=1.0,
                verbinder_spiel_mm=0.2,
                rand_links_mm=2,
            ),
            boxen=[
                Box("B1", "Klein", 8, 6, 1, 1, 3),
                Box("B2", "Mittel", 2, 0, 2, 2, 3, fach_x=2, fach_y=2),
                Box("B3", "Lang", 5, 0, 1, 3, 2, rotation=90, fach_x=1, fach_y=3),
                Box("B4", "Gross", 0, 4, 2, 3, 4),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            ziel = Path(tmp) / "kueche.cadstudio.json"
            env = os.environ.copy()
            env["CADSTUDIO_HOME"] = str(home)
            env["PYTHONPATH"] = str(ROOT)
            code = textwrap.dedent(
                """
                import json, os
                from pathlib import Path
                from sidecar.engine import recent_liste, speichere_und_merke
                projekt = json.loads(Path(os.environ["PROJEKT_JSON"]).read_text(encoding="utf-8"))
                speichere_und_merke(projekt, os.environ["ZIEL"])
                print(json.dumps({"recent": recent_liste()}))
                """
            )
            zwischen = Path(tmp) / "projekt.json"
            zwischen.write_text(json.dumps(projekt.to_dict()), encoding="utf-8")
            env["PROJEKT_JSON"] = str(zwischen)
            env["ZIEL"] = str(ziel)
            erster = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), env=env, capture_output=True, text=True)
            self.assertEqual(erster.returncode, 0, erster.stderr)
            # Frischer Prozess, kein gemeinsamer Speicher.
            code2 = textwrap.dedent(
                """
                import json, os
                from sidecar.engine import lade_und_merke, recent_liste
                geladen = lade_und_merke(os.environ["ZIEL"])
                print(json.dumps({"geladen": geladen, "recent": recent_liste()}))
                """
            )
            zweiter = subprocess.run([sys.executable, "-c", code2], cwd=str(ROOT), env=env, capture_output=True, text=True)
            self.assertEqual(zweiter.returncode, 0, zweiter.stderr)
            daten = json.loads(zweiter.stdout.strip().splitlines()[-1])
            neu = daten["geladen"]["projekt"]
            self.assertEqual(neu["name"], "Kueche")
            self.assertEqual(neu["schublade"]["innenbreite_mm"], 480)
            self.assertEqual(neu["schublade"]["rand_links_mm"], 2)
            self.assertEqual(len(neu["boxen"]), 4)
            self.assertEqual(neu["boxen"][2]["rotation"], 90)
            self.assertEqual(neu["boxen"][3]["ez"], 4)
            self.assertEqual(daten["recent"][0]["name"], "Kueche")
            self.assertEqual(projekt_laden(ziel).boxen[0].x, 8)


if __name__ == "__main__":
    unittest.main()
