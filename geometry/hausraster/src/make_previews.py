# -*- coding: utf-8 -*-
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path("/workspace/ordnungssystem")
out_report = []

# Main preview targets (not every planner plate)
PREVIEWS = [
    ROOT / "01_rastersystem/HR_Grundplatte_3x3.stl",
    ROOT / "01_rastersystem/HR_Plattenverbinder.stl",
    ROOT / "01_rastersystem/HR_Rastclip.stl",
    ROOT / "02_boxen/HR_Box_1x1x3.stl",
    ROOT / "02_boxen/HR_Box_2x2x3.stl",
    ROOT / "06_testdrucke/HR_Passung_Fuss_1x1_Druckanordnung.stl",
    ROOT / "06_testdrucke/HR_Passung_Fuss_1x1_Grundplatte_1x1.stl",
    ROOT / "06_testdrucke/HR_Passung_Fuss_1x1_Fussstumpf.stl",
    ROOT / "06_testdrucke/HR_Passung_Verbinder_Spielstufen_Druckanordnung.stl",
    ROOT / "01_rastersystem/Plan_450x350/HR_Grundplatte_5x4_T1.stl",
    ROOT / "01_rastersystem/Plan_500x400/HR_Grundplatte_6x5_T4.stl",
]


def check_mesh(path: Path):
    rec = {"file": str(path.relative_to(ROOT)), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}
    if not path.exists():
        rec["status"] = "NICHT BESTANDEN"
        rec["detail"] = "Datei fehlt"
        return rec
    try:
        m = trimesh.load(str(path), force="mesh")
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(tuple(g for g in m.geometry.values()))
        rec["faces"] = int(len(m.faces))
        rec["vertices"] = int(len(m.vertices))
        rec["watertight"] = bool(m.is_watertight)
        rec["is_volume"] = bool(getattr(m, "is_volume", False))
        rec["volume_mm3"] = float(m.volume) if m.is_watertight else None
        rec["extents"] = [float(x) for x in m.extents]
        if rec["watertight"] or rec["is_volume"]:
            rec["status"] = "BESTANDEN"
            rec["detail"] = "STL lesbar, wasserdicht=%s, is_volume=%s, %d Dreiecke" % (
                rec["watertight"], rec["is_volume"], rec["faces"])
        else:
            # ehrlich: viele tessellierte CAD-STLs sind nicht perfekt wasserdicht
            rec["status"] = "EINSCHRAENKUNG"
            rec["detail"] = "STL lesbar, aber trimesh.is_watertight=False (tesselliertes CAD-Mesh). Faces=%d. Vor dem Druck im Slicer prüfen." % rec["faces"]
    except Exception as exc:
        rec["status"] = "NICHT BESTANDEN"
        rec["detail"] = "STL nicht lesbar: %s" % exc
    return rec, (m if rec.get("faces") else None)


def render(mesh, png_path: Path, title: str):
    faces = mesh.vertices[mesh.faces]
    if len(faces) > 25000:
        rng = np.random.default_rng(0)
        faces = faces[rng.choice(len(faces), 25000, replace=False)]
    fig = plt.figure(figsize=(7.2, 6.2), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    # simple shade by normals
    normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    nlen = np.linalg.norm(normals, axis=1)
    nlen[nlen == 0] = 1
    normals = normals / nlen[:, None]
    light = np.array([0.4, 0.3, 0.85])
    light = light / np.linalg.norm(light)
    shade = np.clip(normals.dot(light), 0.15, 1.0)
    colors = np.zeros((len(faces), 4))
    colors[:, 0] = 0.16 + 0.25 * shade
    colors[:, 1] = 0.40 + 0.25 * shade
    colors[:, 2] = 0.58 + 0.22 * shade
    colors[:, 3] = 1.0
    col = Poly3DCollection(faces, facecolors=colors, edgecolor="none")
    ax.add_collection3d(col)
    bmin, bmax = mesh.bounds
    center = (bmin + bmax) / 2
    span = max((bmax - bmin).max(), 1.0) * 0.6
    ax.set_xlim(center[0] - span, center[0] + span)
    ax.set_ylim(center[1] - span, center[1] + span)
    ax.set_zlim(center[2] - span, center[2] + span)
    ax.view_init(elev=28, azim=-55)
    ax.set_axis_off()
    ax.set_title(title, fontsize=11, pad=8, color="#222")
    fig.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(png_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    stls = list(ROOT.glob("**/*.stl"))
    stls = [p for p in stls if ".venv" not in p.parts and "tests/smoke" not in str(p)]
    report = []
    meshes = {}
    for p in sorted(stls):
        rec, mesh = check_mesh(p)
        if mesh is not None:
            rec_only, _ = rec, mesh  # rec is the dict
        if isinstance(rec, tuple):
            rec, mesh = rec
        report.append(rec)
        if mesh is not None:
            meshes[p] = mesh
        print("[%s] %s: %s" % (rec["status"], rec["file"], rec["detail"]))

    # Fix unpacking: I made a mess. Rewrite loop cleanly if needed...
    # check_mesh returns rec only when missing, else (rec, mesh). Let me not rely on this.

    Path(ROOT / "tests" / "stl_pruefung.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for p in PREVIEWS:
        if p in meshes:
            png = p.with_suffix(".png")
            render(meshes[p], png, p.stem.replace("_", " "))
            print("PNG", png)
        elif p.exists():
            rec, mesh = check_mesh(p) if not isinstance(check_mesh(p), dict) else (check_mesh(p), None)
            # already loaded above if in stls
            print("skip preview, not in meshes:", p)

    print("done", len(report), "stls")


if __name__ == "__main__":
    # cleaner main
    stls = [p for p in ROOT.rglob("*.stl") if ".venv" not in p.parts]
    report = []
    meshes = {}
    for p in sorted(stls):
        rec = {"file": str(p.relative_to(ROOT)), "exists": True, "bytes": p.stat().st_size}
        try:
            m = trimesh.load(str(p), force="mesh")
            if isinstance(m, trimesh.Scene):
                geoms = list(m.geometry.values())
                m = trimesh.util.concatenate(geoms) if geoms else m
            rec["faces"] = int(len(m.faces))
            rec["vertices"] = int(len(m.vertices))
            rec["watertight"] = bool(m.is_watertight)
            rec["is_volume"] = bool(getattr(m, "is_volume", False))
            rec["volume_mm3"] = float(m.volume) if rec["watertight"] else None
            rec["extents"] = [round(float(x), 3) for x in m.extents]
            rec["readable"] = True
            if rec["faces"] < 4:
                rec["status"] = "NICHT BESTANDEN"
                rec["detail"] = "Zu wenige Dreiecke (%d)." % rec["faces"]
            elif rec["watertight"]:
                rec["status"] = "BESTANDEN"
                rec["detail"] = "STL lesbar und wasserdicht, %d Dreiecke, %.1f mm³" % (rec["faces"], rec["volume_mm3"] or 0)
            else:
                rec["status"] = "EINSCHRAENKUNG"
                rec["detail"] = "STL lesbar, trimesh.is_watertight=False (bei tessellierten CAD-STLs möglich). %d Dreiecke. Im Slicer prüfen." % rec["faces"]
            meshes[p] = m
        except Exception as exc:
            rec["status"] = "NICHT BESTANDEN"
            rec["detail"] = "STL nicht lesbar: %s" % exc
            rec["readable"] = False
        report.append(rec)
        print("[%s] %s: %s" % (rec["status"], rec["file"], rec["detail"]))

    (ROOT / "tests" / "stl_pruefung.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in PREVIEWS:
        if p in meshes:
            png = p.with_suffix(".png")
            render(meshes[p], png, p.stem.replace("_", " "))
            print("PNG", png)
    print("STL-Prüfung:", sum(1 for r in report if r["status"]=="BESTANDEN"), "wasserdicht,",
          sum(1 for r in report if r["status"]=="EINSCHRAENKUNG"), "mit Einschränkung,",
          sum(1 for r in report if r["status"]=="NICHT BESTANDEN"), "fehlgeschlagen")

