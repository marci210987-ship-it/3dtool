# -*- coding: utf-8 -*-
"""Unabhängige QS-Testsuite für Hausraster 0.2.

Ausführung auf der Box:
  /workspace/ordnungssystem/tests/qs/freecadcmd.sh /workspace/ordnungssystem/tests/qs/run_qs_audit.py

Ausführung unter Windows (FreeCAD 1.1.x, Mods unter %APPDATA%\\FreeCAD\\Mod\\):
  1. FreeCAD_Mod/Hausraster, HausrasterPhase3 und HausrasterPhase4 nach
     %APPDATA%\\FreeCAD\\Mod\\ kopieren (siehe Handbuch).
  2. In einer Eingabeaufforderung:

     "%ProgramFiles%\\FreeCAD 1.1\\bin\\FreeCADCmd.exe" -c run_qs_audit.py

     oder, wenn FreeCADCmd die Datei als Skript akzeptiert:

     "%ProgramFiles%\\FreeCAD 1.1\\bin\\FreeCADCmd.exe" run_qs_audit.py

  Alternativ run_qs.bat im selben Ordner starten. Das Arbeitsverzeichnis
  muss tests/qs oder das Projekt根verzeichnis sein; das Skript sucht selbst.

Die Suite vertraut keinen älteren Protokollen. Ein Lauf ohne Exception ist
kein Nachweis für Funktion; es zählen die einzelnen geometrischen Messwerte.
Digital bestandene Prüfungen sind niemals physisch erprobt.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if not (ROOT / "01_rastersystem").exists():
    for cand in (Path("/workspace/ordnungssystem"), Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent):
        if (cand / "01_rastersystem").exists():
            ROOT = cand
            break

for p in (
    HERE,
    ROOT / "src",
    ROOT / "FreeCAD_Mod" / "Hausraster",
    ROOT / "FreeCAD_Mod" / "HausrasterPhase3",
    ROOT / "FreeCAD_Mod" / "HausrasterPhase4",
):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from qs_common import (  # noqa: E402
    REPORT, OUT, FREECAD_VERSION, ROOT as CROOT, now_berlin, write_partial,
)
from qs_load import inventory, test_open_fcstd  # noqa: E402
from qs_param import (  # noqa: E402
    test_param_plates, test_param_boxes, test_param_faecher, test_invalid_params,
)
from qs_assembly import test_assemblies, test_gridfinity_ref  # noqa: E402
from qs_kitchen import test_besteck, test_gewuerz  # noqa: E402
from qs_macros import test_macro_hooks  # noqa: E402
from qs_print import test_printability  # noqa: E402

STATUS_RANK = {
    "FEHLERHAFT": 3,
    "EINGESCHRÄNKT": 2,
    "EINGESCHRAENKT": 2,
    "BESTANDEN": 1,
    "NICHT GETESTET": 0,
    "NICHT_GETESTET": 0,
    "HINWEIS": 0,
}


def finalize_model_status(models):
    by = {}
    for t in REPORT["tests"]:
        mid = t.get("modell")
        if mid:
            by.setdefault(mid, []).append(t)
    for m in models:
        tests = by.get(m["id"], [])
        worst = m["status"]
        for t in tests:
            if STATUS_RANK.get(t["status"], 0) > STATUS_RANK.get(worst, 0):
                worst = t["status"]
        if worst == "EINGESCHRAENKT":
            worst = "EINGESCHRÄNKT"
        if worst == "NICHT_GETESTET":
            worst = "NICHT GETESTET"
        if worst == "BESTANDEN":
            worst = "EINGESCHRÄNKT"
            m["befunde"].append(
                "Alle vorgesehenen digitalen Prüfungen in diesem Lauf waren erfolgreich, "
                "aber es gibt keinen Slicer- und keinen physischen Testdruck. "
                "Status daher EINGESCHRÄNKT, nicht physisch erprobt."
            )
        m["status"] = worst
        m["n_tests"] = len(tests)


def write_reports(models):
    REPORT["beendet"] = now_berlin()
    counts = {}
    for t in REPORT["tests"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    mod_counts = {}
    for m in models:
        mod_counts[m["status"]] = mod_counts.get(m["status"], 0) + 1
    REPORT["zusammenfassung"] = {
        "tests_gesamt": len(REPORT["tests"]),
        "tests_nach_status": counts,
        "modelle_gesamt": len(models),
        "modelle_nach_status": mod_counts,
        "gefundene_fehler": REPORT["fehler"],
        "freecad_version": FREECAD_VERSION,
        "slicer": "OFFEN in diesem Skript (gesondert dokumentiert).",
        "physische_tests": "NICHT AUSGEFUEHRT (kein Drucker in dieser Pruefung).",
    }
    (OUT / "report.json").write_text(json.dumps(REPORT, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (OUT / "modelle.json").write_text(json.dumps(models, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    lines = []
    lines.append("# QS-Audit Hausraster 0.2 – maschineller Prüfbericht")
    lines.append("")
    lines.append("Unabhängige Prüfung. Vorherigen Protokollen wurde nicht vertraut.")
    lines.append("")
    lines.append("- FreeCAD: **%s**" % FREECAD_VERSION)
    lines.append("- Zeitpunkt (Europe/Berlin): **%s**" % now_berlin())
    lines.append("- Projektwurzel: `%s`" % CROOT)
    lines.append("")
    z = REPORT["zusammenfassung"]
    lines.append("## Zahlen")
    lines.append("")
    lines.append("- Tests gesamt: **%d**" % z["tests_gesamt"])
    for k, v in sorted(z["tests_nach_status"].items()):
        lines.append("- Tests %s: **%d**" % (k, v))
    lines.append("- Modelle gesamt: **%d**" % z["modelle_gesamt"])
    for k, v in sorted(z["modelle_nach_status"].items()):
        lines.append("- Modelle %s: **%d**" % (k, v))
    lines.append("")
    lines.append("Ein digital bestandener Test bedeutet **nicht**, dass das Teil physisch erprobt ist.")
    lines.append("Slicer-Prüfungen in diesem Skript: **nicht ausgeführt** (gesondert dokumentiert).")
    lines.append("")
    lines.append("## Modellstatus")
    lines.append("")
    lines.append("| Modell | Ordner | Status | Lücken | Befunde |")
    lines.append("|---|---|---|---|---|")
    for m in models:
        bef = "; ".join(m["befunde"][:4]).replace("|", "/")
        if len(m["befunde"]) > 4:
            bef += " …"
        lue = ", ".join(m["luecken"]) if m["luecken"] else "—"
        lines.append("| %s | %s | **%s** | %s | %s |" % (m["id"], m["ordner"], m["status"], lue, bef[:200]))
    lines.append("")
    lines.append("## Gefundene Fehler (Skriptebene)")
    lines.append("")
    if not REPORT["fehler"]:
        lines.append("Keine auf der Skriptebene gesammelten Fehlerobjekte.")
    else:
        for f in REPORT["fehler"]:
            lines.append("- **%s** (Schwere: %s): %s" % (f.get("id"), f.get("schwere"), f.get("ursache", f)))
    lines.append("")
    lines.append("## Fehlgeschlagene und eingeschränkte Tests")
    lines.append("")
    for t in REPORT["tests"]:
        if t["status"] in ("FEHLERHAFT", "EINGESCHRAENKT", "EINGESCHRÄNKT", "NICHT_GETESTET", "NICHT GETESTET"):
            lines.append("### %s — %s — %s" % (t["status"], t["bereich"], t["name"]))
            if t["details"]:
                lines.append("")
                lines.append(str(t["details"])[:2000])
            if t["messwerte"]:
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(t["messwerte"], ensure_ascii=False, default=str, indent=2)[:4000])
                lines.append("```")
            lines.append("")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Berichte geschrieben nach", OUT)
    print("Tests:", z["tests_gesamt"], z["tests_nach_status"])
    print("Modelle:", z["modelle_nach_status"])


def main():
    print("QS-Audit startet, FreeCAD", FREECAD_VERSION, "Wurzel", CROOT)
    print("=== 1 Bestand ===")
    models = inventory()
    write_partial()
    print("=== 2 FreeCAD je FCStd ===")
    test_open_fcstd(models)
    write_partial()
    print("=== 3 Parametrik ===")
    test_param_plates()
    test_param_boxes()
    test_param_faecher()
    test_invalid_params()
    write_partial()
    print("=== 4 Baugruppe / Gridfinity ===")
    test_assemblies()
    test_gridfinity_ref()
    write_partial()
    print("=== 5 Besteck ===")
    test_besteck()
    write_partial()
    print("=== 6 Gewuerz ===")
    test_gewuerz()
    write_partial()
    print("=== Makro-Haken ===")
    test_macro_hooks()
    write_partial()
    print("=== 7 Druckbarkeit ===")
    test_printability(models)
    finalize_model_status(models)
    write_reports(models)
    print("FERTIG", now_berlin())


# FreeCADCmd führt Dateien oft mit __name__ != "__main__" aus.
print("run_qs_audit: __name__=%r, starte main()" % __name__, flush=True)
try:
    main()
except Exception:
    traceback.print_exc()
    try:
        write_partial()
    except Exception:
        pass
    sys.exit(1)
sys.exit(0)
