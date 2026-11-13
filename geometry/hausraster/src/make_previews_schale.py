# -*- coding: utf-8 -*-
"""STL-Prüfung und Vorschaubilder nur für die neuen Schalen-Dateien."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import trimesh

ROOT = Path("/workspace/ordnungssystem")
DIR = ROOT / "04_gewuerz"

PREVIEWS = [
    DIR / "HR_Stufenregal_180x120_E3_Schale.stl",
    DIR / "HR_Stufenregal_250x150_E3_Schale.stl",
    DIR / "HR_Stufenregal_400x180_E4_Schale_Segment_1.stl",
    DIR / "HR_Schraege_200x200_Schale.stl",
    DIR / "HR_Schraege_300x250_Schale_Segment_1_1.stl",
    DIR / "HR_Schraege_450x350_Schale_Segment_1_1.stl",
    DIR / "HR_Schraege_450x350_Schale_Segment_1_2.stl",
]


def render(mesh, png_path: Path, title: str):
    faces = mesh.vertices[mesh.faces]
    if len(faces) > 25000:
        rng = np.random.default_rng(0)
        faces = faces[rng.choice(len(faces), 25000, replace=False)]
    fig = plt.figure(figsize=(7.2, 6.2), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
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
    ax.add_collection3d(Poly3DCollection(faces, facecolors=colors, edgecolor="none"))
    ext = mesh.extents
    c = mesh.bounds.mean(axis=0)
    maxd = max(ext) * 0.6 + 1
    ax.set_xlim(c[0] - maxd, c[0] + maxd)
    ax.set_ylim(c[1] - maxd, c[1] + maxd)
    ax.set_zlim(c[2] - maxd, c[2] + maxd)
    ax.set_xlabel("X mm")
    ax.set_ylabel("Y mm")
    ax.set_zlabel("Z mm")
    ax.set_title(title, fontsize=10)
    ax.view_init(elev=22, azim=-60)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass
    fig.tight_layout()
    fig.savefig(str(png_path), dpi=110, facecolor="white")
    plt.close(fig)


def main():
    report = []
    meshes = {}
    files = sorted(DIR.glob("*Schale*.stl"))
    for p in files:
        rec = {"file": str(p.relative_to(ROOT)), "exists": True, "bytes": p.stat().st_size}
        m = trimesh.load(str(p), force="mesh")
        if isinstance(m, trimesh.Scene):
            geoms = list(m.geometry.values())
            m = trimesh.util.concatenate(geoms) if geoms else m
        rec["faces"] = int(len(m.faces))
        rec["vertices"] = int(len(m.vertices))
        rec["watertight"] = bool(m.is_watertight)
        rec["is_volume"] = bool(getattr(m, "is_volume", False))
        rec["volume_mm3"] = float(m.volume) if rec["watertight"] or rec["is_volume"] else None
        rec["extents"] = [round(float(x), 3) for x in m.extents]
        if rec["faces"] < 4:
            rec["status"] = "NICHT BESTANDEN"
            rec["detail"] = "Zu wenige Dreiecke."
        elif rec["watertight"] or rec["is_volume"]:
            rec["status"] = "BESTANDEN"
            rec["detail"] = "STL lesbar, wasserdicht=%s, is_volume=%s, %d Dreiecke" % (
                rec["watertight"], rec["is_volume"], rec["faces"])
        else:
            rec["status"] = "EINSCHRAENKUNG"
            rec["detail"] = "STL lesbar, trimesh.is_watertight=False. Vor dem Druck im Slicer prüfen."
        meshes[p] = m
        report.append(rec)
        print("[%s] %s: %s" % (rec["status"], rec["file"], rec["detail"]))
    out = ROOT / "tests" / "phase3_schale_stl_pruefung.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for p in PREVIEWS:
        if p in meshes:
            png = p.with_suffix(".png")
            render(meshes[p], png, p.stem.replace("_", " "))
            print("PNG", png)
    print("STL-Prüfung:", sum(1 for r in report if r["status"] == "BESTANDEN"), "bestanden,",
          sum(1 for r in report if r["status"] != "BESTANDEN"), "andere, von", len(report))


if __name__ == "__main__":
    main()
