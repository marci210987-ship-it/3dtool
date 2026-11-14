# CAD Studio

Windows-Programm für die eigenen 3D-Druck-Entwürfe. Phase B enthält den Schubladen-Konfigurator, Phase C ergänzt automatisches Füllen, druckbare Randstreifen und selbst gezeichnete Teile. Die Oberfläche ist Deutsch, die Maße sind Millimeter.

Der Druckerbezug ist ein Bambu Lab P2S, Bauraum 256 × 256 × 256 mm. Das Raster kommt aus Hausraster 0.2-qs1: 42 mm je Feld, 7 mm je Höhenstufe, anschlussfähig an Gridfinity. Es wird nur diese korrigierte Generatorversion verwendet. Die älteren Grundplatten ohne QS1 sind fehlerhaft und werden nicht geladen.

## Architektur

Die Oberfläche ist eine Tauri-2-Anwendung mit React und TypeScript. Sie spricht mit einem lokalen Python-Dienst auf `127.0.0.1:47321`. Der Dienst plant die Schublade mit `plane_schublade` aus den mitgelieferten Hausraster-Quellen und startet für die Körper **FreeCADCmd 1.1** als eigenen Prozess. Anfragen und Antworten sind JSON. FreeCAD wird nicht mitgeliefert (Lizenz LGPL-2.0-or-later) und nicht verändert.

Projektdateien sind JSON (`.cadstudio.json`) auf dem eigenen Rechner. Es gibt keine Cloud und kein Abo.

```
geometry/hausraster/   Generator 0.2-qs1 (const, plan, geom, fcstd, Phase 3 und 4, Makros, Workbenches)
sidecar/               Planung, FreeCAD-Sitzung, Exportprüfung, Stückliste, Montageplan,
                       eigenteil.py (gezeichnete Teile), autofill.py (automatische Bestückung)
ui/                    Deutsche Oberfläche
src-tauri/             Fenster, Start des Dienstes, Dateidialog
examples/              Beispielprojekt der Abnahmeschublade 480 × 420 mm
```

Eine Änderung an einer Box erzeugt die Geometrie neu. Das Tabellenblatt `HIER_MASSE_AENDERN` in den FCStd-Dateien ist nicht live mit dem Körper verbunden; ohne erneuten Generatorlauf bliebe der alte Körper stehen.

Randstreifen, die nicht mehr in eine Außenplatte passen, werden nur genannt. Einen druckbaren Streifenkörper gibt es im Generator nicht, und CAD Studio erfindet keinen.

Schubladenspiel 1,0 mm und Verbinder-Spiel 0,20 mm sind Vorgaben in den Einstellungen und je Projekt änderbar. Sie sind nicht an einem gedruckten Teil geprüft.

## Voraussetzungen unter Windows

1. [FreeCAD 1.1](https://www.freecad.org/) für Windows installieren. Nicht 0.21 und nicht eine andere Hauptversion. Der Installer von CAD Studio enthält FreeCAD nicht.
2. Python braucht der Installer nicht: Er liefert ein eigenes, eingebettetes Python 3.12 mit (siehe unten). Nur wer den Dienst aus den Quellen startet, braucht Python 3.11 oder neuer.
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

Der Workflow `.github/workflows/windows.yml` baut auf `windows-latest` MSI und NSIS und lädt beide Pakete als GitHub-Actions-Artifacts hoch. Sie bleiben 14 Tage zum Herunterladen. Ein Start dieser Pakete auf einem Windows-Rechner ist damit nicht geprüft.

## Bedienung

Siehe [docs/BEDIENUNGSANLEITUNG.md](docs/BEDIENUNGSANLEITUNG.md). Ersatzteile (Kabelclip, Hülse, Scheibe, Haken, Fuß, Knopf, Stopfen, Winkel) liegen auf der Startseite und werden mit FreeCAD erzeugt.

Beispiel: [examples/schublade_480x420.cadstudio.json](examples/schublade_480x420.cadstudio.json) (480 × 420 mm, vier Boxen, eine davon gedreht, eine in der Höhe geändert).

## Tests

```bash
python3 -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_einbetten
FREECADCMD=/pfad/zu/FreeCADCmd python3 -m unittest tests.test_abnahme tests.test_sonder tests.test_eigenteil tests.test_vorlagen
npm test
npx playwright install chromium   # einmalig
FREECADCMD=/pfad/zu/FreeCADCmd npx playwright test   # startet Dienst und Oberfläche selbst; ohne FREECADCMD entfällt nur der Export
```

Der Workflow `.github/workflows/windows.yml` führt in GitHub Actions auf `windows-latest` zwei Jobs aus. `tests` lädt FreeCAD 1.1.4 (mit Prüfsumme, zwischengespeichert) und führt alle Python-Tests, Vitest, den Build und Playwright mit echtem Export aus. `installer` baut MSI und Setup mit eingebettetem Python, installiert das Setup still auf dem Runner, startet die App und prüft, dass der Dienst auf `/health` antwortet und mit dem mitgelieferten Python läuft.

### Mitgeliefertes Python

`scripts/python_einbetten.py` lädt das „embeddable package“ von Python 3.12.10 von python.org, prüft die feste SHA256-Summe, entpackt es nach `src-tauri/python` und schreibt `python312._pth` so, dass `..` (der Ordner mit `sidecar/` und `geometry/`) auf dem Suchpfad liegt. Tauri legt das als `python/` in den Installationsordner. Der Starter in `src-tauri/src/lib.rs` nimmt dieses Python zuerst und fällt sonst auf `python3`, `python` oder `py` zurück. Dienst und Kindprozesse starten ohne Konsolenfenster; der Dienst schreibt seine Ausgabe nach `%APPDATA%\CADStudio\dienst.log`. Vor einem lokalen Installer-Build einmal `python scripts/python_einbetten.py` ausführen. Der Ordner `src-tauri/python` ist bis auf `.gitkeep` nicht eingecheckt.

`tests/test_abnahme.py` legt die Schublade 480 × 420 mm an, prüft das Raster, verschiebt und dreht Boxen, verlangt eine erkannte Überlappung, speichert in einem frischen Prozess, erzeugt STL und FCStd und lädt die Dateien in einem zweiten FreeCAD-Prozess. Erfolg gibt es nur, wenn die Dateien existieren und die Netzprüfung besteht.

Der Prüfbericht steht in [TESTBERICHT.md](TESTBERICHT.md).

## Installer auf dem eigenen Windows-PC prüfen

Diese Schritte sind die Anleitung für den ersten Start. Sie sind kein bereits durchgeführter Test auf Windows-Hardware.

1. Den Pull Request öffnen und unter **Checks** den Workflow **Windows** wählen. Unten auf der Laufseite steht **Artifacts**. Zwei Pakete liegen dort 14 Tage: `cad-studio-windows-msi` und `cad-studio-windows-setup`. Jedes ist ein Zip.
2. Beide herunterladen und entpacken. Im MSI-Zip liegt `CAD Studio_0.2.0_x64_en-US.msi`, im Setup-Zip `CAD Studio_0.2.0_x64-setup.exe`. Eines von beiden installieren. Das Setup ist der einfachere Weg. Windows SmartScreen kann warnen, weil das Paket nicht signiert ist.
3. Python ist nicht nötig, der Installer bringt es mit. Fehlt der Dienst trotzdem („Der lokale Dienst antwortet nicht“), steht die Ausgabe in `%APPDATA%\CADStudio\dienst.log`.
4. [FreeCAD 1.1.x](https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4) für Windows installieren, zum Beispiel 1.1.4. CAD Studio enthält FreeCAD nicht. Versionen außerhalb von 1.1.x werden abgelehnt.
5. CAD Studio starten. Unter **Einstellungen** auf **FreeCAD suchen** tippen. Gesucht wird in dieser Reihenfolge: gespeicherter Pfad, `FREECADCMD`, `FREECAD_ROOT`, `FreeCADCmd.exe` im PATH, `%ProgramFiles%\FreeCAD*\bin\FreeCADCmd.exe`, `%ProgramFiles(x86)%\…`, `%LocalAppData%\Programs\FreeCAD*\bin\FreeCADCmd.exe`, danach die Deinstallations-Schlüssel der Registry, wenn der Anzeigename FreeCAD enthält. Wenn nichts gefunden wird, den Pfad von Hand eintragen, typisch `C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`, und erneut suchen. Der Hinweis muss Version 1.1.x nennen.
6. Die Beispieldatei [examples/schublade_480x420.cadstudio.json](examples/schublade_480x420.cadstudio.json) als Rohdatei speichern (auf GitHub **Raw**, nicht die Webseite). In CAD Studio **Öffnen** wählen. Erwartet: Innenmaß 480 × 420 mm, Raster **11 × 9** Felder, vier Grundplatten, vier Boxen. **Alle Teile berechnen** startet FreeCAD und darf erst grün werden, wenn STL und FCStd geschrieben und geprüft sind. Das dauert.
7. Wenn etwas scheitert, diese Angaben schicken: Windows-Version, MSI oder Setup, Inhalt von `%APPDATA%\CADStudio\dienst.log`, der angezeigte FreeCAD-Pfad oder der deutsche Fehlertext wortgetreu, ein Bildschirmfoto, und ob das Beispielprojekt die 11 × 9 Felder gezeigt hat. Den roten Text unter **Nicht exportiert** vollständig übernehmen. Nicht raten, ob ein Druck passen würde.

## Was noch nicht da ist

Elektronikgehäuse ist auf der Startseite sichtbar und als „in Vorbereitung“ markiert. Ersatzteile und Kabelmanagement sind benutzbar. Das Kabelmanagement ist ein Satz aus Kanal, 90°-Ecke, Endkappe, Wandhalter und Auslass mit gemeinsamem Stecker-Buchse-Profil; das Spiel (Vorgabe 0,20 mm) ist die Lücke im Modell und nicht am Druck geprüft. Gezeichnete Teile bestehen aus Rechtecken (auch gedreht), Kreisen und Vielecken, die zu Körpern gezogen werden, mit Löchern, Stufen, Schrägen, Keil sowie Fasen und Rundungen. Freiformflächen, Gewinde, Text und 3D-Skizzen gibt es nicht. Randstreifen sind einfache, glatte Füllplatten ohne Verbinder. Der Windows-Installer wird in GitHub Actions gebaut und dort auf dem Runner gestartet; auf einem echten Windows-PC eines Benutzers wurde er noch nicht geprüft.
