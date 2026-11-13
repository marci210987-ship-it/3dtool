# -*- coding: utf-8 -*-
"""Einrichtungsskript für das mitgelieferte Python: Prüfsumme, Entpacken, Suchpfade, Wiederholung (ohne Netz)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _laden():
    spec = importlib.util.spec_from_file_location("python_einbetten", ROOT / "scripts" / "python_einbetten.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _zip(pfad: Path) -> str:
    with zipfile.ZipFile(pfad, "w") as zf:
        zf.writestr("python.exe", b"MZ")
        zf.writestr("python312._pth", "python312.zip\nimport site\n")
        zf.writestr("LICENSE.txt", "PSF")
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


class EinbettenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.modul = _laden()
        self.modul.ROOT = self.root
        self.cache = self.root / ".cache" / "python-embed"
        self.cache.mkdir(parents=True)
        self.archiv = self.cache / ("python-%s-embed-amd64.zip" % self.modul.VERSION)
        self.geladen = 0

        def herunterladen(ziel):
            self.geladen += 1
            _zip(ziel)  # liefert ein Archiv, dessen Prüfsumme nicht zur festen Prüfsumme passt

        self.modul.herunterladen = herunterladen

    def tearDown(self):
        self.tmp.cleanup()

    def test_pruefsumme_der_festen_version_ist_gesetzt(self):
        self.assertEqual(len(self.modul.SHA256), 64)
        self.assertTrue(self.modul.URL.startswith("https://www.python.org/ftp/python/"))
        self.assertIn(self.modul.VERSION, self.modul.URL)

    def test_falsche_pruefsumme_bricht_ab_und_verwirft_das_archiv(self):
        with self.assertRaises(SystemExit) as fehler:
            self.modul.einrichten(self.root / "ziel")
        self.assertIn("Prüfsumme", str(fehler.exception))
        self.assertFalse(self.archiv.exists())
        self.assertFalse((self.root / "ziel" / "python.exe").exists())

    def test_entpacken_suchpfade_und_wiederholung(self):
        self.modul.SHA256 = _zip(self.archiv)
        ziel = self.root / "ziel"
        self.modul.einrichten(ziel)
        self.assertTrue((ziel / "python.exe").is_file())
        # Suchpfade: Standardbibliothek, Ordner der python.exe, Ordner darüber (sidecar/, geometry/); kein "import site"
        self.assertEqual((ziel / "python312._pth").read_text(encoding="utf-8").split(), ["python312.zip", ".", ".."])
        self.assertEqual((ziel / ".version").read_text(encoding="utf-8").strip(), self.modul.VERSION)
        self.assertEqual(self.geladen, 0)
        # zweiter Aufruf: nichts erneut entpacken oder laden
        (ziel / "python.exe").write_bytes(b"geaendert")
        self.modul.einrichten(ziel)
        self.assertEqual((ziel / "python.exe").read_bytes(), b"geaendert")
        self.assertEqual(self.geladen, 0)

    def test_lädt_nur_bei_fehlendem_archiv(self):
        self.modul.SHA256 = _zip(self.root / "vorlage.zip")  # Prüfsumme des Archivs, das der Fake-Download liefert
        self.modul.einrichten(self.root / "ziel")
        self.assertEqual(self.geladen, 1)
        self.assertTrue((self.root / "ziel" / "python.exe").is_file())

    def test_neue_version_wird_neu_eingerichtet(self):
        self.modul.SHA256 = _zip(self.archiv)
        ziel = self.root / "ziel"
        self.modul.einrichten(ziel)
        (ziel / ".version").write_text("3.0.0\n", encoding="utf-8")
        (ziel / "python.exe").write_bytes(b"alt")
        self.modul.einrichten(ziel)
        self.assertEqual((ziel / "python.exe").read_bytes(), b"MZ")


if __name__ == "__main__":
    unittest.main()
