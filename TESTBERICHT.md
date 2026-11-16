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

### Nachtrag: Rechtecke drehen, Maße per Eingabe, SVG/DXF-Import

| Prüfung | Ergebnis |
|---|---|
| 9 Python-Module mit FreeCAD | bestanden. Neu: Bounding-Box gedrehter Rechtecke, Prüfung (Keil nicht drehbar, Bauraum nach Drehung), FreeCAD-Export gedrehter Rechtecke mit Radius, Fase und als Loch (Volumina und Maße nachgerechnet) |
| `npm test`, `npm run build` | bestanden, 47 Tests (neu: Drehung in Box/Fang/Kreismuster/Spiegeln; Maße per Eingabe inkl. Rückgängig; 13 Parser-Tests für SVG und DXF: Grundformen, Pfade mit Kurven und Bögen, Transformationen, Maßstab, Verschachtelung, Vereinfachung, Formenlimit, Verkettung von Linien, Bulge; Import-Panel mit Maßstab, Höhe und ungültigen Dateien) |
| Live im Browser | SVG mit Rechteck (Eckenradius), Kreis und Langloch aus Bögen importiert: 3 Formen, 90 × 50 mm; Breite per Klick auf das Maß auf 100 mm geändert; exportiert: 27 315,8 mm³ gemessen gegenüber 27 312,4 mm³ gerechnet |

Fund: jsdom kennt `getScreenCTM` nicht; der Zugriff ist jetzt optional abgesichert.

### Nachtrag: mitgeliefertes Python, Starter, CI, Playwright

| Prüfung | Ergebnis |
|---|---|
| 10 Python-Module mit FreeCAD | bestanden, 79 Tests, 1 übersprungen. Neu: `tests.test_einbetten` (Prüfsumme, Entpacken, Suchpfade, Wiederholung, Versionswechsel, ohne Netz) |
| Eingebettetes Python 3.12.10 (python.org, SHA256 geprüft) | Selbsttest bestanden. Simulierter Installationsordner (`python/`, `sidecar/`, `geometry/`): `python.exe -m sidecar.server` startet aus einem fremden Arbeitsordner, `/health` antwortet, ein echter Export über FreeCAD (gedrehtes Rechteck mit Radius und Loch) endet erfolgreich |
| `cargo check` (Windows, Rust-Starter mit Konsolenfenster-Unterdrückung, Log, bevorzugtem Python) | ohne Fehler |
| Playwright lokal mit Chromium und FreeCAD | 6 von 6 bestanden (Schubladenablauf mit Export, Zeichnen mit Mauszug, Maß per Eingabe und Rückgängig, Vorlagen und SVG-Import, Muster und Ausrichten, Wunschliste und Füllstil, Export eigener Teile). Ohne FreeCAD: 5 bestanden, Export übersprungen |
| `npm test`, `npm run build` | bestanden, 49 Tests |
| Workflow-Datei | YAML gültig; die Prüfsummenlogik für FreeCAD gegen das echte Archiv getestet. Der neue Lauf in GitHub Actions ist noch nicht gelaufen |

Fund: Eine Vorlage oder ein Import neben einem leeren Startteil ließ das leere Teil stehen und blockierte den Export. Ein leeres aktives Teil wird jetzt ersetzt. Der E2E-Test lief vorher nur mit Linux-Pfaden und startete keine Server; er ist portabel und startet Dienst und Oberfläche selbst.

Nicht ausgeführt: `npx playwright test` (Spezifikation auf die neue Schrittnummer „5. Drucken“ angepasst, aber nicht gelaufen), Start des Windows-Installers, Druck auf dem P2S, Passung der Füllplatten und Spiele.

## Ersatzteil-Generator (14. November 2026)

FreeCAD 1.1.4 auf Linux (`AppRun freecadcmd`). Acht Teile: Kabelclip, Distanzhülse, Unterlegscheibe, Wandhaken, Möbelfuß, Drehknopf, Stopfen, Winkel. Nichts hier ist geschätzt. Ein Start auf Windows-Hardware hat nicht stattgefunden.

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest tests.test_ersatzteil` mit `FREECADCMD` | bestanden, 14. November 2026. Standard und Extremwerte jeder Art exportiert (STL wasserdicht, Bounding-Box zum Soll, FCStd erneut als gültiger Körper). Kabelclip Durchmesser 4 mm gegen 12 mm: Tiefe und Höhe der Bounding-Box wachsen. Ungültige Werte (zu dünn, außerhalb der Grenzen, zu großes Loch) werden auf Deutsch abgelehnt, der Auftrag bleibt `ok` falsch. |
| `python3 -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_vorlagen tests.test_einbetten tests.test_ersatzteil` | bestanden, 36 Tests |
| `python3 -m unittest tests.test_abnahme tests.test_sonder tests.test_eigenteil` | bestanden, 49 Tests. Die Schublade und die gezeichneten Teile bleiben grün. |
| `npm test`, `npm run build` | bestanden, 51 Vitest-Tests, Produktionsbau ohne Typfehler |
| `npx playwright test tests/e2e/ersatzteil.spec.ts tests/e2e/schublade.spec.ts` mit FreeCAD | bestanden, 14. November 2026, 23,4 Sekunden. Ersatzteile ist aktiv, zwei Kacheln bleiben „in Vorbereitung“. Kabelclip: Durchmesser 0 wird abgelehnt und der Knopf gesperrt, Durchmesser 10 zeigt das Außenmaß. Der Schubladenablauf mit Export bleibt grün. |
| Windows-Hardware, Druck, Passung der Bohrungen und des Stopfen-Spiels 0,3 mm | nicht ausgeführt |
| GitHub Actions `windows.yml`, Commit `ce0f2f7`, beide Jobs | bestanden, 14. November 2026. Lauf [43570280793](https://github.com/marci210987-ship-it/3dtool/actions/runs/43570280793). Jobs `tests` und `installer` grün. Artifacts: `cad-studio-windows-msi` 14 336 174 Byte, `cad-studio-windows-setup` 11 402 054 Byte. [Artifacts](https://github.com/marci210987-ship-it/3dtool/actions/runs/43570280793#artifacts). Der Installer wurde dabei nicht auf einem privaten Windows-PC gestartet. |

## Kabelmanagement (14. November 2026)

FreeCAD 1.1.4 auf Linux (`AppRun freecadcmd`). Fünf Teile eines Systems: Kabelkanal (Buchse und Stecker, optionaler Deckel, Teilung auf höchstens 250 mm), 90°-Ecke, Endkappe, Wandhalter, Kabelauslass. Dasselbe Profil (Innenmaß, Wand, Spiel, Einstecktiefe). Nichts hier ist geschätzt. Ein Start auf Windows-Hardware hat nicht stattgefunden. Das Spiel ist die Lücke im Modell, kein gedruckter Sitz.

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest tests.test_kabel` mit `FREECADCMD` | bestanden, 14. November 2026, 9 Tests. Standard und Extremwerte jeder Art exportiert (STL wasserdicht und mannigfaltig, ein gültiger Körper, Bounding-Box zum Soll, FCStd erneut geladen). Ein Kanal von 400 mm wird in zwei Stücke plus Deckel geteilt, jedes Stück höchstens 250 mm. Zwei Kanäle mit Spiel 0,20 mm: Schnittvolumen 0, gemessene Lücken links, rechts und unten je 0,20 mm. Mit Spiel 0,35 mm liegen die Lücken bei 0,35 mm. Ein zu breiter Stecker schneidet die schmalere Buchse (Schnittvolumen über 1 mm³), die deutsche Meldung nennt die abweichende Innenbreite. Eine zu schmale Seite lässt eine größere Lücke als das Spiel. Ecke in beide Richtungen und der Wandhalter um den Kanal: Schnittvolumen 0, Lücke 0,20 mm. Ungültige Werte (Wand 0,4 mm, zu kurzer Schenkel, Spiel 2 mm, zu großes Loch, Auslass ohne Rand) werden auf Deutsch abgelehnt. |
| `python3 -m unittest tests.test_layout tests.test_projekt tests.test_server tests.test_kabel.KabelPruefung` | bestanden, 20 Tests. Alte Projektdateien ohne das Feld `kabel` laden weiter. |
| `npm test`, `npm run build` | bestanden, 14. November 2026, 56 Vitest-Tests, Produktionsbau ohne Typfehler |
| `npx playwright test tests/e2e/kabel.spec.ts tests/e2e/ersatzteil.spec.ts tests/e2e/schublade.spec.ts` | bestanden, 14. November 2026. Kabelmanagement ist aktiv, eine Kachel bleibt „in Vorbereitung“. Wand 0,4 mm wird abgelehnt und der Knopf gesperrt. Eine Ecke mit anderer Innenbreite meldet „passen nicht“. Profil angleichen hebt die Meldung auf. „Neue Schublade“ verlässt den Kabel-Modus. Der Schubladenablauf mit Export bleibt grün (23,4 Sekunden). |
| Windows-Hardware, Druck, ob das Spiel von 0,20 mm auf dem P2S sitzt | nicht ausgeführt |
| GitHub Actions `windows.yml`, Commit `631255c`, beide Jobs | bestanden, 14. November 2026. Lauf [43575410119](https://github.com/marci210987-ship-it/3dtool/actions/runs/43575410119). Jobs `tests` und `installer` grün. Artifacts: `cad-studio-windows-msi` 14 340 270 Byte, `cad-studio-windows-setup` 11 409 354 Byte. [Artifacts](https://github.com/marci210987-ship-it/3dtool/actions/runs/43575410119#artifacts). Der Installer wurde dabei nicht auf einem privaten Windows-PC gestartet. |

## Elektronikgehäuse (14. November 2026)

FreeCAD 1.1.4 auf Linux (`AppRun freecadcmd`). Innenmaß, Schraubdeckel mit Säulen und optionaler Senkung, Schiebedeckel, Platinenstützen für Raspberry Pi 4, Raspberry Pi 5 und Arduino Uno R3 sowie eigene Rechtecke, rechteckige und runde Öffnungen, Lüftungsschlitze, Wandlaschen. Nichts hier ist geschätzt. Ein Start auf Windows-Hardware hat nicht stattgefunden. Lochbilder sind Nennwerte der genannten Zeichnungen. Das Spiel und die Einpresslöcher sind nicht gedruckt geprüft.

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest tests.test_gehaeuse` mit `FREECADCMD` | bestanden, 14. November 2026, 6 Tests. Standard, Extrem (Arduino Uno, Senkung, Lüftung, Laschen) und Schiebedeckel exportiert: Korpus und Deckel je STL wasserdicht und mannigfaltig, ein gültiger Körper, Bounding-Box zum Soll, FCStd erneut geladen. Innenbreite 100 gegen 130 mm: die Bounding-Box in X wächst um 30 mm. Deckel auf dem Korpus: Schnittvolumen 0, gemessene Lücken 0,20 mm, bei Spiel 0,35 mm entsprechend 0,35 mm. Schraubenlöcher fluchten mit den Säulen, Platinenlöcher mit den Stützen, auch beim Uno und beim Schiebedeckel. Ungültige Wand, zu große Platine und eine Öffnung an der Säule werden auf Deutsch abgelehnt, der Auftrag bleibt erfolglos. |
| `npm test`, `npm run build` | bestanden, 14. November 2026, 59 Vitest-Tests. `tsc --noEmit` ohne Typfehler |
| `npx playwright test tests/e2e/gehaeuse.spec.ts tests/e2e/kabel.spec.ts tests/e2e/ersatzteil.spec.ts tests/e2e/schublade.spec.ts` | bestanden, 14. November 2026. Elektronikgehäuse ist aktiv, keine Kachel mehr „in Vorbereitung“. Wand 0,4 mm wird abgelehnt und der Knopf gesperrt, 1,6 mm hebt die Meldung auf. „Neue Schublade“ verlässt den Gehäuse-Modus. Kabel, Ersatzteile und der Schubladenablauf mit Export (23 Sekunden) bleiben grün. |
| Windows-Hardware, Druck, Sitz des Deckels und der Platine, Einpressgewinde | nicht ausgeführt |
| GitHub Actions `windows.yml`, Commit `24e9380`, beide Jobs | bestanden, 14. November 2026. Lauf [43576665607](https://github.com/marci210987-ship-it/3dtool/actions/runs/43576665607). Jobs `tests` und `installer` grün. Artifacts: `cad-studio-windows-msi` 14 356 654 Byte, `cad-studio-windows-setup` 11 417 404 Byte. [Artifacts](https://github.com/marci210987-ship-it/3dtool/actions/runs/43576665607#artifacts). Der Installer wurde dabei nicht auf einem privaten Windows-PC gestartet. |

## Oberfläche (14. November 2026)

FrohnLabs-Wortmarke auf dunkelblauer Kopfleiste, Bambu-Grün für Aktionen, heller Arbeitsbereich. Im Schubladenplan steht der Box-Typ und die Feldgröße. Eine Box von einem Feld zeigt nur „1×1“. Die Schrift ist mindestens 13 Bildschirmpixel, solange sie in die Box passt. Die gewählte Box ist dunkelgrün mit weißer Schrift.

| Prüfung | Ergebnis |
|---|---|
| `npm test` | bestanden, 14. November 2026. Neu: zweizeilige Beschriftung, Kurzform 1×1, Schriftgröße mindestens 13 px bei normaler Box |
| Playwright `tests/e2e/design.spec.ts` und `tests/e2e/schublade.spec.ts` | lokal bestanden. Sechs Ansichten bei 1440×900, die große Box zeigt „Große Box“ und „2×3“ |
| Windows-Hardware | nicht ausgeführt |
| GitHub Actions `windows.yml`, Commit `35c8798`, beide Jobs | bestanden, 14. November 2026. Lauf [43586530496](https://github.com/marci210987-ship-it/3dtool/actions/runs/43586530496). Jobs `tests` und `installer` grün. Artifacts: `cad-studio-windows-msi` 14 373 038 Byte, `cad-studio-windows-setup` 11 421 436 Byte. [Artifacts](https://github.com/marci210987-ship-it/3dtool/actions/runs/43586530496#artifacts). Der Installer wurde dabei nicht auf einem privaten Windows-PC gestartet. |

## Erweiterungen im Zeichnen (14. November 2026)

FreeCAD 1.1.4 auf Linux (`AppRun freecadcmd`), Chromium für Playwright. Windows-Hardware, Druck und GitHub Actions: nicht ausgeführt.

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest tests.test_erweitert` mit `FREECADCMD` | bestanden, 14 Tests. Volumen gegen Rechnung: erhabener und vertiefter Text, 90°-Senkung oben und unten, Gegenbohrung, Sechskant-Tasche, durchgehende, Sack- und Schlitz-Seitenlöcher, Drehprofil (Guldin), gerundetes Quadrat. Druckhinweise: Teil mit freitragender Decke und 0,5-mm-Rippe meldet beides, ein einfacher Klotz nichts |
| Alle Python-Module (14) mit FreeCAD | 115 Tests bestanden |
| `npm test`, `npm run build` | 69 Vitest-Tests bestanden, Produktionsbau ohne Typfehler |
| Playwright (alle Spezifikationen) | 15 von 15 bestanden, darunter Langloch/Text/Senkung, Gruppen, Seitenloch/Drehteil, Export eines Drehteils mit Seitenloch |
| Sichtprüfung | Bildschirmfoto: gerundetes Vieleck, Langloch mit Winkel, erhabener Text lesbar |

Grenzen: Die Druckhinweise sind Faustregeln für eine 0,4-mm-Düse und keine Slicer-Simulation. Die Textvorschau im Blatt ist vereinfacht, der Export setzt die Pixelschrift. Gerundete Vielecke gehen nicht zusammen mit Kantenfase. Nichts davon ist gedruckt.

## 3D-Ansicht und Auto-Bestückung (14. November 2026)

FreeCAD 1.1.4 auf Linux, Chromium mit Software-WebGL. Windows-Hardware, Druck und GitHub Actions: nicht ausgeführt.

| Prüfung | Ergebnis |
|---|---|
| Alle Python-Module (15) mit FreeCAD | 126 Tests bestanden. Neu: Netze der Vorschau (nur das gewählte Teil, Maße folgen der Eingabe, ungültige Eingabe meldet Fehler, Gehäuse und Deckel als zwei Netze, Wiederverwendung der Sitzung) |
| Fund und Korrektur | Die Prüfung auf dünne Stellen meldete eine Platte mit Loch und Senkung fälschlich als dünn (Orientierung der Innenkontur nach dem Flächenversatz). Die Versätze werden jetzt je Kontur und mit Richtungsprüfung gerechnet, dazu ein Regressionstest |
| `tests.test_autofill_optimierer` | 9 Tests bestanden: linke und rechte Seite, vertauschte Seiten, vorne und hinten, unbekannte Seite, Gruppen zusammenhängend, Suche nie schlechter als das Zeilenverfahren und bei den Zufallsschubladen mehrmals besser, reproduzierbar, alle Zellen belegt |
| Zufallsprobe (40 Schubladen mit bis zu 3 eigenen Teilen, nicht im Testlauf) | Die Füllung wurde in 30 von 40 Fällen besser als das Zeilenverfahren, der langsamste Lauf dauerte 0,44 s |
| `npm test`, `npm run build` | 71 Vitest-Tests bestanden, Build ohne Typfehler |
| Playwright (alle) | 17 von 17 bestanden, neu: 3D-Ansicht beim Zeichnen (Maße, Neuberechnung bei Höhenänderung, Fehlermeldung bei Höhe 0) und Wunschliste mit Seiten |
| Sichtprüfung | Bildschirmfotos der 3D-Ansicht für ein gezeichnetes Teil mit Drehknopf und für Gehäuse mit Deckel |

Grenzen: Die 3D-Ansicht braucht FreeCAD und WebGL. Die Gewichte der Suche (Seite, Gruppe, Kontakt) sind Vorgaben und noch nicht an echten Schubladen abgestimmt. Die Verbesserung der Füllung hat eine feste Knotenzahl; bei sehr großen freien Flächen kann sie das Optimum verfehlen, ist aber nie schlechter als das Zeilenverfahren.

## Schnitt, Messen, Druckausrichtung, Schrauben (15. November 2026)

FreeCAD 1.1.4 auf Linux, Chromium mit Software-WebGL. Windows-Hardware, Druck und GitHub Actions für diesen Stand: nicht ausgeführt.

| Prüfung | Ergebnis |
|---|---|
| Python (15 Module) mit FreeCAD | 129 Tests bestanden. Neu: Schraubdom auf Platte (Volumen gegen Rechnung, Loch endet an der Plattenoberfläche), Druckausrichtung von Gehäusedeckel, Stopfen und Knopf (Überhang unter 5 mm²) |
| `npm test`, `npm run build` | 94 Vitest-Tests bestanden (Schnittebene je Achse, Messen und Fangen, Ausrichtung mit Quader und Pyramiden, Schraubentabelle und Dom), Build ohne Typfehler |
| Playwright (alle) | 20 von 20 bestanden, neu: Schnitt, Messen, Ausrichtung und Schraubenpanels |
| Sichtprüfung | Bildschirmfotos: aufgeschnittene Platte mit orangefarbener Schnittfläche, Dom mit Zylinderkopf |

Fund aus der Druckausrichtung: Der Schraubdeckel des Gehäuses (7800 mm² Überhang in der exportierten Lage), der Stopfen (72 mm²) und der Drehknopf (28 mm²) waren in Einbaulage exportiert und werden jetzt gedreht. Kabelkanal (2770 mm²), 90°-Ecke (2037 mm²) und Kabelauslass (1068 mm²) haben an der Stufe zwischen Buchse und Kanalboden einen großen Überhang; das ist nicht geändert und braucht eine Entscheidung.

Grenzen: Die Tabellenwerte der Schrauben sind Nennwerte beziehungsweise typische Werte (Einsatz-Außendurchmesser: Datenblatt prüfen), die Zuschläge sind Vorgaben. Die Druckausrichtung ist eine Faustregel auf dem Netz. Nichts davon ist gedruckt geprüft.

## Nachtrag: intelligente Zeichen- und Lochfunktionen, 16.11.2026

Lokal auf Windows geprüft, Python 3.14, FreeCADCmd unter `C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe`, Chromium über die im Lockfile festgelegte Playwright-Version. Kein neuer Installer gebaut oder installiert; kein Drucktest.

| Prüfung | Ergebnis |
|---|---|
| `npm test -- --silent` | 120/120 Tests bestanden (14 Dateien). Vor Änderung: 97/97. Neu: 21 Rechentests und zwei UI-Tests. |
| `npm run build` | TypeScript und Vite-Produktionsbuild erfolgreich. Bestehender Hinweis auf einen JS-Chunk über 500 kB. |
| Python-Vollsuite mit FreeCAD | 131 Fälle durchlaufen, 130 bestanden, einer übersprungen (Registry-Leerlaufprüfung ist nur für Nicht-Windows gedacht). Enthält neue Projektdatei-/Exportvertragsfälle. |
| `python -m unittest tests.test_positionierung` mit FreeCAD, nach Ergänzung des echten Exportfalls | 3/3 bestanden. Positionsmetadaten und Altdateien bleiben kompatibel; versetzte Platte mit konzentrischen Löchern als STL/FCStd exportiert, geschlossenes Netz und Körper geprüft, Volumen mit analytischem Soll verglichen. |
| `npx playwright test` mit FreeCAD | 22/22 bestanden. Bestehendes Zeichnen, Polygonbearbeitung, Gruppen/Muster, echte 3D-Netze, Schubladen-, STL-/FCStd-Export und neue Positionierungsabläufe. |
| Neue Browserfälle | Versetzte Grundform und Größenänderung, konzentrischer Materialkreis, Durchmesser, gebundener Randabstand, sichtbarer Fangpunkt und Abschalten; Layout ohne horizontalen Überlauf bei 390, 768 und 1400 px. |

Python-Vollsuite:

```powershell
$env:FREECADCMD = 'C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe'
$env:PYTHONUTF8 = '1'
python -m unittest tests.test_layout tests.test_stlcheck tests.test_detect tests.test_projekt tests.test_server tests.test_eigenteil tests.test_ersatzteil tests.test_kabel tests.test_gehaeuse tests.test_erweitert tests.test_autofill_optimierer tests.test_positionierung tests.test_abnahme tests.test_sonder tests.test_vorlagen tests.test_einbetten
```

Der erste Vollsuite-Lauf enthielt zwei neue Python-Fälle; der dritte, echte Exportfall wurde anschließend separat mit dem ganzen Positionierungsmodul ausgeführt. Insgesamt sind damit 132 unterschiedliche Python-Fälle abgedeckt, davon einer plattformbedingt übersprungen. Testbedingte Änderungen der eingecheckten Beispieldateien wurden zurückgesetzt.

Während der Entwicklung behoben: doppelter React-Schlüssel der Kontext- und Musterpanels, Testselektoren nach Umstellung von Radius auf Durchmesser sowie horizontaler Überlauf durch die 3D-Canvas beim Verkleinern. Der finale Stand hat keine fehlgeschlagenen lokalen Tests. Die vorhandenen jsdom-WebGL- und Python-ResourceWarnings sind keine neuen Funktionsfehler; reale 3D-Prüfungen erfolgen im Browser/FreeCAD. `npm ci` meldete bereits vor der Umsetzung sechs Abhängigkeitsbefunde; das Lockfile wurde nicht verändert.

Bedienung, Datenmodell und funktionale Grenzen: [POSITIONIERUNG.md](docs/POSITIONIERUNG.md). Beziehungen werden im Zeicheneditor nachgeführt, nicht bei externer JSON- oder FCStd-Bearbeitung. Zentrieren/Randabstände verwenden den achsparallelen Rahmen freier Materialformen, keine Flächenschwerpunkte oder kürzesten Konturabstände. Reine Drehprofile liefern keinen Rahmen für diese Aktionen. Materialunion vor Lochabzug bleibt erhalten; Verteilung verwendet Mittelpunktabstände.
