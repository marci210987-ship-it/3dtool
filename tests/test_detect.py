# -*- coding: utf-8 -*-
"""FreeCAD-Suche mit nachgebauten Ordnern. Kein echter Windows-Lauf."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.detect_freecad import (  # noqa: E402
    candidate_paths,
    detect,
    freecad_command,
    parse_version,
    version_ist_1_1,
)


class DetectTest(unittest.TestCase):
    def test_version(self):
        self.assertEqual(parse_version("FreeCAD 1.1.4R20260928"), "1.1.4")
        self.assertTrue(version_ist_1_1("1.1.4"))
        self.assertTrue(version_ist_1_1("1.1.0"))
        self.assertFalse(version_ist_1_1("1.0.0"))
        self.assertFalse(version_ist_1_1("0.21.2"))
        self.assertFalse(version_ist_1_1("26.3.0"))

    def test_benutzerpfad_und_program_files_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            exe = basis / "FreeCAD 1.1" / "bin" / "FreeCADCmd.exe"
            exe.parent.mkdir(parents=True)
            exe.write_text("", encoding="utf-8")
            alt = os.environ.get("FREECADCMD")
            os.environ.pop("FREECADCMD", None)
            try:
                pfade = candidate_paths(user_path=str(exe), extra_roots=[basis])
                self.assertEqual(pfade[0], exe)
                self.assertIn(exe, pfade)
                info = detect(user_path=str(basis / "fehlt.exe"), extra_roots=[basis], probe=False)
            finally:
                if alt:
                    os.environ["FREECADCMD"] = alt
            self.assertTrue(info["gefunden"])
            self.assertTrue(info["pfad"].endswith("FreeCADCmd.exe"))

    def test_appimage_befehl(self):
        self.assertEqual(freecad_command(Path("/tmp/FreeCAD.AppImage"))[1], "freecadcmd")
        self.assertEqual(len(freecad_command(Path("/usr/bin/freecadcmd"))), 1)

    def test_registry_auf_dieser_vm_nicht_ausgefuehrt(self):
        if os.name == "nt":
            self.skipTest("Windows-Lauf")
        from sidecar.detect_freecad import registry_candidates

        self.assertEqual(registry_candidates(), [])


if __name__ == "__main__":
    unittest.main()
