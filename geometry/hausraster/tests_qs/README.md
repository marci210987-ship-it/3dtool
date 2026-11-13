# QS-Testsuite Hausraster 0.2

Unabhängige, wiederholbare Prüfung der FreeCAD-Konstruktionen.

## Voraussetzungen

- FreeCAD 1.1.x (auf der Entwicklungsumgebung: 1.1.4 AppImage, extrahiert)
- Die Module `Hausraster`, `HausrasterPhase3` und `HausrasterPhase4` im FreeCAD-Mod-Pfad
  (unter Windows typisch `%APPDATA%\FreeCAD\Mod\`)
- Optional für den Gridfinity-Vergleich: Referenz-STLs im Ordner `/tmp/gf_ref`
  (Baseplate 1x1/3x3, Bin 1x1 3u, Bin 2x2 3u). Fehlen sie, wird dieser Block als NICHT GETESTET gekennzeichnet.

## Ausführen unter Linux / auf der Box

```bash
/workspace/ordnungssystem/tests/qs/freecadcmd.sh /workspace/ordnungssystem/tests/qs/run_qs_audit.py
```

## Ausführen unter Windows

1. Die drei Ordner aus `FreeCAD_Mod` nach `%APPDATA%\FreeCAD\Mod\` kopieren.
2. `tests\qs\run_qs.bat` doppelklicken oder in der Eingabeaufforderung starten.
3. Alternativ, wenn FreeCAD woanders liegt:

```bat
set FREECADCMD=C:\Pfad\zu\FreeCADCmd.exe
tests\qs\run_qs.bat
```

## Ergebnisse

Nach dem Lauf liegen in `tests/qs/out/`:

- `report.json` – vollständige maschinenlesbare Ergebnisse
- `report.md` – lesbarer Bericht
- `modelle.json` – Statusliste je Modell
- `report_partial.json` – Zwischenstand, falls der Lauf abbricht

Ein digital bestandener Test ist **kein** physischer Nachweis. Slicer-Läufe (Bambu Studio) sind ein gesonderter Schritt und werden im Prüfbericht als OFFEN gekennzeichnet, wenn sie nicht ausgeführt werden konnten.


## Nachtest nach Korrekturen

```bash
/workspace/ordnungssystem/tests/qs/freecadcmd.sh /workspace/ordnungssystem/tests/qs/qs_retest_and_export.py
```

Ergebnisse: `tests/qs/out/retest_qs1.json`. Dieser Lauf erzeugt außerdem die `_QS1`-Dateien der Grundplatten und den Minimal-Testsatz unter `06_testdrucke/QS_Minimaltestsatz/`.

Die erste unabhängige Prüfung (vor den Korrekturen) bleibt in `tests/qs/out/report.json` als Nachweis erhalten. Vorherigen Projekt-Testprotokollen aus Phase 2–5 wurde nicht vertraut.

Unter Windows denselben Aufruf mit `%FREECADCMD%` verwenden, nachdem die drei `FreeCAD_Mod`-Ordner nach `%APPDATA%\FreeCAD\Mod\` kopiert wurden. Nach einem Update von FreeCAD 1.1 liegt der Mod-Pfad unter Umständen in `%APPDATA%\FreeCAD\v1-1\Mod\`.
