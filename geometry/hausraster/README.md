# Hausraster-Quellen – Abbild für CAD Studio (Phase A)

Stand: 13. November 2026, Europe/Berlin.

Dies ist eine **Kopie** der wiederverwendbaren Generator-Quellen aus
`/workspace/ordnungssystem` (Systemversion **0.2-qs1**).
Die Originale in `ordnungssystem` und in Google Drive wurden nicht verändert.

## Inhalt

- `src/` – Python-Generatoren (`hausraster_const.py`, `hausraster_geom.py`,
  `hausraster_plan.py`, `hausraster_fcstd.py`, Phase-3- und Phase-4-Module,
  vorhandene Build- und Smoke-Skripte).
- `FreeCAD_Mod/` – Workbenches `Hausraster`, `HausrasterPhase3`, `HausrasterPhase4`
  (inhaltlich identisch mit den gleichnamigen Dateien in `src/`).
- `macros/` – `Hausraster_NeuBerechnen.FCMacro`, Phase-3/4-Makros, `Schubladenplaner.FCMacro`.
- `tests_qs/` – unabhängige QS-Testskripte (ohne die alten Ergebnisordner).
- `inventar_fcstd.txt` – Liste der 58 FCStd-Dateien im Projektordner
  (Originale vor QS ausgenommen). Die Modelldateien selbst liegen weiter unter
  `/workspace/ordnungssystem/` bzw. im Drive-Ordner und wurden hier nicht dupliziert.
- `MANIFEST_SHA256.txt` – Prüfsummen dieser Kopie.

## Wichtiger Hinweis zur Parametrik

Die FCStd-Dateien enthalten das Tabellenblatt `HIER_MASSE_AENDERN` mit Aliasen,
aber **keine Expression-Bindung**. Eine Massenänderung wirkt erst, wenn die
Geometrie über die Python-Funktionen bzw. die NeuBerechnen-Makros neu erzeugt wird.

Für neue Drucke die Generatoren dieser Version (0.2-qs1) verwenden, nicht die
Ursprungs-FCStd ohne Suffix `_QS1`.

Headless-Aufruf: FreeCADCmd 1.1 führt übergebene `.py`-Dateien nicht zuverlässig aus.
Das Muster steht in `src/run_fc.sh` und in `../../smoke/run_smoke.sh` (stdin-exec).
