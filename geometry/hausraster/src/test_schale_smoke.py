import sys, traceback
sys.path.insert(0,'/workspace/ordnungssystem/src')
import FreeCAD as App
from hausraster_phase3_schale import stufen_schale_teile, schraege_schale_teile

def info(sh):
    bb=sh.BoundBox
    return "valid=%s solids=%d size=%.2f×%.2f×%.2f vol=%.1f" % (
        sh.isValid(), len(sh.Solids), bb.XLength, bb.YLength, bb.ZLength, sh.Volume or 0)

try:
    plan, shapes = stufen_schale_teile({"Gesamtbreite":180,"Gesamttiefe":120,"Ebenenanzahl":3,"Glasdurchmesser":55})
    sh=shapes["Segment_1"]
    print("[OK]" if sh.isValid() and len(sh.Solids)==1 else "[FAIL]", "stufen_180", info(sh), "plan.h", plan.hoehe)
except Exception:
    print("[FAIL] stufen_180")
    traceback.print_exc()

try:
    plan, shapes = schraege_schale_teile({"Schubladenbreite":200,"Schubladentiefe":200,"Neigungswinkel":15,"Verfuegbare_Hoehe":90})
    sh=shapes["Segment_1_1"]
    print("[OK]" if sh.isValid() and len(sh.Solids)==1 else "[FAIL]", "schraege_200", info(sh))
except Exception:
    print("[FAIL] schraege_200")
    traceback.print_exc()
