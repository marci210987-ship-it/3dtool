# -*- coding: utf-8 -*-
"""5×7-Pixelschrift für Text an eigenen Teilen.

Jedes Zeichen besteht aus Rechtecken (ein Pixel = Schrifthöhe / 7). Dadurch braucht
der Text keine Schriftdatei und sieht auf jedem Rechner gleich aus. Ä, Ö, Ü und ß
werden zu AE, OE, UE und SS.
"""

from __future__ import annotations

from sidecar.montage import _FONT as _BASIS

_ZUSATZ = {
    " ": "00000 00000 00000 00000 00000 00000 00000",
    ".": "00000 00000 00000 00000 00000 01100 01100",
    ",": "00000 00000 00000 00000 01100 00100 01000",
    ":": "00000 01100 01100 00000 01100 01100 00000",
    "/": "00001 00010 00010 00100 01000 01000 10000",
    "+": "00000 00100 00100 11111 00100 00100 00000",
    "=": "00000 00000 11111 00000 11111 00000 00000",
    "(": "00010 00100 01000 01000 01000 00100 00010",
    ")": "01000 00100 00010 00010 00010 00100 01000",
    "!": "00100 00100 00100 00100 00100 00000 00100",
    "?": "01110 10001 00001 00010 00100 00000 00100",
    "%": "11001 11010 00010 00100 01000 01011 10011",
}
FONT = {**_BASIS, **_ZUSATZ}
MAX_ZEICHEN = 40
MIN_PIXEL_MM = 0.4


def normalisiert(text: str) -> str:
    t = str(text).upper()
    for alt, neu in (("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "SS")):
        t = t.replace(alt, neu)
    return t


def unbekannte_zeichen(text: str) -> list[str]:
    return sorted({z for z in normalisiert(text) if z not in FONT})


def text_groesse(text: str, schrift_mm: float) -> tuple[float, float]:
    """Breite und Höhe des Textes in mm."""
    n = len(normalisiert(text))
    px = float(schrift_mm) / 7.0
    return (max(0, 6 * n - 1) * px, 7 * px)


def text_rechtecke(text: str, x: float, y: float, schrift_mm: float) -> list[tuple[float, float, float, float]]:
    """Rechtecke (x, y, b, t) in mm; waagerechte Pixelreihen sind zusammengefasst. Ursprung links unten."""
    px = float(schrift_mm) / 7.0
    ergebnis = []
    for i, zeichen in enumerate(normalisiert(text)):
        muster = FONT.get(zeichen)
        if not muster:
            continue
        for zeile, bits in enumerate(muster.split()):
            spalte = 0
            while spalte < 5:
                if bits[spalte] != "1":
                    spalte += 1
                    continue
                ende = spalte
                while ende + 1 < 5 and bits[ende + 1] == "1":
                    ende += 1
                links = x + (i * 6 + spalte) * px
                unten = y + (6 - zeile) * px
                ergebnis.append((round(links, 4), round(unten, 4), round((ende - spalte + 1) * px, 4), round(px, 4)))
                spalte = ende + 1
    return ergebnis
