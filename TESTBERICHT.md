# Testbericht CAD Studio, Phase B

**Datum:** 13. November 2026, Europe/Berlin  
**FreeCAD:** 1.1.4 (AppImage `FreeCAD_1.1.4-Linux-x86_64-py311.AppImage`, Aufruf über `AppRun freecadcmd`)  
**Hausraster:** 0.2-qs1, Quellen im Repository unter `geometry/hausraster`

Nichts in dieser Liste ist geschätzt. „Bestanden“ heißt, der genannte Lauf ist auf dieser Maschine ohne Fehler durchgelaufen. „Nicht ausgeführt“ heißt, der Lauf hat nicht stattgefunden.

## Bestanden

| Test | Ergebnis | Anmerkung |
|---|---|---|
| `python3 -m unittest tests.test_layout` | bestanden | 5 Tests. Plan 480×420 mm: 11×9 Felder, vier Platten 5×4, 5×5, 6×4, 6×5, alle im Bauraum, 16 Verbinder. Randstreifen werden nur ausgewiesen. Überlappung, Drehung, Höhe, freie Felder. |
| `python3 -m unittest tests.test_stlcheck` | bestanden | 4 Tests. Geschlossener Würfel besteht, offenes Netz und falsches Sollmaß fallen durch, fehlende Datei fällt durch. |
| `python3 -m unittest tests.test_detect` | bestanden | 4 Tests. Version 1.1 wird erkannt, 1.0 und 0.21 nicht. Nachgebautes `FreeCAD 1.1\bin\FreeCADCmd.exe` wird gefunden. Registry-Funktion liefert auf Linux eine leere Liste. |
| `python3 -m unittest tests.test_projekt` | bestanden | Speichern und Laden in einem zweiten Python-Prozess, einschließlich der Liste zuletzt geöffneter Projekte. |
| `FREECADCMD=…/AppRun python3 -m unittest tests.test_abnahme` | bestanden | 13. November 2026, etwa 20 Sekunden. Schublade 480×420 mm, Spiel 1,0 mm. Raster 11×9, vier Platten. Vier Boxen, eine verschoben, eine um 90° gedreht, Höhe einer Box von 3 auf 4 Stufen. Überlappung wird erkannt, der Export dazu ist nicht erfolgreich (`ok` falsch). Nach dem Auflösen: STL und FCStd für P1–P4, B1–B4, Verbinder und Rastclip. Unabhängige Netzprüfung und FreeCAD-Meshprüfung bestanden. Zweiter FreeCAD-Prozess lädt jede FCStd-Datei erneut als gültigen Körper mit Tabellenblatt. Stückliste, HTML, PDF und PNG der Montageübersicht sind vorhanden. Maße unter anderem: P1 226×188×5,45 mm, P4 252×230×5,45 mm, B1 41,5×41,5×25,4 mm, B3 nach Drehung 125,5×41,5×18,4 mm, B4 83,5×125,5×32,4 mm. Auszug: `examples/abnahme_manifest_auszug.json`. |
| `python3 -m unittest tests.test_sonder` | bestanden | 13. November 2026. Dieselbe Schublade mit Box plus Deckel (`D1_Box`, `D1_Deckel`), Kabelbox und Bestecksortierer (`S1_Segment_*`, `S1_Segmentverbinder`). Gesamtergebnis `ok` wahr, also Dateien vorhanden und Netzprüfung bestanden. |
| `python3 -m unittest tests.test_server` | bestanden | 13. November 2026, nach der Review. Fremde Origin wird abgewiesen, ohne Sitzungs-Token gibt es kein Speichern, relative Pfade landen unter dem Benutzerordner `projekte`, nicht im Arbeitsverzeichnis. |
| Kabelbox ohne Stapellippe, FreeCAD 1.1.4 | bestanden | 13. November 2026. 2×2×3 mit Kabelkerben und ausgeschalteter Lippe, Sollhöhe 21,0 mm. Export `ok`, Bounding-Box 83,5 × 83,5 × 21,0 mm. |
| `npm test` (Vitest) | bestanden | 4 Tests. Layout und der Editor: vier Boxen, Verschieben, Drehen, Überlappungstext, Höhenänderung. |
| `npx playwright test` | bestanden | 13. November 2026, erneut 22,9 Sekunden nach der Absicherung des lokalen Dienstes. Chromium, kopflos. Startseite mit den vier Bereichen, drei davon „in Vorbereitung“. Neue Schublade 480×420, Raster 11×9 und Platten im Bauraum. Vier Boxen, Verschieben, Drehen, Überlappung, Export-Knopf gesperrt. Konflikt aufgelöst, Höhe geändert, Projekt gespeichert, Seite neu geladen, Projekt aus „Zuletzt geöffnet“ wieder da (Breite 480, Box B4 Höhe 4). „Alle Teile berechnen“ endet mit der Erfolgsmeldung und der Kennzeichnung „3D-Ansicht aus den erzeugten STL-Dateien“. |
| GitHub Actions `windows.yml` auf `windows-latest`, Commit `8913cde` | bestanden | 13. November 2026, 10:16–10:24 UTC. Lauf [43407884824](https://github.com/marci210987-ship-it/3dtool/actions/runs/43407884824). Vitest und die Python-Tests ohne FreeCAD sind auf Windows grün. Der Schritt „Windows-Installer“ hat `CAD Studio_0.2.0_x64_en-US.msi` (3,11 MiB) und `CAD Studio_0.2.0_x64-setup.exe` (2,10 MiB) erzeugt. An diesem Lauf hängen sie nicht als Artifact. |
| GitHub Actions `windows.yml` auf `windows-latest`, Commit `84c85b9` | bestanden | 13. November 2026. Lauf [43412907844](https://github.com/marci210987-ship-it/3dtool/actions/runs/43412907844). Die Schritte „MSI hochladen“ und „Setup hochladen“ sind grün. Artifacts, 14 Tage, nicht abgelaufen: `cad-studio-windows-msi` 3 256 494 Byte und `cad-studio-windows-setup` 2 201 427 Byte. Direkt: [Artifacts dieses Laufs](https://github.com/marci210987-ship-it/3dtool/actions/runs/43412907844#artifacts). Der Installer wurde auf diesem Lauf nicht auf einem Windows-PC gestartet. |

## Nicht ausgeführt

| Prüfung | Ergebnis |
|---|---|
| Start der installierten Windows-Anwendung | nicht ausgeführt. Der Installer ist auf `windows-latest` gebaut, aber nicht auf einem Windows-Rechner gestartet. FreeCAD unter Windows ist dabei nicht angebunden worden. |
| `cargo check` auf der Linux-VM | nicht abgeschlossen. Rust 1.83 kann die Tauri-Abhängigkeiten nicht bauen (Edition 2024). Der Windows-Lauf oben hat mit dem stabilen Rust übersetzt. Die Oberfläche wurde auf Linux im Browser gegen denselben lokalen Dienst geprüft. |
| FreeCAD-Suche in der Windows-Registry auf einem Windows-Rechner | nicht ausgeführt. Der Code ist vorhanden. Auf dieser Maschine gibt es keine Windows-Registry. |
| Doppelklick auf MSI oder NSIS und Anbindung von FreeCADCmd.exe auf einem Windows-PC | nicht ausgeführt. Der Build auf `windows-latest` ist oben als bestanden geführt. |
| Druck auf dem Bambu Lab P2S, Slicer, Passung der Vorgaben 1,0 mm und 0,20 mm | nicht ausgeführt. |
| Lebensmittelkontakt, Spülmaschine, Wärme, gemessene Rastkraft | nicht ausgeführt. |

Ein Export gilt in den bestandenen Läufen nur als erfolgreich, wenn die Datei existiert und die Netzprüfung einen geschlossenen Körper mit plausibler Bounding-Box ergeben hat. Der absichtlich überlappende Stand wurde nicht als Erfolg gewertet.


## Phase C (Windows 11, 13. November 2026)

FreeCAD 1.1.4 (portable Windows-Version py311), Python 3.14, Node 22. Nichts hier ist geschätzt.

| Prüfung | Ergebnis |
|---|---|
| `python -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_abnahme tests.test_sonder tests.test_eigenteil` mit `FREECADCMD` | bestanden, 36 Tests, 1 übersprungen |
| `tests.test_eigenteil` | Formenprüfung, Auftrag, Randstreifen als Füllplatten (Breiten 500, 537, 613 mm), Auto-Bestückung (480×420, 213×377, 95×95, 700×150) ohne Überlappung, Export von Vieleck, Sackloch und Füllplatte mit FreeCAD, Modus „nur eigene Teile“ |
| `npm test` (Vitest) | bestanden, 8 Tests |
| `npm run build` | bestanden |
| Oberfläche live im Browser gegen den Sidecar | Rechteck und Kreisloch gezeichnet, Export „Alle Teile berechnen“ erfolgreich (E1). Schublade 537×301 mm: Raster 12×7, 12 Boxen automatisch gesetzt, Export mit P1–P4, 12 Boxen, S1 (Füllplatte), V und R erfolgreich |

### Nachtrag: Platzieren eigener Teile und PNG-Beschriftung

| Prüfung | Ergebnis |
|---|---|
| 8 Python-Module mit FreeCAD (`test_layout`, `test_stlcheck`, `test_detect`, `test_projekt`, `test_server`, `test_abnahme`, `test_sonder`, `test_eigenteil`) | bestanden, 42 Tests, 1 übersprungen |
| `npm test`, `npm run build` | bestanden, 9 Tests |
| Live im Browser | Teil gezeichnet, in die Schublade gestellt (Fehlermeldungen „liegt nicht in der Schublade“ und „überlappt Box“ erschienen), im Lageplan verschoben (175 / 133 mm), Export erfolgreich; das PNG zeigt P1, P2, B1 und das Teil E1 beschriftet |

### Nachtrag: Auto-Bestückung mit platzierten Teilen, Rückgängig/Wiederholen

| Prüfung | Ergebnis |
|---|---|
| 8 Python-Module mit FreeCAD | bestanden, 43 Tests, 1 übersprungen |
| `npm test`, `npm run build` | bestanden, 10 Tests (neu: Verlauf neues Teil, getippter Name, Rückgängig/Wiederholen) |
| Live im Browser | zwei Rechtecke gezeichnet, Strg+Z (2 → 1 Form), Strg+Y (1 → 2 Formen) |

### Nachtrag: Rundungen und Fasen

| Prüfung | Ergebnis |
|---|---|
| 8 Python-Module mit FreeCAD | bestanden, 48 Tests, 1 übersprungen. Neu: Kantenprüfung, Export mit Eckenradius, Rundung oben, Fase unten und reiner Fase (Volumen kleiner als der Quader, Bounding-Box unverändert) |
| `npm test`, `npm run build` | bestanden, 11 Tests |
| Live im Browser | Rechteck mit Eckenradius 8 mm, Rundung oben 1,5 mm und Fase unten 0,6 mm exportiert; STL wasserdicht, 70 × 40 × 10 mm, 27 312 mm³ gegenüber 28 000 mm³ beim Vollquader |

Fund: FreeCADs einfache `BoundBox` ist bei gekrümmten Flächen um bis zu ~1 mm zu groß und hätte Drucklage und Maßprüfung verfälscht. Der Worker nutzt jetzt `optimalBoundingBox()`. Die bisherigen Abnahmetests laufen damit unverändert durch.

### Nachtrag: Bemaßung, Wunschliste, Stufenteile, Vorlagen

| Prüfung | Ergebnis |
|---|---|
| 8 Python-Module mit FreeCAD | bestanden, 60 Tests, 1 übersprungen. Neu: Wunschliste (Platzierung, Drehung, Rest füllen, zu viele Wünsche, niedrige Schublade, unbekannte Sorte, platzierte Teile bleiben frei), Stufenteile (Höhenlogik, Prüfung, Export mit Volumenprüfung, schwebende Form wird gemeldet) |
| `npm test`, `npm run build` | bestanden, 14 Tests (neu: Maßangaben, Höhen, Vorlagen) |
| Live im Browser | alle fünf Vorlagen in einem Lauf exportiert, STL nachgemessen: Außenmaße und Volumina wie erwartet (z. B. Stufenblock 21 600 mm³ = 14 400 + 7 200). Wunschliste: 1 Kabelbox, 2 Besteckfächer, 3 kleine Boxen und 1 Bestecksortierer platziert, Rest bewusst nicht gefüllt |

### Nachtrag: Schrägen, Keil, Kanten je Form, Einrasten, eigene Vorlagen, klügere Verteilung

| Prüfung | Ergebnis |
|---|---|
| 9 Python-Module mit FreeCAD | bestanden, 71 Tests, 1 übersprungen. Geometrie gegen analytische Volumina: Pyramidenstumpf (Verjüngung 5 mm), Keil (12 000 mm³, 15 mm hoch), Konus-Senkung, Fase an Formkante (12 000 − 70 mm³), Fase am Lochrand; verdeckte Kante wird gemeldet. Vorlagen speichern/laden/ersetzen/löschen, beschädigte Datei. Verteilung: Kontakt, Füllstile |
| `npm test`, `npm run build` | bestanden, 20 Tests (neu: Einrasten, Verschieben mit Fang, Ausrichten, Vorlagen speichern/einsetzen, Ausrichten per Knopf mit Rückgängig) |
| Live im Browser | Kreis neben die Plattenmitte gezogen, rastet exakt auf 30 / 20 ein; Ausrichten setzt Mitte x von 12 auf 30; eigene Vorlage gespeichert, nach Neuladen gefunden, eingesetzt (6 Formen) und gelöscht; Rampe und Senkungsplatte exportiert und nachgemessen (Rampe 19 200 mm³, 13 mm hoch; Senkung 6 990 mm³ wie gerechnet); Füllstile an 480 × 420 mm: groß 9 × 3×3 + 3 × 2×3, einheitlich ebenso, klein 99 × 1×1 |

Fund: Die erste Fassung des Stils „einheitlich“ (meiste Zellen mit gleichen Boxen) lieferte 33 schmale Boxen. Die Wahl nutzt jetzt eine Kostenregel (Boxanzahl + 4 je verschiedener Größe).

### Nachtrag: Muster und Spiegeln

| Prüfung | Ergebnis |
|---|---|
| 9 Python-Module mit FreeCAD | bestanden, 71 Tests, 1 übersprungen (unverändert, Backend nicht berührt) |
| `npm test`, `npm run build` | bestanden, 27 Tests (neu: Gitter, Reihe, Kreismuster, Spiegeln inkl. Keil, Abstandsvorschlag; Panel: Gitter mit Rückgängig, Kreismuster um die Plattenmitte, Spiegelkopie und Ersetzen, Formenlimit, Hinweis bei Rechtecken) |
| Live im Browser | 80 × 80 mm Platte mit einem Loch, Kreismuster mit 6 Löchern um die Plattenmitte, exportiert: 62 305,6 mm³ gemessen gegenüber 62 303,5 mm³ gerechnet (Kreisnäherung im STL) |

Fund: Zahlenfelder, die bei jedem Tastendruck auf einen Mindestwert klammerten, ließen aus „2“ nach dem Leeren „12“ werden. Die Muster-Eingaben halten jetzt den Text und werten ihn erst beim Erzeugen aus. Die Erfolgsmeldung liegt im übergeordneten Zustand, weil das Panel nach dem Erzeugen neu aufgebaut wird (neue Auswahl). `bereinigen` lieferte vereinzelt `-0`.

Nicht ausgeführt: `npx playwright test` (Spezifikation auf die neue Schrittnummer „5. Drucken“ angepasst, aber nicht gelaufen), Start des Windows-Installers, Druck auf dem P2S, Passung der Füllplatten und Spiele.
