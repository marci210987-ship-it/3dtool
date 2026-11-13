# -*- coding: utf-8 -*-
"""FreeCADCmd suchen.

Reihenfolge (überschreibbar):
1. Vom Benutzer gesetzter Pfad
2. Umgebungsvariable FREECADCMD bzw. FREECAD_ROOT
3. FreeCADCmd im PATH
4. Typische Installationsordner (Windows: Program Files, LocalAppData;
   Linux: /usr/bin, /usr/local/bin)
5. Unter Windows zusätzlich die Deinstallations-Schlüssel der Registry

Die Version wird nur akzeptiert, wenn sie 1.1.x ist. Andere Hauptversionen
werden gemeldet, aber nicht stillschweigend verwendet.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _exe_names() -> list[str]:
    # Beide Schreibweisen, damit ein Windows-Pfad auch in Tests und ein
    # Linux-Build im selben Suchlauf erkannt werden.
    return ["FreeCADCmd.exe", "freecadcmd.exe", "freecadcmd", "FreeCADCmd"]


def _looks_like_cmd(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name.lower()
    return name.startswith("freecadcmd")


def _from_root(root: Path) -> list[Path]:
    names = _exe_names()
    found = []
    for rel in (
        Path("bin"),
        Path("usr") / "bin",
        Path(""),
    ):
        for name in names:
            candidate = root / rel / name
            if _looks_like_cmd(candidate):
                found.append(candidate)
    return found


def registry_candidates() -> list[Path]:
    """Windows-Registry. Auf anderen Systemen leer."""
    if os.name != "nt":
        return []
    try:
        import winreg  # type: ignore
    except ImportError:
        return []
    found: list[Path] = []
    roots = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, key_path in roots:
        try:
            with winreg.OpenKey(hive, key_path) as root:
                count = winreg.QueryInfoKey(root)[0]
                for i in range(count):
                    try:
                        subname = winreg.EnumKey(root, i)
                        with winreg.OpenKey(root, subname) as sub:
                            display, _ = _reg_str(sub, "DisplayName")
                            if not display or "freecad" not in display.lower():
                                continue
                            loc, _ = _reg_str(sub, "InstallLocation")
                            if loc:
                                found.extend(_from_root(Path(loc)))
                            icon, _ = _reg_str(sub, "DisplayIcon")
                            if icon:
                                icon_path = Path(icon.split(",")[0].strip().strip('"'))
                                if icon_path.parent.name.lower() == "bin":
                                    found.extend(_from_root(icon_path.parent.parent))
                    except OSError:
                        continue
        except OSError:
            continue
    return found


def _reg_str(key, name: str) -> tuple[str, bool]:
    import winreg  # type: ignore

    try:
        value, _typ = winreg.QueryValueEx(key, name)
    except OSError:
        return "", False
    return str(value), True


def installation_candidates(extra_roots: list[Path] | None = None) -> list[Path]:
    """Typische Installationsorte. extra_roots erlaubt Tests ohne Windows."""
    found: list[Path] = []
    roots: list[Path] = list(extra_roots or [])
    if os.name == "nt":
        for var in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
            base = os.environ.get(var)
            if not base:
                continue
            base_path = Path(base)
            if var == "LocalAppData":
                roots.append(base_path / "Programs")
            else:
                roots.append(base_path)
        roots.extend(registry_install_roots_only())
    else:
        roots.extend([Path("/usr/bin"), Path("/usr/local/bin"), Path("/opt")])
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if _looks_like_cmd(root):
            if root not in seen:
                found.append(root)
                seen.add(root)
            continue
        if not root.is_dir():
            continue
        namen = _exe_names()
        for name in namen:
            direkt = root / name
            if _looks_like_cmd(direkt) and direkt not in seen:
                found.append(direkt)
                seen.add(direkt)
        try:
            children = [child for child in root.iterdir() if child.is_dir() and "freecad" in child.name.lower()]
        except OSError:
            children = []
        for child in children:
            for cmd in _from_root(child):
                if cmd not in seen:
                    found.append(cmd)
                    seen.add(cmd)
    if os.name == "nt":
        for cmd in registry_candidates():
            if cmd not in seen:
                found.append(cmd)
                seen.add(cmd)
    return found


def registry_install_roots_only() -> list[Path]:
    """Nur Installationsordner aus der Registry, ohne die exe schon aufzulösen."""
    paths: list[Path] = []
    if os.name != "nt":
        return paths
    try:
        import winreg  # type: ignore
    except ImportError:
        return paths
    uninstall = (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, key_path in uninstall:
        try:
            with winreg.OpenKey(hive, key_path) as root:
                count = winreg.QueryInfoKey(root)[0]
                for i in range(count):
                    try:
                        subname = winreg.EnumKey(root, i)
                        with winreg.OpenKey(root, subname) as sub:
                            display, _ = _reg_str(sub, "DisplayName")
                            if not display or "freecad" not in display.lower():
                                continue
                            loc, _ = _reg_str(sub, "InstallLocation")
                            if loc:
                                paths.append(Path(loc))
                    except OSError:
                        continue
        except OSError:
            continue
    return paths


def freecad_command(path: Path) -> list[str]:
    """AppImage und AppRun brauchen den Unterbefehl freecadcmd."""
    name = path.name.lower()
    if name == "apprun" or name.endswith(".appimage"):
        return [str(path), "freecadcmd"]
    return [str(path)]


def candidate_paths(user_path: str | None = None, extra_roots: list[Path] | None = None) -> list[Path]:
    ordered: list[Path] = []
    seen: set[str] = set()

    def add(path: Path | None):
        if path is None:
            return
        try:
            key = str(path)
        except Exception:
            return
        if key in seen:
            return
        seen.add(key)
        ordered.append(path)

    if user_path:
        add(Path(user_path))
    env_cmd = os.environ.get("FREECADCMD")
    if env_cmd:
        add(Path(env_cmd))
    env_root = os.environ.get("FREECAD_ROOT")
    if env_root:
        for cmd in _from_root(Path(env_root)):
            add(cmd)
    for name in _exe_names():
        found = shutil.which(name)
        if found:
            add(Path(found))
    for cmd in installation_candidates(extra_roots):
        add(cmd)
    return ordered


def parse_version(text: str) -> str | None:
    match = VERSION_RE.search(text or "")
    if not match:
        return None
    return "%s.%s.%s" % match.groups()


def version_ist_1_1(version: str | None) -> bool:
    if not version:
        return False
    parts = version.split(".")
    return len(parts) >= 2 and parts[0] == "1" and parts[1] == "1"


def probe_version(cmd: Path, timeout: float = 120.0) -> tuple[str | None, str]:
    """Kurzer FreeCADCmd-Lauf, der nur die Version druckt.

    FreeCAD 1.1 führt Skriptdateien unzuverlässig aus. Der Aufruf geht über
    stdin (exec), wie im Hausraster-Smoke-Test.
    """
    script = (
        "import FreeCAD\n"
        "v = FreeCAD.Version()\n"
        "print('CADSTUDIO_VERSION ' + '.'.join(str(x) for x in list(v)[:3]))\n"
    )
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    try:
        proc = subprocess.run(
            freecad_command(cmd),
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
    for line in blob.splitlines():
        if "CADSTUDIO_VERSION" in line:
            return parse_version(line), blob[-2000:]
    return parse_version(blob), blob[-2000:]


def detect(
    user_path: str | None = None,
    extra_roots: list[Path] | None = None,
    probe: bool = True,
) -> dict:
    """Sucht FreeCADCmd und prüft auf Wunsch die Version."""
    checked = []
    for path in candidate_paths(user_path, extra_roots):
        exists = path.is_file()
        item = {"pfad": str(path), "existiert": exists}
        if not exists:
            item["grund"] = "Datei nicht gefunden"
            checked.append(item)
            continue
        if not probe:
            checked.append(item)
            return {
                "gefunden": True,
                "pfad": str(path),
                "version": None,
                "geeignet": None,
                "geprueft": checked,
                "hinweis": "Version wurde nicht abgefragt.",
            }
        version, ausgabe = probe_version(path)
        item["version"] = version
        if version_ist_1_1(version):
            checked.append(item)
            return {
                "gefunden": True,
                "pfad": str(path),
                "version": version,
                "geeignet": True,
                "geprueft": checked,
                "hinweis": "FreeCAD %s gefunden." % version,
            }
        item["grund"] = (
            "Version %s ist nicht 1.1.x." % version
            if version
            else "Version konnte nicht gelesen werden."
        )
        item["ausgabe_kurz"] = ausgabe[-500:]
        checked.append(item)
    return {
        "gefunden": False,
        "pfad": None,
        "version": None,
        "geeignet": False,
        "geprueft": checked,
        "hinweis": (
            "FreeCAD 1.1.x wurde nicht gefunden. Bitte FreeCAD 1.1 für Windows "
            "installieren (LGPL, wird nicht mitgeliefert) und den Pfad zu "
            "FreeCADCmd.exe in den Einstellungen eintragen. Typisch: "
            "C:\\Program Files\\FreeCAD 1.1\\bin\\FreeCADCmd.exe"
        ),
    }
