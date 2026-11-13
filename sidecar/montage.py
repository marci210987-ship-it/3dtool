# -*- coding: utf-8 -*-
"""Stückliste und Montageübersicht (SVG, HTML, PNG, PDF)."""

from __future__ import annotations

import csv
import json
import zlib
import struct
from pathlib import Path


DICHTE = {"PLA": 1.24, "PETG": 1.27, "ABS": 1.04}


def _masse_g(volumen_mm3: float, material: str) -> float | None:
    if not volumen_mm3:
        return None
    dichte = DICHTE.get(material.upper(), DICHTE["PLA"])
    return round(volumen_mm3 / 1000.0 * dichte, 1)


def schreibe_stueckliste(pfad_json: Path, pfad_csv: Path, zeilen: list[dict], hinweise: list[str]) -> None:
    pfad_json.write_text(
        json.dumps({"zeilen": zeilen, "hinweise": hinweise}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with pfad_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Teil",
                "Bezeichnung",
                "Anzahl",
                "Breite_mm",
                "Tiefe_mm",
                "Hoehe_mm",
                "Material",
                "Masse_geschaetzt_g",
                "Bauraum",
                "STL",
                "FCStd",
                "Pruefung",
            ],
            delimiter=";",
        )
        writer.writeheader()
        for zeile in zeilen:
            writer.writerow({k: zeile.get(k, "") for k in writer.fieldnames})


def _svg(projekt_name: str, ansicht: dict, boxen: list[dict], breite: float, tiefe: float) -> str:
    margin = 18
    zeichnung_b = 920
    zeichnung_h = 640
    scale = min((zeichnung_b - 2 * margin) / breite, (zeichnung_h - 2 * margin) / tiefe)
    def X(mm):
        return margin + mm * scale
    def Y(mm):
        # vorne ist oben in der Ansicht
        return margin + mm * scale
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{zeichnung_b}" height="{zeichnung_h + 80}" viewBox="0 0 {zeichnung_b} {zeichnung_h + 80}">',
        '<rect width="100%" height="100%" fill="#f7f4ee"/>',
        f'<text x="{margin}" y="28" font-family="Segoe UI, sans-serif" font-size="18" fill="#1c1915">{_xml(projekt_name)} – Montageübersicht</text>',
        f'<text x="{margin}" y="48" font-family="Segoe UI, sans-serif" font-size="12" fill="#5c564c">Draufsicht, maßstäblich. Vorne ist oben. Maße in Millimeter. Raster {ansicht.get("raster_mm", 42):.0f} mm.</text>',
    ]
    # Schublade
    parts.append(
        f'<rect x="{X(0):.2f}" y="{Y(0):.2f}" width="{breite * scale:.2f}" height="{tiefe * scale:.2f}" '
        'fill="#fff" stroke="#1c1915" stroke-width="2"/>'
    )
    ox = ansicht.get("ursprung_x_mm", 0)
    oy = ansicht.get("ursprung_y_mm", 0)
    ex = int(ansicht.get("einheiten_x") or 0)
    ey = int(ansicht.get("einheiten_y") or 0)
    raster = float(ansicht.get("raster_mm") or 42)
    for i in range(ex + 1):
        x = X(ox + i * raster)
        parts.append(
            f'<line x1="{x:.2f}" y1="{Y(oy):.2f}" x2="{x:.2f}" y2="{Y(oy + ey * raster):.2f}" stroke="#e4ddd0" stroke-width="1"/>'
        )
    for j in range(ey + 1):
        y = Y(oy + j * raster)
        parts.append(
            f'<line x1="{X(ox):.2f}" y1="{y:.2f}" x2="{X(ox + ex * raster):.2f}" y2="{y:.2f}" stroke="#e4ddd0" stroke-width="1"/>'
        )
    for platte in ansicht.get("platten") or []:
        lage = platte["lage"]
        parts.append(
            f'<rect x="{X(lage["links_mm"]):.2f}" y="{Y(lage["vorne_mm"]):.2f}" '
            f'width="{lage["breite_mm"] * scale:.2f}" height="{lage["tiefe_mm"] * scale:.2f}" '
            'fill="none" stroke="#0f6e6e" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{X(lage["links_mm"]) + 6:.2f}" y="{Y(lage["vorne_mm"]) + 16:.2f}" '
            f'font-family="Segoe UI, sans-serif" font-size="13" fill="#0f6e6e">{_xml(platte["id"])} '
            f'{platte["einheiten_x"]}×{platte["einheiten_y"]}</text>'
        )
    farben = ["#f3d2a4", "#c9dfc4", "#f0c9cf", "#c9d7f0", "#e6d4f2", "#f7e3a1"]
    for index, box in enumerate(boxen):
        farbe = "#d9d2c3" if box.get("art") == "eigen" else farben[index % len(farben)]
        parts.append(
            f'<rect x="{X(box["links_mm"]):.2f}" y="{Y(box["vorne_mm"]):.2f}" '
            f'width="{box["breite_mm"] * scale:.2f}" height="{box["tiefe_mm"] * scale:.2f}" '
            f'fill="{farbe}" fill-opacity="0.85" stroke="#1c1915" stroke-width="1.4" rx="3"/>'
        )
        parts.append(
            f'<text x="{X(box["links_mm"]) + 5:.2f}" y="{Y(box["vorne_mm"]) + box["tiefe_mm"] * scale / 2:.2f}" '
            f'font-family="Segoe UI, sans-serif" font-size="12" fill="#1c1915">{_xml(box["id"])}</text>'
        )
    for verb in ansicht.get("verbinder") or []:
        parts.append(
            f'<circle cx="{X(verb["x_mm"]):.2f}" cy="{Y(verb["y_mm"]):.2f}" r="3.2" fill="#a33b2b"/>'
        )
    parts.append(
        f'<text x="{margin}" y="{zeichnung_h + 28}" font-family="Segoe UI, sans-serif" font-size="12" fill="#5c564c">'
        "Türkise Rahmen: Grundplatten. Farbige Flächen: Boxen, graue Flächen: eigene Teile. "
        "Rote Punkte: Plattenverbinder an den Rippen. Randstreifen (S1, ...) werden lose daneben gelegt.</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def schreibe_uebersicht(
    out_dir: Path,
    projekt_name: str,
    schublade: dict,
    ansicht: dict,
    boxen_zeichnung: list[dict],
    hinweise: list[str],
) -> dict:
    breite = float(schublade["innenbreite_mm"])
    tiefe = float(schublade["innentiefe_mm"])
    svg = _svg(projekt_name, ansicht, boxen_zeichnung, breite, tiefe)
    svg_path = out_dir / "Montageuebersicht.svg"
    html_path = out_dir / "Montageuebersicht.html"
    png_path = out_dir / "Montageuebersicht.png"
    pdf_path = out_dir / "Montageuebersicht.pdf"
    svg_path.write_text(svg, encoding="utf-8")
    hinweis_html = "".join("<li>%s</li>" % _xml(h) for h in hinweise)
    html_path.write_text(
        """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><title>Montageübersicht</title>
<style>body{font-family:Segoe UI,sans-serif;background:#f7f4ee;color:#1c1915;margin:24px} li{margin:6px 0}</style>
</head><body>
<h1>%s</h1>
<p>Schublade innen %s × %s mm, nutzbare Höhe %s mm. Spiel zur Wand %s mm (ungeprüfte Vorgabe).</p>
%s
<ul>%s</ul>
</body></html>
"""
        % (
            _xml(projekt_name),
            schublade["innenbreite_mm"],
            schublade["innentiefe_mm"],
            schublade["nutzhoehe_mm"],
            schublade["spiel_mm"],
            svg,
            hinweis_html,
        ),
        encoding="utf-8",
    )
    _png_plan(png_path, breite, tiefe, ansicht, boxen_zeichnung, projekt_name)
    _pdf_plan(pdf_path, breite, tiefe, ansicht, boxen_zeichnung, projekt_name, hinweise)
    return {"svg": str(svg_path), "html": str(html_path), "png": str(png_path), "pdf": str(pdf_path)}


_FONT = {
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "-": "00000 00000 00000 11111 00000 00000 00000", "_": "00000 00000 00000 00000 00000 00000 11111",
    "×": "00000 10001 01010 00100 01010 10001 00000",
}


def _text_pixel(text: str, groesse: int, max_breite: int) -> list[tuple[int, int]]:
    """Pixelpositionen (x, y) für Text in einer 5×7-Schrift, auf max_breite gekürzt."""
    pixel = []
    schritt = 6 * groesse
    stellen = max(0, max_breite // schritt)
    for i, zeichen in enumerate(text.upper()[:stellen]):
        muster = _FONT.get(zeichen)
        if not muster:
            continue
        for zeile, bits in enumerate(muster.split()):
            for spalte, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(groesse):
                        for dx in range(groesse):
                            pixel.append((i * schritt + spalte * groesse + dx, zeile * groesse + dy))
    return pixel


def _png_plan(path: Path, breite, tiefe, ansicht, boxen, titel: str) -> None:
    w, h = 1100, 780
    margin = 40
    scale = min((w - 2 * margin) / breite, (h - 80 - 2 * margin) / tiefe)
    ox = margin
    oy = 70

    def px(mm_x, mm_y):
        return int(ox + mm_x * scale), int(oy + mm_y * scale)

    bild = [[(247, 244, 238) for _ in range(w)] for _ in range(h)]

    def rect(x0, y0, x1, y1, farbe, rand=None):
        x0, x1 = sorted((max(0, x0), min(w - 1, x1)))
        y0, y1 = sorted((max(0, y0), min(h - 1, y1)))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if rand and (x == x0 or x == x1 or y == y0 or y == y1):
                    bild[y][x] = rand
                elif not rand:
                    bild[y][x] = farbe
                elif x0 < x < x1 and y0 < y < y1:
                    bild[y][x] = farbe

    def beschriften(text, x0, y0, x1, farbe, groesse=2):
        for dx, dy in _text_pixel(text, groesse, max(0, x1 - x0 - 6)):
            xx, yy = x0 + 4 + dx, y0 + 4 + dy
            if 0 <= xx < w and 0 <= yy < h:
                bild[yy][xx] = farbe

    beschriften(titel + " - MONTAGEUEBERSICHT", 40, 20, w - 40, (28, 25, 21), 2)
    x1, y1 = px(breite, tiefe)
    rect(ox, oy, x1, y1, (255, 255, 255), (28, 25, 21))
    for platte in ansicht.get("platten") or []:
        lage = platte["lage"]
        a, b = px(lage["links_mm"], lage["vorne_mm"])
        c, d = px(lage["links_mm"] + lage["breite_mm"], lage["vorne_mm"] + lage["tiefe_mm"])
        rect(a, b, c, d, (255, 255, 255), (15, 110, 110))
        beschriften("%s %d×%d" % (platte["id"], platte["einheiten_x"], platte["einheiten_y"]), a, b, c, (15, 110, 110))
    farben = [(243, 210, 164), (201, 223, 196), (240, 201, 207), (201, 215, 240)]
    for index, box in enumerate(boxen):
        a, b = px(box["links_mm"], box["vorne_mm"])
        c, d = px(box["links_mm"] + box["breite_mm"], box["vorne_mm"] + box["tiefe_mm"])
        farbe = (217, 210, 195) if box.get("art") == "eigen" else farben[index % len(farben)]
        rect(a, b, c, d, farbe, (28, 25, 21))
        beschriften(str(box["id"]), a, b + (d - b) // 2 - 7, c, (28, 25, 21), 2 if c - a > 90 else 1)
    raw = bytearray()
    for row in bild:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))
    _write_png(path, w, h, bytes(raw))


def _write_png(path: Path, width: int, height: int, raw: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def _pdf_escape(text: str) -> str:
    raw = text.encode("latin-1", errors="replace")
    out = []
    for byte in raw:
        if byte in (40, 41, 92):
            out.append("\\%s" % chr(byte))
        elif 32 <= byte < 127:
            out.append(chr(byte))
        else:
            out.append("\\%03o" % byte)
    return "".join(out)


def _pdf_plan(path: Path, breite, tiefe, ansicht, boxen, titel: str, hinweise: list[str]) -> None:
    page_w, page_h = 842, 595
    margin = 36
    scale = min((page_w - 280) / breite, (page_h - 80) / tiefe)
    ox, oy = margin, 48

    def X(mm):
        return ox + mm * scale

    def Y(mm):
        # PDF-Ursprung unten links; vorne (mm=0) soll oben stehen
        return page_h - 36 - mm * scale

    ops = ["0.97 0.96 0.93 rg 0 0 842 595 re f", "0 0 0 RG 0.8 w"]
    ops.append("BT /F1 16 Tf 36 560 Td (%s) Tj ET" % _pdf_escape(titel + " – Montageübersicht"))
    ops.append("BT /F1 10 Tf 36 544 Td (Draufsicht, vorn oben, Millimeter. Rot markierte Verbinder sitzen auf den Plattenrippen.) Tj ET")
    ops.append("%.2f %.2f %.2f %.2f re S" % (X(0), Y(tiefe), breite * scale, tiefe * scale))
    ops.append("0.06 0.43 0.43 RG 1.2 w")
    for platte in ansicht.get("platten") or []:
        lage = platte["lage"]
        ops.append(
            "%.2f %.2f %.2f %.2f re S" % (
                X(lage["links_mm"]),
                Y(lage["vorne_mm"] + lage["tiefe_mm"]),
                lage["breite_mm"] * scale,
                lage["tiefe_mm"] * scale,
            )
        )
        ops.append(
            "BT /F1 9 Tf %.2f %.2f Td (%s) Tj ET"
            % (X(lage["links_mm"]) + 4, Y(lage["vorne_mm"]) - 14, _pdf_escape(platte["id"]))
        )
    ops.append("0 0 0 RG 0.6 w")
    for index, box in enumerate(boxen):
        ops.append(
            "%.2f %.2f %.2f %.2f re S" % (
                X(box["links_mm"]),
                Y(box["vorne_mm"] + box["tiefe_mm"]),
                box["breite_mm"] * scale,
                box["tiefe_mm"] * scale,
            )
        )
        ops.append(
            "BT /F1 9 Tf %.2f %.2f Td (%s) Tj ET"
            % (X(box["links_mm"]) + 3, Y(box["vorne_mm"]) - 12, _pdf_escape(box["id"]))
        )
    ops.append("0.64 0.23 0.17 rg")
    for verb in ansicht.get("verbinder") or []:
        ops.append("%.2f %.2f 2 0 360 arc f" % (X(verb["x_mm"]), Y(verb["y_mm"])))
    text_x = page_w - 250
    ops.append("BT /F1 11 Tf %d 520 Td (Teile) Tj ET" % text_x)
    y = 500
    for platte in ansicht.get("platten") or []:
        zeile = "%s  %d×%d  %.0f×%.0f mm" % (
            platte["id"], platte["einheiten_x"], platte["einheiten_y"], platte["breite_mm"], platte["tiefe_mm"]
        )
        ops.append("BT /F1 9 Tf %d %d Td (%s) Tj ET" % (text_x, y, _pdf_escape(zeile)))
        y -= 14
    y -= 8
    for box in boxen:
        zeile = "%s  %s" % (box["id"], box.get("name", ""))
        ops.append("BT /F1 9 Tf %d %d Td (%s) Tj ET" % (text_x, y, _pdf_escape(zeile[:42])))
        y -= 14
    y -= 10
    for hinweis in hinweise[:6]:
        ops.append("BT /F1 8 Tf 36 %d Td (%s) Tj ET" % (max(24, y), _pdf_escape(hinweis[:110])))
        y -= 12
    stream = "\n".join(ops).encode("latin-1", errors="replace")
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Count 1 /Kids [3 0 R] >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(b"4 0 obj << /Length %d >> stream\n" % len(stream) + stream + b"\nendstream endobj\n")
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> endobj\n")
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref = len(pdf)
    pdf.extend(("xref\n0 %d\n" % (len(offsets))).encode())
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(("%010d 00000 n \n" % off).encode())
    pdf.extend(
        ("trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(offsets), xref)).encode()
    )
    path.write_bytes(pdf)
