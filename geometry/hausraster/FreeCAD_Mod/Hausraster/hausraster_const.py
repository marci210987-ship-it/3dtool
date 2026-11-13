# -*- coding: utf-8 -*-
"""Hausraster Systemkonstanten und Parameterprüfung.

Schnittstellenmasse des Aufnahmekörpers folgen der Gridfinity-Community-
Spezifikation (gridfinity.xyz / gridfinity-rebuilt-openscad, MIT,
ursprünglich Zack Freedman). Abweichungen sind unten und in der
Phase-1-Spezifikation dokumentiert.
"""

from __future__ import annotations

# --- Raster (Gridfinity-kompatibel) ---
RASTER_MM = 42.0
HOEHENEINHEIT_MM = 7.0
KASTEN_AUSSEN_ABZUG_MM = 0.5  # 0,25 mm je Seite
KASTEN_AUSSEN_1x1_MM = RASTER_MM - KASTEN_AUSSEN_ABZUG_MM  # 41,5

# Platten-Aufnahmeprofil (von innen nach aussen, 45°-Schrägen)
# 0,7 hoch/aus + 1,8 senkrecht + 2,15 hoch/aus = 4,65 mm
PLATTE_PROFIL_P0 = 0.7
PLATTE_PROFIL_P1 = 1.8
PLATTE_PROFIL_P2 = 2.15
PLATTE_PROFIL_HOEHE = PLATTE_PROFIL_P0 + PLATTE_PROFIL_P1 + PLATTE_PROFIL_P2  # 4,65

# Box-Fussprofil (von unten nach oben)
# 0,8 + 1,8 + 2,15 = 4,75 mm
FUSS_PROFIL_P0 = 0.8
FUSS_PROFIL_P1 = 1.8
FUSS_PROFIL_P2 = 2.15
FUSS_PROFIL_HOEHE = FUSS_PROFIL_P0 + FUSS_PROFIL_P1 + FUSS_PROFIL_P2  # 4,75

# Eckenradien
ECKENRADIUS_PLATTE = 4.0          # Aussendurchmesser 8 mm / 2
ECKENRADIUS_BOX_OBEN = 3.75       # 7,5 / 2
ECKENRADIUS_FUSS_UNTEN = ECKENRADIUS_BOX_OBEN - (FUSS_PROFIL_P0 + FUSS_PROFIL_P2)  # 0,8

# Standard-Plattenhoehe nach Spezifikation
PLATTE_HOEHE_STANDARD = 5.0
PLATTE_FREIRAUM_STANDARD = PLATTE_HOEHE_STANDARD - PLATTE_PROFIL_HOEHE  # 0,35

# Stapellippe (wird nicht in die Höheneinheiten eingerechnet)
LIPPE_P0 = 0.7
LIPPE_P1 = 1.8
LIPPE_P2 = 1.9
LIPPE_HOEHE = LIPPE_P0 + LIPPE_P1 + LIPPE_P2  # 4,4
LIPPE_STUETZ_HOEHE = 1.2
LIPPE_FILLET = 0.6

# Drucker P2S
BAURAUM_X = 256.0
BAURAUM_Y = 256.0
BAURAUM_Z = 256.0
DUESENBREITE = 0.4

# Werkstoff-Schätzwerte (nicht als Messwerte ausgeben)
PLA_DICHTE_G_CM3 = 1.24  # typische Angaben vieler PLA-Hersteller, Schätzung
PETG_DICHTE_G_CM3 = 1.27

# --- Hausraster-eigene Festlegungen (Abweichungen) ---
# Wandstaerke 1,2 mm statt Gridfinity-Minimum 0,95 mm, damit die Wand
# ein Vielfaches der 0,4-mm-Düse ist (3 Linien).
WANDSTAERKE_STANDARD = 1.2
TRENNWAND_STANDARD = 1.2
# Plattenboden: 0,8 mm (2 Düsenbreiten). Dadurch sitzt die Tasche 0,45 mm
# höher als der 0,35-mm-Freiraum der 5-mm-Standardplatte, sofern die
# Profilhöhe vollständig erhalten bleibt. Siehe plattenhoehe().
BODEN_PLATTE_STANDARD = 0.8
# Box: Hohlraum beginnt nach der ersten Höheneinheit (7 mm), also 2,25 mm
# über dem Fussprofil – wie im Gridfinity-Standard.
BODEN_BOX_STANDARD = HOEHENEINHEIT_MM - FUSS_PROFIL_HOEHE  # 2,25
INNENRADIUS_STANDARD = 2.0
PASSUNGSSPIEL_EXTRA_STANDARD = 0.0  # zusätzlich zum 0,25-mm-Standardspiel
SCHUBLADENSPIEL_STANDARD = 1.0  # mm je Seite, damit die Platte nicht klemmt
VERBINDER_SPIEL_STANDARD = 0.20

# Verbinder (Hausraster, nicht Teil von Gridfinity)
VERBINDER_TIEFE = 8.0       # mm je Platte nach innen
VERBINDER_KOPF_BREITE = 12.0
VERBINDER_HALS_BREITE = 7.0
VERBINDER_BODEN_ABSTAND = 0.4  # geschlossener Boden unter der Tasche
VERBINDER_OBEN_FREI = 0.2      # Clip sitzt leicht versenkt

# Verriegelungsnut an der Plattenaussenseite (Hausraster)
NUT_TIEFE = 1.0
NUT_HOEHE = 1.6
NUT_ECKENABSTAND = 10.0

SYSTEM_NAME = "Hausraster"
SYSTEM_VERSION = "0.2-qs1"


def kasten_aussen(einheiten: int, extra_spiel_je_seite: float = 0.0) -> float:
    return einheiten * RASTER_MM - KASTEN_AUSSEN_ABZUG_MM - 2.0 * extra_spiel_je_seite


def box_hoehe(einheiten_z: int, mit_lippe: bool) -> float:
    h = einheiten_z * HOEHENEINHEIT_MM
    if mit_lippe:
        h += LIPPE_HOEHE
    return h


def plattenhoehe(bodenstaerke: float) -> float:
    """Gesamthöhe so, dass das volle Aufnahmeprofil über dem Boden steht."""
    return round(bodenstaerke + PLATTE_PROFIL_HOEHE, 6)


def max_einheiten_je_seite(bauraum: float = BAURAUM_X, rand: float = 0.0) -> int:
    return int((bauraum - rand) // RASTER_MM)


def wand_ist_duesenvielfaches(wand: float, tol: float = 0.021) -> bool:
    n = round(wand / DUESENBREITE)
    return n >= 2 and abs(wand - n * DUESENBREITE) <= tol


# Zulässige Bereiche. Werte ausserhalb sollen die Erzeugung abbrechen.
PARAMETER_BEREICHE = {
    "Einheiten_X": (1, 6),
    "Einheiten_Y": (1, 6),
    "Einheiten_Z": (1, 12),
    "Raster_mm": (42.0, 42.0),  # fest, Kompatibilität
    "Hoeheneinheit_mm": (7.0, 7.0),
    "Wandstaerke": (0.8, 3.2),
    "Bodenstaerke_Platte": (0.6, 2.4),
    "Bodenstaerke_Box": (1.2, 6.0),
    "Passungsspiel": (0.0, 0.4),
    "Rand_X_links": (0.0, 40.0),
    "Rand_X_rechts": (0.0, 40.0),
    "Rand_Y_vorne": (0.0, 40.0),
    "Rand_Y_hinten": (0.0, 40.0),
    "Fachanzahl_X": (1, 8),
    "Fachanzahl_Y": (1, 8),
    "Trennwandstaerke": (0.8, 3.2),
    "Verbinder_Spiel": (0.08, 0.40),
    "Innenradius": (0.0, 6.0),
    "Stapellippe": (0, 1),
    "Verriegelung": (0, 1),
    "Verbinder": (0, 1),
    "Schubladenspiel": (0.0, 5.0),
}


def pruefe_parameter(params: dict) -> list[str]:
    """Gibt eine Liste von Fehlertexten zurück, leer = gültig."""
    errors = []
    p = dict(params)

    def _get(name, default=None):
        return p.get(name, default)

    for name, (lo, hi) in PARAMETER_BEREICHE.items():
        if name not in p:
            continue
        val = p[name]
        if val < lo or val > hi:
            errors.append(f"{name}={val} liegt ausserhalb des zulässigen Bereichs {lo} … {hi}.")

    ex = int(_get("Einheiten_X", 1))
    ey = int(_get("Einheiten_Y", 1))
    ez = int(_get("Einheiten_Z", 1))
    wand = float(_get("Wandstaerke", WANDSTAERKE_STANDARD))
    boden_p = float(_get("Bodenstaerke_Platte", BODEN_PLATTE_STANDARD))
    boden_b = float(_get("Bodenstaerke_Box", BODEN_BOX_STANDARD))
    rand_l = float(_get("Rand_X_links", 0.0))
    rand_r = float(_get("Rand_X_rechts", 0.0))
    rand_f = float(_get("Rand_Y_vorne", 0.0))
    rand_b = float(_get("Rand_Y_hinten", 0.0))
    fx = int(_get("Fachanzahl_X", 1))
    fy = int(_get("Fachanzahl_Y", 1))
    trenn = float(_get("Trennwandstaerke", TRENNWAND_STANDARD))
    spiel = float(_get("Passungsspiel", 0.0))
    raster = float(_get("Raster_mm", RASTER_MM))
    lippe = int(_get("Stapellippe", 1))

    if abs(raster - RASTER_MM) > 1e-6:
        errors.append("Raster_mm darf nicht verändert werden, sonst entfällt die Gridfinity-Kompatibilität.")

    brutto_x = ex * raster + rand_l + rand_r
    brutto_y = ey * raster + rand_f + rand_b
    hoehe_p = plattenhoehe(boden_p)
    hoehe_box = box_hoehe(ez, bool(lippe))

    if brutto_x > BAURAUM_X + 1e-6:
        errors.append(f"Plattenbreite {brutto_x:.2f} mm überschreitet den P2S-Bauraum ({BAURAUM_X} mm).")
    if brutto_y > BAURAUM_Y + 1e-6:
        errors.append(f"Plattentiefe {brutto_y:.2f} mm überschreitet den P2S-Bauraum ({BAURAUM_Y} mm).")
    if hoehe_p > BAURAUM_Z + 1e-6 or hoehe_box > BAURAUM_Z + 1e-6:
        errors.append("Höhe überschreitet den P2S-Bauraum (256 mm).")

    if not wand_ist_duesenvielfaches(wand):
        errors.append(
            f"Wandstaerke {wand} mm ist kein sinnvolles Vielfaches von {DUESENBREITE} mm "
            "(empfohlen 0,8 / 1,2 / 1,6 / 2,0 / 2,4)."
        )

    # Innenmasse der Box müssen für Fächer reichen
    innen_x = kasten_aussen(ex, spiel) - 2 * wand
    innen_y = kasten_aussen(ey, spiel) - 2 * wand
    if innen_x < 8 or innen_y < 8:
        errors.append(
            f"Lichter Innenraum {innen_x:.2f}×{innen_y:.2f} mm ist zu klein. "
            "Einheiten erhöhen oder Wandstärke verringern."
        )
    FACH_MIN_LICHT = 12.0
    if fx > 1 or fy > 1:
        nutz_x = innen_x - (fx - 1) * trenn
        nutz_y = innen_y - (fy - 1) * trenn
        if nutz_x / fx < FACH_MIN_LICHT or nutz_y / fy < FACH_MIN_LICHT:
            errors.append(
                f"Fachanzahl {fx}×{fy} ergibt zu schmale Fächer "
                f"(lichte Breite unter {FACH_MIN_LICHT:.0f} mm). "
                "Fachanzahl verringern oder Box vergrößern."
            )

    # Innenraumhöhe über dem Boden: Lippe zählt zur nutzbaren Höhe.
    box_gesamt = box_hoehe(ez, bool(lippe))
    innen_h = box_gesamt - (boden_b + FUSS_PROFIL_HOEHE)
    if innen_h < 0.8:
        errors.append(
            "Bodenstaerke_Box lässt oberhalb des Bodens zu wenig Wandhöhe "
            f"({innen_h:.2f} mm). Einheiten_Z erhöhen, Stapellippe einschalten "
            "oder Boden reduzieren. Eine 1-Einheiten-Box braucht typischerweise die Lippe."
        )

    max_u = max_einheiten_je_seite()
    if ex > max_u or ey > max_u:
        errors.append(f"Mehr als {max_u} Rastereinheiten je Seite passen nicht in den P2S-Bauraum.")

    return errors


def default_params(**overrides) -> dict:
    p = {
        "Raster_mm": RASTER_MM,
        "Hoeheneinheit_mm": HOEHENEINHEIT_MM,
        "Einheiten_X": 3,
        "Einheiten_Y": 3,
        "Einheiten_Z": 3,
        "Wandstaerke": WANDSTAERKE_STANDARD,
        "Bodenstaerke_Platte": BODEN_PLATTE_STANDARD,
        "Bodenstaerke_Box": BODEN_BOX_STANDARD,
        "Passungsspiel": PASSUNGSSPIEL_EXTRA_STANDARD,
        "Rand_X_links": 0.0,
        "Rand_X_rechts": 0.0,
        "Rand_Y_vorne": 0.0,
        "Rand_Y_hinten": 0.0,
        "Fachanzahl_X": 1,
        "Fachanzahl_Y": 1,
        "Trennwandstaerke": TRENNWAND_STANDARD,
        "Verbinder_Spiel": VERBINDER_SPIEL_STANDARD,
        "Innenradius": INNENRADIUS_STANDARD,
        "Stapellippe": 1,
        "Verriegelung": 1,
        "Verbinder": 1,
        "Schubladenspiel": SCHUBLADENSPIEL_STANDARD,
        "Profil_Platte_P0": PLATTE_PROFIL_P0,
        "Profil_Platte_P1": PLATTE_PROFIL_P1,
        "Profil_Platte_P2": PLATTE_PROFIL_P2,
        "Profil_Fuss_P0": FUSS_PROFIL_P0,
        "Profil_Fuss_P1": FUSS_PROFIL_P1,
        "Profil_Fuss_P2": FUSS_PROFIL_P2,
        "Eckenradius_Platte": ECKENRADIUS_PLATTE,
        "Eckenradius_Box": ECKENRADIUS_BOX_OBEN,
    }
    p.update(overrides)
    return p
