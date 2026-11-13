# AGENTS.md – CAD Studio

Windows-Programm für eigene 3D-Druck-Entwürfe (Bambu Lab P2S, Bauraum 256 mm). Ziel: Schubladen beliebiger Maße mit Gridfinity-kompatiblen Platten und Boxen bestücken und eigene einfache Teile zeichnen; Ausgabe sind STL, FCStd, Stückliste und Montageplan. Oberfläche Deutsch, Maße in Millimeter. Details: `README.md`, `docs/BEDIENUNGSANLEITUNG.md`, `TESTBERICHT.md`.

## Stack
- UI: Tauri 2 + React 18 + TypeScript + Vite (`ui/`, `src-tauri/`), 3D-Vorschau mit three.js.
- Sidecar: Python 3.11+ (`sidecar/`), lokaler HTTP-Dienst `127.0.0.1:47321`, JSON-Befehle über `POST /api` (`plane`, `save`, `load`, `generate`, `autofill`, `detect`, …), Sitzungs-Token und Origin-Prüfung.
- Geometrie: FreeCADCmd **1.1.x** als eigener Prozess (`sidecar/fc_worker.py`), Generator `geometry/hausraster` (Version 0.2-qs1, nur diese verwenden).

## Befehle
```bash
python -m sidecar.server        # Dienst starten
npm ci && npm run dev           # UI auf http://localhost:1420
npm test                        # Vitest
npm run build                   # tsc + vite build
python -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_eigenteil
FREECADCMD=/pfad/FreeCADCmd python -m unittest tests.test_abnahme tests.test_sonder tests.test_eigenteil   # braucht FreeCAD 1.1
npx playwright test             # E2E (Chromium nötig)
```
Unter Windows `FREECADCMD` auf `.../bin/freecadcmd.exe` setzen. `tests/` hat kein `__init__.py`: Module einzeln nennen, nicht `discover`.

## Architektur
- `sidecar/layout.py`: Projektdatei (`Projekt`, `Schublade`, `Box`), Plan, Prüfung, `auftrag_bauen` (beschreibt alle Körper als Liste von Teilen mit `rolle`).
- `sidecar/eigenteil.py`: gezeichnete Teile (Formen: rechteck, kreis, polygon; `loch`; `boden_mm`), Prüfung ohne FreeCAD.
- `sidecar/autofill.py`: füllt freie Rasterzellen zeilenweise mit der größten freien Box (kein Optimierer).
- `sidecar/fc_worker.py`: baut je `rolle` den Körper in FreeCAD (`grundplatte`, `box`, `phase4`, `besteck`, `verbinder`, `rastclip`, `eigen`). Randstreifen sind `rolle: eigen` (Teile S1, S2, …).
- `sidecar/engine.py`: startet FreeCAD, prüft jede STL unabhängig (`stlcheck.py`), schreibt Stückliste und Montageübersicht (`montage.py`).
- `Projekt.nur_eigene`: nur gezeichnete Teile, ohne Schublade/Platten/Montageplan.
- UI: `ui/src/App.tsx` (Schritte 1–5), `editor.tsx` (Boxen), `zeichenblatt.tsx` + `zeichnen.ts` (Zeichnen), `preview.tsx` (vereinfachte 3D-Vorschau, nicht die Druckgeometrie).
- Projektdateien `.cadstudio.json`, `FORMAT_VERSION` = 1; neue Felder sind optional, damit ältere Dateien laden.

## Regeln
- Erfolg gilt nur, wenn Dateien existieren, das Netz geschlossen ist und FCStd in einem zweiten Lauf als gültiger Körper lädt. Nie „bestanden“ melden, ohne dass der Lauf stattfand.
- Keine Cloud, kein Konto, keine Secrets. FreeCAD wird nicht mitgeliefert (LGPL) und nicht verändert.
- Der Dienst akzeptiert nur Aufrufe mit Token und lokaler Origin, relative Pfade landen im Benutzerordner `projekte`. Diese Sicherheitsprüfungen nicht aufweichen (`tests/test_server.py`).
- Spiele (Schublade 1,0 mm, Verbinder 0,20 mm) und Füllplatten sind ungetestet gedruckt; so kennzeichnen.
- Exportordner (`export_*/`) und Beispielausgaben nicht einchecken.

## Stand und nächste Schritte (Phase C)
Fertig: Randstreifen als Füllplatten, automatische Bestückung, Zeichnen (Rechteck/Kreis/Vieleck, Löcher, Sacklöcher), Modus „nur eigene Teile“, Platzieren eigener Teile in der Schublade (Lageplan, Kollisionsprüfung, Montageplan), beschriftetes PNG (5×7-Bitmap-Schrift in `montage.py`), Auto-Bestückung lässt Felder unter platzierten Teilen frei, Rückgängig/Wiederholen im Zeichenblatt (Verlauf in `zeichenblatt.tsx`), Eckenradius am Rechteck sowie obere Kante (Fase/Rundung) und untere Fase je Teil (`fc_worker._kante_bearbeiten`, Parameter `KanteObenArt/KanteObenMm/KanteUntenMm`). Wunschliste in `autofill.py` (`SORTEN` muss zum Katalog in `ui/src/layout.ts` passen); Formen mit `z_mm`/`h_mm` (Stufenteile, Gesamthöhe `eigenteil_hoehe`), Vorlagen in `zeichnen.ts` (`VORLAGEN`), Maßanzeige `massangaben`. SVG/DXF-Import (`ui/src/import.ts`: `leseSvg`, `leseDxf`, `zuFormen`; Gerade-Ungerade-Regel für Löcher, Vereinfachung, y-Spiegelung nur bei SVG), Maßeingabe im Blatt (`masseSetzen`, `masswertText`, `MassFeld`), Gedrehte Rechtecke (`winkel`, Drehung um die Mitte; Bounding-Box exakt in `form_bbox`/`formBox`, Kontur in `_kontur_abstand`), Muster/Spiegeln (`gitter`, `reihe`, `kreismuster`, `spiegeln` in `zeichnen.ts`, Panel `MusterPanel`; Eingaben als Text halten, nicht bei jedem Tastendruck klammern), Einrasten/Ausrichten (`fangpunkte`, `einrasten`, `verschiebenMitFang`, `ausrichten` in `zeichnen.ts`), eigene Vorlagen (`sidecar/vorlagen.py`, `vorlagen.json` im Programmordner, Befehle `vorlagen`/`vorlage_save`/`vorlage_delete`), Formoptionen `kante_art/kante_mm/schraege_mm/keil_mm` (Prüfung `form_zusatz_pruefen`, Bau `_form_koerper`/`_form_kanten` in `fc_worker.py`), Auto-Bestückung mit Kontakt-Bewertung und Füllstil (`stil`: einheitlich/gross/klein). Hinweis: Die BoundBox ist bei gekrümmten Flächen ~1 mm zu groß; deshalb `optimalBoundingBox()` verwenden (`_genaue_bbox`).
Offen, nach Nutzen sortiert:
1. Playwright-E2E für den Zeichen- und Auto-Fülle-Ablauf ergänzen und laufen lassen.
2. Zeichnen: Gruppen von Formen, Vieleck-Punkte bearbeiten, Import von SVG/DXF-Umrissen.
3. Auto-Bestückung: Wunschliste mit Gruppen („Besteck links, Kabel rechts“), Optimierer statt Greedy.
4. Windows-Installer auf einem echten PC starten und FreeCAD-Anbindung prüfen.

## Zusammenarbeit
Im selben Checkout schreibt nur ein Agent. Vor Arbeitsbeginn `git status` und `git pull --ff-only`. Branch: `cursor/cad-studio-phase-b-5939` (PR #1), `main` enthält nur ein leeres README. Kein Merge, Force-Push oder Löschen ohne ausdrückliche Zustimmung des Nutzers.
