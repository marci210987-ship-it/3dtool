# -*- coding: utf-8 -*-
"""Eigene Vorlagen: Speichern, Laden, Ersetzen, Löschen, ungültige Eingaben."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar import vorlagen  # noqa: E402
from sidecar.eigenteil import Eigenteil  # noqa: E402


def _teil(**extra):
    return {"name": "Halter", "hoehe_mm": 10, "formen": [{"typ": "rechteck", "x": 0, "y": 0, "b": 40, "t": 30, "loch": False}], **extra}


class VorlagenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = os.environ.get("CADSTUDIO_HOME")
        os.environ["CADSTUDIO_HOME"] = self.tmp.name

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("CADSTUDIO_HOME", None)
        else:
            os.environ["CADSTUDIO_HOME"] = self.alt
        self.tmp.cleanup()

    def test_speichern_laden_und_loeschen(self):
        self.assertEqual(vorlagen.vorlagen_laden(), [])
        liste = vorlagen.vorlage_speichern("Mein Halter", _teil(platziert=True, x_mm=99, y_mm=50, id="E7"))
        self.assertEqual(len(liste), 1)
        eintrag = vorlagen.vorlagen_laden()[0]
        self.assertEqual(eintrag["name"], "Mein Halter")
        # Platzierung und Id gehören nicht zur Vorlage
        self.assertFalse(eintrag["teil"]["platziert"])
        self.assertEqual(eintrag["teil"]["x_mm"], 0.0)
        self.assertNotIn("id", eintrag["teil"])
        Eigenteil.from_dict({**eintrag["teil"], "id": "E1"})  # lädt wieder als Teil
        self.assertEqual(vorlagen.vorlage_loeschen(eintrag["id"]), [])
        self.assertEqual(vorlagen.vorlagen_laden(), [])

    def test_gleicher_name_ersetzt(self):
        vorlagen.vorlage_speichern("A", _teil())
        liste = vorlagen.vorlage_speichern("a", _teil(hoehe_mm=20))
        self.assertEqual(len(liste), 1)
        self.assertEqual(liste[0]["teil"]["hoehe_mm"], 20)

    def test_ungueltiges_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            vorlagen.vorlage_speichern("", _teil())
        with self.assertRaises(ValueError):
            vorlagen.vorlage_speichern("x" * 61, _teil())
        with self.assertRaises(ValueError):
            vorlagen.vorlage_speichern("Leer", _teil(formen=[]))
        with self.assertRaises(ValueError):
            vorlagen.vorlage_speichern("Schief", _teil(hoehe_mm=-1))
        self.assertEqual(vorlagen.vorlagen_laden(), [])

    def test_beschaedigte_datei_ergibt_leere_liste(self):
        (Path(self.tmp.name) / "vorlagen.json").write_text("{kaputt", encoding="utf-8")
        self.assertEqual(vorlagen.vorlagen_laden(), [])
        (Path(self.tmp.name) / "vorlagen.json").write_text('{"a": 1}', encoding="utf-8")
        self.assertEqual(vorlagen.vorlagen_laden(), [])
        (Path(self.tmp.name) / "vorlagen.json").write_text('[1, {"id": "v-1", "name": "ok", "teil": {}}]', encoding="utf-8")
        self.assertEqual([e["id"] for e in vorlagen.vorlagen_laden()], ["v-1"])
        # Speichern funktioniert danach wieder
        vorlagen.vorlage_speichern("Neu", _teil())
        self.assertEqual(len(vorlagen.vorlagen_laden()), 2)


if __name__ == "__main__":
    unittest.main()
