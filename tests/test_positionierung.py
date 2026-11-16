"""Positionsmetadaten bleiben beim Speichern/Laden und im Exportauftrag erhalten."""
import json
import unittest
from sidecar.eigenteil import Eigenteil, eigen_params, form_bbox


class PositionierungTest(unittest.TestCase):
    def test_projekt_und_exportauftrag(self):
        formen = [
            {"typ": "rechteck", "x": 30, "y": 20, "b": 80, "t": 40, "loch": False, "form_id": "f1"},
            {"typ": "kreis", "x": 70, "y": 40, "r": 3, "loch": True, "form_id": "f2",
             "position": {"x": {"quelle": "teil", "lage": "mitte"}, "y": {"quelle": "teil", "lage": "mitte"}}},
            {"typ": "kreis", "x": 70, "y": 40, "r": 8, "loch": False, "form_id": "f3",
             "position": {"x": {"quelle": "f2", "lage": "mitte"}, "y": {"quelle": "f2", "lage": "mitte"}}},
        ]
        teil = Eigenteil(id="E1", formen=formen)
        geladen = Eigenteil.from_dict(json.loads(json.dumps(teil.to_dict())))
        self.assertEqual(geladen.formen, formen)
        self.assertEqual(eigen_params(geladen)["Formen"], formen)
        self.assertEqual(form_bbox(geladen.formen[1]), (67, 37, 73, 43))

    def test_alte_projekte_ohne_bindungen(self):
        teil = Eigenteil.from_dict({"id": "E1", "formen": [{"typ": "kreis", "x": 10, "y": 20, "r": 3, "loch": False}]})
        self.assertEqual(form_bbox(teil.formen[0]), (7, 17, 13, 23))

    def test_freecad_export_mit_positionsmetadaten(self):
        import os
        import math
        import tempfile
        from pathlib import Path
        from sidecar.engine import generiere
        from sidecar.layout import Projekt
        freecad = os.environ.get("FREECADCMD", "")
        if not freecad or not Path(freecad).exists():
            self.skipTest("FREECADCMD nicht gesetzt")
        formen = [
            {"typ": "rechteck", "x": 30, "y": 20, "b": 80, "t": 40, "loch": False, "form_id": "f1"},
            {"typ": "kreis", "x": 70, "y": 40, "r": 3, "loch": True, "form_id": "f2",
             "position": {"x": {"quelle": "teil", "lage": "mitte"}, "y": {"quelle": "teil", "lage": "mitte"}}},
            {"typ": "kreis", "x": 70, "y": 40, "r": 6, "loch": True, "form_id": "f3",
             "position": {"x": {"quelle": "f2", "lage": "mitte"}, "y": {"quelle": "f2", "lage": "mitte"}}},
        ]
        teil = Eigenteil(id="E1", hoehe_mm=4, formen=formen)
        with tempfile.TemporaryDirectory() as tmp:
            ergebnis = generiere(Projekt(nur_eigene=True, eigene=[teil]), Path(tmp), freecad_pfad=freecad)
            self.assertTrue(ergebnis["ok"], ergebnis["fehler"])
            dateien = [d for t in ergebnis["teile"] for d in t["dateien"]]
            self.assertTrue(dateien)
            self.assertAlmostEqual(dateien[0]["solid"]["volume_mm3"], (80 * 40 - math.pi * 36) * 4, delta=1)
