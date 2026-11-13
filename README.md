# CAD Studio

Windows-Programm für die eigenen 3D-Druck-Entwürfe. Phase B enthält den Schubladen-Konfigurator. Die Oberfläche ist Deutsch, die Maße sind Millimeter.

Der Druckerbezug ist ein Bambu Lab P2S, Bauraum 256 × 256 × 256 mm. Das Raster kommt aus Hausraster 0.2-qs1: 42 mm je Feld, 7 mm je Höhenstufe, anschlussfähig an Gridfinity. Es wird nur diese korrigierte Generatorversion verwendet. Die älteren Grundplatten ohne QS1 sind fehlerhaft und werden nicht geladen.

## Architektur

Die Oberfläche ist eine Tauri-2-Anwendung mit React und TypeScript. Sie spricht mit einem lokalen Python-Dienst auf `127.0.0.1:47321`. Der Dienst plant die Schublade mit `plane_schublade` aus den mitgelieferten Hausraster-Quellen und startet für die Körper **FreeCADCmd 1.1** als eigenen Prozess. Anfragen und Antworten sind JSON. FreeCAD wird nicht mitgeliefert (Lizenz LGPL-2.0-or-later) und nicht verändert.

Projektdateien sind JSON (`.cadstudio.json`) auf dem eigenen Rechner. Es gibt keine Cloud und kein Abo.

```
geometry/hausraster/   Generator 0.2-qs1 (const, plan, geom, fcstd, Phase 3 und 4, Makros, Workbenches)
sidecar/               Planung, FreeCAD-Sitzung, Exportprüfung, Stückliste, Montageplan
ui/                    Deutsche Oberfläche
src-tauri/             Fenster, Start des Dienstes, Dateidialog
examples/              Beispielprojekt der Abnahmeschublade 480 × 420 mm
```

Eine Änderung an einer Box erzeugt die Geometrie neu. Das Tabellenblatt `HIER_MASSE_AENDERN` in den FCStd-Dateien ist nicht live mit dem Körper verbunden; ohne erneuten Generatorlauf bliebe der alte Körper stehen.

Randstreifen, die nicht mehr in eine Außenplatte passen, werden nur genannt. Einen druckbaren Streifenkörper gibt es im Generator nicht, und CAD Studio erfindet keinen.

Schubladenspiel 1,0 mm und Verbinder-Spiel 0,20 mm sind Vorgaben in den Einstellungen und je Projekt änderbar. Sie sind nicht an einem gedruckten Teil geprüft.

## Voraussetzungen unter Windows

1. [FreeCAD 1.1](https://www.freecad.org/) für Windows installieren. Nicht 0.21 und nicht eine andere Hauptversion. Der Installer von CAD Studio enthält FreeCAD nicht.
2. Python 3.11 oder neuer, aufrufbar als `python` oder `py`. Der Dienst läuft darin und steuert FreeCADCmd.
3. Beim ersten Start sucht das Programm FreeCAD in dieser Reihenfolge:
   - Pfad aus den Einstellungen
   - Umgebungsvariable `FREECADCMD` oder `FREECAD_ROOT`
   - `FreeCADCmd.exe` im PATH
   - `%ProgramFiles%\FreeCAD*\bin\FreeCADCmd.exe`, `%ProgramFiles(x86)%\…`, `%LocalAppData%\Programs\FreeCAD*\bin\FreeCADCmd.exe`
   - Deinstallations-Schlüssel der Registry, wenn der Anzeigename FreeCAD enthält

Fehlt FreeCAD 1.1, erscheint ein deutscher Hinweis mit dem typischen Pfad `C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`. Ein Export ohne diese Version wird nicht als Erfolg gemeldet.

Die Workbenches unter `geometry/hausraster/FreeCAD_Mod` können zusätzlich nach `%APPDATA%\FreeCAD\Mod` kopiert werden, wenn die Modelle auch in der FreeCAD-Oberfläche neu berechnet werden sollen. Die Anwendung selbst braucht das nicht.

## Starten während der Entwicklung

```bash
python3 -m sidecar.server
npm install
npm run dev
```

Die Oberfläche liegt dann auf `http://localhost:1420`. Unter Windows startet die installierte Anwendung den Dienst selbst.

Installationspaket (MSI und NSIS) baut die Workflow-Datei `.github/workflows/windows.yml` auf `windows-latest` mit dem aktuellen stabilen Rust. Dieser Lauf ist von der Linux-Umgebung aus nicht ausgeführt worden. Das Rust auf dieser Maschine ist 1.83 und kann die Tauri-Abhängigkeiten nicht übersetzen, weil die Edition 2024 vorausgesetzt wird.

## Bedienung

Siehe [docs/BEDIENUNGSANLEITUNG.md](docs/BEDIENUNGSANLEITUNG.md).

Beispiel: [examples/schublade_480x420.cadstudio.json](examples/schublade_480x420.cadstudio.json) (480 × 420 mm, vier Boxen, eine davon gedreht, eine in der Höhe geändert).

## Tests

```bash
python3 -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt
FREECADCMD=/pfad/zu/FreeCADCmd python3 -m unittest tests.test_abnahme
npm test
npx playwright test
```

`tests/test_abnahme.py` legt die Schublade 480 × 420 mm an, prüft das Raster, verschiebt und dreht Boxen, verlangt eine erkannte Überlappung, speichert in einem frischen Prozess, erzeugt STL und FCStd und lädt die Dateien in einem zweiten FreeCAD-Prozess. Erfolg gibt es nur, wenn die Dateien existieren und die Netzprüfung besteht.

Der Prüfbericht steht in [TESTBERICHT.md](TESTBERICHT.md).

## Was noch nicht da ist

Ersatzteile, Kabelmanagement und Elektronikgehäuse sind auf der Startseite sichtbar und als „in Vorbereitung“ markiert. Separate Randstreifen haben kein Modell. Ein Windows-Installer wurde hier nicht gebaut und nicht gestartet.
