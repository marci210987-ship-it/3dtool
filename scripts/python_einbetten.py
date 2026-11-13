# -*- coding: utf-8 -*-
"""Richtet das mitgelieferte Python für den Windows-Installer ein.

Lädt das offizielle „embeddable package“ von python.org (feste Version, geprüft mit SHA256),
entpackt es nach ``src-tauri/python`` und passt die Suchpfade so an, dass ``python -m sidecar.server``
die Quellen im Installationsordner findet. Der Dienst nutzt nur die Standardbibliothek, deshalb
braucht der Rechner des Benutzers kein eigenes Python.

Aufruf::

    python scripts/python_einbetten.py [Zielordner]

Ohne Angabe ist das Ziel ``src-tauri/python``. Eine bereits eingerichtete Version wird nicht erneut geladen.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "3.12.10"
URL = "https://www.python.org/ftp/python/%s/python-%s-embed-amd64.zip" % (VERSION, VERSION)
SHA256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"
# python312._pth: Standardbibliothek, Ordner der python.exe, Ordner darüber (dort liegen sidecar/ und geometry/)
PTH_NAME = "python312._pth"
PTH_INHALT = "python312.zip\n.\n..\n"

ROOT = Path(__file__).resolve().parents[1]


def herunterladen(ziel: Path) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    print("Lade %s" % URL)
    with urllib.request.urlopen(URL, timeout=120) as antwort, open(ziel, "wb") as datei:
        while True:
            block = antwort.read(1 << 20)
            if not block:
                break
            datei.write(block)


def pruefsumme(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as datei:
        for block in iter(lambda: datei.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def einrichten(ziel: Path) -> None:
    marke = ziel / ".version"
    if (ziel / "python.exe").is_file() and marke.is_file() and marke.read_text(encoding="utf-8").strip() == VERSION:
        print("Python %s ist bereits eingerichtet: %s" % (VERSION, ziel))
        return
    cache = ROOT / ".cache" / "python-embed"
    archiv = cache / ("python-%s-embed-amd64.zip" % VERSION)
    if not archiv.is_file() or pruefsumme(archiv) != SHA256:
        herunterladen(archiv)
    ist = pruefsumme(archiv)
    if ist != SHA256:
        archiv.unlink(missing_ok=True)
        raise SystemExit("Prüfsumme stimmt nicht: erwartet %s, erhalten %s" % (SHA256, ist))
    ziel.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archiv) as zf:
        zf.extractall(ziel)
    (ziel / PTH_NAME).write_text(PTH_INHALT, encoding="utf-8")
    marke.write_text(VERSION + "\n", encoding="utf-8")
    print("Python %s eingerichtet: %s" % (VERSION, ziel))


def selbsttest(ziel: Path) -> None:
    """Startet das eingebettete Python und importiert, was der Dienst braucht (nur unter Windows)."""
    exe = ziel / "python.exe"
    if sys.platform != "win32":
        print("Selbsttest übersprungen (kein Windows).")
        return
    code = "import sys, json, http.server, socket, zlib, winreg, struct, secrets, shutil, csv; print(sys.version.split()[0])"
    ergebnis = subprocess.run([str(exe), "-c", code], capture_output=True, text=True, timeout=60)
    if ergebnis.returncode != 0:
        raise SystemExit("Selbsttest fehlgeschlagen:\n" + ergebnis.stdout + ergebnis.stderr)
    print("Selbsttest bestanden, Python %s" % ergebnis.stdout.strip())


def main() -> None:
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "src-tauri" / "python"
    einrichten(ziel)
    selbsttest(ziel)


if __name__ == "__main__":
    main()
