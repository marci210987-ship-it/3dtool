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
python -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_eigenteil tests.test_ersatzteil tests.test_kabel tests.test_gehaeuse tests.test_erweitert tests.test_autofill_optimierer
FREECADCMD=/pfad/FreeCADCmd python -m unittest tests.test_abnahme tests.test_sonder tests.test_eigenteil   # braucht FreeCAD 1.1
npx playwright test             # E2E, startet Dienst und UI selbst (Chromium: npx playwright install chromium); FREECADCMD für den Export
python scripts/python_einbetten.py   # mitgeliefertes Python für den Installer einrichten (vor `tauri build`)
```
Unter Windows `FREECADCMD` auf `.../bin/freecadcmd.exe` setzen. `tests/` hat kein `__init__.py`: Module einzeln nennen, nicht `discover`.

## Architektur
- `sidecar/layout.py`: Projektdatei (`Projekt`, `Schublade`, `Box`), Plan, Prüfung, `auftrag_bauen` (beschreibt alle Körper als Liste von Teilen mit `rolle`).
- `sidecar/eigenteil.py`: gezeichnete Teile (Formen: rechteck, kreis, polygon; `loch`; `boden_mm`), Prüfung ohne FreeCAD.
- `sidecar/ersatzteil.py` und `ersatzteil_geom.py`: Bibliothek parametrischer Ersatzteile (Prüfung ohne FreeCAD, Körper nur in FreeCAD). Projektfelder `ersatzteile` und `nur_ersatz`.
- `sidecar/kabel.py` und `kabel_geom.py`: modulares Kabelmanagement (Kanal, Ecke, Endkappe, Wandhalter, Auslass, optionaler Deckel). Gleiches Profil je System. Projektfelder `kabel` und `nur_kabel`. Die geometrische Passung (Schnittvolumen und Lücke) läuft in FreeCAD über den Befehl `kabel_passung`.
- `sidecar/gehaeuse.py` und `gehaeuse_geom.py`: Elektronikgehäuse (Innenmaß, Schraub- oder Schiebedeckel, Platinenstützen, Öffnungen). Projektfelder `gehaeuse` und `nur_gehaeuse`. Passung über `gehaeuse_passung`.
- `sidecar/autofill.py`: füllt freie Rasterzellen zeilenweise mit der größten freien Box (kein Optimierer).
- `sidecar/fc_worker.py`: baut je `rolle` den Körper in FreeCAD (`grundplatte`, `box`, `phase4`, `besteck`, `verbinder`, `rastclip`, `eigen`, `ersatzteil`, `kabel`, `gehaeuse`). Randstreifen sind `rolle: eigen` (Teile S1, S2, …).
- `sidecar/engine.py`: startet FreeCAD, prüft jede STL unabhängig (`stlcheck.py`), schreibt Stückliste und Montageübersicht (`montage.py`).
- `Projekt.nur_eigene`: nur gezeichnete Teile, ohne Schublade/Platten/Montageplan. `nur_ersatz`, `nur_kabel` und `nur_gehaeuse` genauso: beim Wechsel in einen anderen Bereich werden die anderen Schalter gelöscht.
- UI: `ui/src/App.tsx` (Schritte 1–5), `editor.tsx` (Boxen), `zeichenblatt.tsx` + `zeichnen.ts` (Zeichnen), `ersatzteile.tsx`, `kabel.tsx`, `gehaeuse.tsx`, `preview.tsx` (vereinfachte 3D-Vorschau, nicht die Druckgeometrie).
- Projektdateien `.cadstudio.json`, `FORMAT_VERSION` = 1; neue Felder sind optional, damit ältere Dateien laden.

## Regeln
- Erfolg gilt nur, wenn Dateien existieren, das Netz geschlossen ist und FCStd in einem zweiten Lauf als gültiger Körper lädt. Nie „bestanden“ melden, ohne dass der Lauf stattfand.
- Keine Cloud, kein Konto, keine Secrets. FreeCAD wird nicht mitgeliefert (LGPL) und nicht verändert.
- Der Dienst akzeptiert nur Aufrufe mit Token und lokaler Origin, relative Pfade landen im Benutzerordner `projekte`. Diese Sicherheitsprüfungen nicht aufweichen (`tests/test_server.py`).
- Spiele (Schublade 1,0 mm, Verbinder 0,20 mm) und Füllplatten sind ungetestet gedruckt; so kennzeichnen.
- Exportordner (`export_*/`) und Beispielausgaben nicht einchecken.

## Stand und nächste Schritte (Phase C)
Fertig: Randstreifen als Füllplatten, automatische Bestückung, Zeichnen (Rechteck/Kreis/Vieleck, Löcher, Sacklöcher), Modus „nur eigene Teile“, Platzieren eigener Teile in der Schublade (Lageplan, Kollisionsprüfung, Montageplan), beschriftetes PNG (5×7-Bitmap-Schrift in `montage.py`), Auto-Bestückung lässt Felder unter platzierten Teilen frei, Rückgängig/Wiederholen im Zeichenblatt (Verlauf in `zeichenblatt.tsx`), Eckenradius am Rechteck sowie obere Kante (Fase/Rundung) und untere Fase je Teil (`fc_worker._kante_bearbeiten`, Parameter `KanteObenArt/KanteObenMm/KanteUntenMm`). Wunschliste in `autofill.py` (`SORTEN` muss zum Katalog in `ui/src/layout.ts` passen); Formen mit `z_mm`/`h_mm` (Stufenteile, Gesamthöhe `eigenteil_hoehe`), Vorlagen in `zeichnen.ts` (`VORLAGEN`), Maßanzeige `massangaben`. SVG/DXF-Import (`ui/src/import.ts`: `leseSvg`, `leseDxf`, `zuFormen`; Gerade-Ungerade-Regel für Löcher, Vereinfachung, y-Spiegelung nur bei SVG), Maßeingabe im Blatt (`masseSetzen`, `masswertText`, `MassFeld`), Gedrehte Rechtecke (`winkel`, Drehung um die Mitte; Bounding-Box exakt in `form_bbox`/`formBox`, Kontur in `_kontur_abstand`), Muster/Spiegeln (`gitter`, `reihe`, `kreismuster`, `spiegeln` in `zeichnen.ts`, Panel `MusterPanel`; Eingaben als Text halten, nicht bei jedem Tastendruck klammern), Einrasten/Ausrichten (`fangpunkte`, `einrasten`, `verschiebenMitFang`, `ausrichten` in `zeichnen.ts`), eigene Vorlagen (`sidecar/vorlagen.py`, `vorlagen.json` im Programmordner, Befehle `vorlagen`/`vorlage_save`/`vorlage_delete`), Formoptionen `kante_art/kante_mm/schraege_mm/keil_mm` (Prüfung `form_zusatz_pruefen`, Bau `_form_koerper`/`_form_kanten` in `fc_worker.py`), Auto-Bestückung mit Kontakt-Bewertung und Füllstil (`stil`: einheitlich/gross/klein). Installer: `scripts/python_einbetten.py` (feste Python-Version mit SHA256), `src-tauri/src/lib.rs` (bevorzugt `<Ressourcen>/python/python.exe`, ohne Konsolenfenster, Log `%APPDATA%\CADStudio\dienst.log`), CI in `.github/workflows/windows.yml` (Jobs `tests` und `installer`). Hinweis: Die BoundBox ist bei gekrümmten Flächen ~1 mm zu groß; deshalb `optimalBoundingBox()` verwenden (`_genaue_bbox`).
Ersatzteil-Generator (eigener Bereich, nicht der gezeichnete Modus): Kabelclip, Distanzhülse, Unterlegscheibe, Wandhaken, Möbelfuß, Drehknopf, Stopfen, Winkel. UI `ui/src/ersatzteile.tsx`, Export über `rolle: ersatzteil`. Kabelmanagement: gerader Kanal (geteilt auf 250 mm, Buchse/Stecker, Spiel standardmäßig 0,20 mm), 90°-Ecke, Endkappe, Wandhalter, Kabelauslass, optionaler Deckel. UI `ui/src/kabel.tsx`, Export über `rolle: kabel`. Elektronikgehäuse: Innenmaß, Schraubdeckel (M3 oder M2,5, optionale Senkung) oder Schiebedeckel, Platinenstützen (Pi 4, Pi 5, Arduino Uno R3 oder eigenes Rechteck), rechteckige und runde Wandöffnungen, Lüftungsschlitze, Wandlaschen. UI `ui/src/gehaeuse.tsx`, Export von Korpus und Deckel über `rolle: gehaeuse`.

Erweiterungen (14.11.2026, Tests mit FreeCAD grün, nicht gedruckt): Langloch (`langlochAus`, Rechteck mit vollem Radius), Vieleck-Eckenradius (`_polygon_gerundet`), Senkung/Gegenbohrung/Sechskant an runden Löchern (`senk_*`, `_senk_werkzeuge`), Text als Pixelschrift (`sidecar/pixelschrift.py`, Form `text`), Gruppen (`gruppe*` in `zeichnen.ts`, Umschalt-Klick), Seitenlöcher (`Eigenteil.seitenloecher`, `_seitenloch_werkzeug`), Drehprofil (`Eigenteil.profil`, `dreh_x_mm/dreh_y_mm`, `_profil_koerper`), Druckhinweise (`sidecar/druckpruefung_geom.py`, nur Rolle `eigen`, Hinweise landen in `hinweise` des Ergebnisses). UI: `ui/src/erweitert.tsx`, `felder.tsx`. Tests: `tests/test_erweitert.py`, `tests/e2e/erweitert.spec.ts`.

3D-Ansicht: `ui/src/ansicht3d.tsx` zeigt die echte Geometrie (FreeCAD-Netze über Befehl `vorschau`, `engine.vorschau_bauen` mit kurz offener FreeCAD-Sitzung, Worker `vorschau_netze`), im Zeichnen, bei Ersatzteilen, Kabeln und Gehäuse. Auto-Bestückung: Wünsche mit `seite` und `gruppe`, Strahlsuche und Verbesserung der Füllung durch Verzweigen und Beschneiden mit fester Knotenzahl (`autofill.py`, Konstanten oben; Tests `tests/test_autofill_optimierer.py`).

Schnitt, Messen, Ausrichtung, Schrauben (15.11.2026): `ui/src/schnitt.ts` (Schnittebene und Messen, three.js-Clipping in `ansicht3d.tsx`), `ui/src/ausrichtung.ts` (sechs Lagen auf dem Netz bewerten), `ui/src/schrauben.ts` (Tabelle M2 bis M5, `lochDurchmesser`, `kopfFelder`, `schraubdom`), Panels `SchraubenPanel` und `DomPanel` in `erweitert.tsx`. Aus der Ausrichtung folgte: Gehäuse-Schraubdeckel, Stopfen und Knopf werden in `fc_worker._shapes_fuer` gedreht (`DRUCK_UMGEDREHT`, `_umdrehen`). Kabelkanal, Ecke und Auslass haben an der Stufe Buchse/Boden einen großen Überhang (nicht geändert, Entscheidung offen).

Offen, nach Nutzen sortiert:
1. Playwright-E2E für den Zeichen- und Auto-Fülle-Ablauf ergänzen und laufen lassen.
2. Zeichnen: Skizzen mit Bedingungen, Text in echten Schriftarten, Gewinde. (Gruppen sind fertig; Vieleck-Punkte bearbeiten ist fertig: Griffe an Ecken und Kanten, Punktfelder, Entf; Hilfsfunktionen `punktVerschieben`, `punktEinfuegen`, `punktLoeschen`, `polygonSelbstschnitt` in `zeichnen.ts`.)
3. Auto-Bestückung: Gewichte der Strahlsuche an echten Schubladen abstimmen, Boxen verschiedener Höhe berücksichtigen.
4. Windows-Installer auf einem echten PC starten und FreeCAD-Anbindung prüfen.

## Zusammenarbeit
Im selben Checkout schreibt nur ein Agent. Vor Arbeitsbeginn `git status` und `git pull --ff-only`. `main` enthält die Anwendung (Stand 16.11.2026); Erweiterungen auf einem eigenen `codex/`-Branch bearbeiten. Die frühere Phase-B-Branchangabe ist historisch. Kein Merge, Force-Push oder Löschen ohne ausdrückliche Zustimmung des Nutzers.

## Parametrische Positionierung (16.11.2026)
`ui/src/positionierung.ts`: optionale `form_id` und `position.x/y` an Formen. Alle Formänderungen im Zeichenblatt über `positionenAufloesen` führen. IDs sind innerhalb eines Teils stabil; Kopien bekommen eigene IDs/freie Positionen. Manuelle Positionseingaben lösen die betroffene Achse. Kontext-UI: `position-panel.tsx`. Bezug für Bauteilmitte/Randabstand ist der achsparallele Rahmen freier Materialformen; keine Konturabstände und kein Drehprofilrahmen. Der Sidecar speichert Metadaten unverändert, Export/Vorschau nutzen bereits aufgelöste Koordinaten. Details: `docs/POSITIONIERUNG.md`. Python-Test zusätzlich: `python -m unittest tests.test_positionierung` (FreeCAD-Test optional über `FREECADCMD`).
