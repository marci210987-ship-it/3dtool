# -*- coding: utf-8 -*-
"""Erzeugt das Phase-5-Gesamthandbuch als HTML, PDF und DOCX. Überschreibt keine bestehenden Docs."""
from __future__ import annotations
import html
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

ROOT = Path("/workspace/ordnungssystem")
DOC = ROOT / "07_dokumentation"
GUI = DOC / "handbuch_assets" / "gui_print"
OUT_HTML = DOC / "Hausraster_Gesamthandbuch_Phase5.html"
OUT_PDF = DOC / "Hausraster_Gesamthandbuch_Phase5.pdf"
OUT_DOCX = DOC / "Hausraster_Gesamthandbuch_Phase5.docx"
OUT_MD = DOC / "Hausraster_Gesamthandbuch_Phase5.md"

# Image helpers
def g(name: str) -> Path:
    p = GUI / name
    if not p.exists():
        raise FileNotFoundError(p)
    return p

def m(rel: str) -> Path:
    p = ROOT / rel
    if not p.exists():
        raise FileNotFoundError(p)
    return p

# ---------- content as structured blocks ----------
# kind: h1/h2/h3/p/ul/ol/table/note/warn/img/caption/page

BLOCKS = []

def add(*items):
    BLOCKS.extend(items)

add(
    ("h1", "Hausraster – Gesamthandbuch"),
    ("p", "Version 0.2-phase5 · 12. November 2026 · Zeitzone Europe/Berlin"),
    ("p", "Ein parametrisches Ordnungssystem für den Haushalt. Du trägst Schubladen- oder Schrankmasse ins Tabellenblatt ein, lässt das Modell neu berechnen und druckst die Teile auf dem Bambu Lab P2S Combo."),
    ("note", "Die Spielwerte bleiben auf den Standardwerten (Schubladenspiel 1,00 mm je Seite, Verbinder_Spiel 0,20 mm je Kontaktfläche, Deckel_Spiel 0,25 mm). Sie sind bewusst als Parameter ausgeführt und im Blatt sowie in diesem Handbuch klar als «nach Testdruck anpassen» gekennzeichnet. Eine CAD-Prüfung ersetzt keinen echten Testdruck."),
    ("warn", "Lebensmittelechtheit wird nicht behauptet. Die Teile sind Organizer. Direkter Lebensmittelkontakt wurde weder konstruiert noch geprüft."),
    ("h2", "Inhalt"),
    ("ol", [
        "Systemüberblick",
        "Gridfinity-Kompatibilität und Abweichungen",
        "Installation von Mod und Makros unter Windows",
        "Alle Modelle: Vorschau, Parameter, ungültige Kombinationen",
        "Schritt für Schritt in FreeCAD (echte GUI-Screenshots)",
        "Vorbereitung in Bambu Studio (nur Text)",
        "Testdruck-Reihenfolge",
        "Küche und Material",
        "Gesamt-Testprotokoll",
        "Praktisch zu prüfende Punkte",
        "Offene Punkte",
    ]),

    ("h1", "1. Systemüberblick"),
    ("p", "Hausraster ist ein eigenes Rastersystem mit Gridfinity-kompatibler Schnittstelle. Es besteht aus Grundplatten, die in die Schublade gelegt und werkzeuglos zusammengesteckt werden, aus Boxen mit Füssen, die in die Plattentaschen greifen, sowie aus Einsätzen für Besteck, Gewürze und weitere Haushaltsbereiche."),
    ("ul", [
        "Rastermass 42 mm, Höheneinheit 7 mm – diese beiden Werte nicht ändern.",
        "Box-Aussenmass: 42 × n − 0,5 mm. Fussprofil 0,8 / 1,8 / 2,15 mm (4,75 mm). Plattentasche 0,7 / 1,8 / 2,15 mm (4,65 mm).",
        "Standardwand 1,20 mm (drei Bahnen bei 0,4-mm-Düse). Boden der Platte 0,8 mm, Plattenhöhe damit 5,45 mm.",
        "Plattenverbinder: eigener doppelter Schwalbenschwanz. Optionaler Rastclip (C-Profil) aus Phase 2.",
        "Kein Magnet, keine Schraubenpflicht. Lange oder grosse Teile werden in druckbare Segmente geteilt (typisch max. 250 mm, P2S-Bauraum 256 × 256 × 256 mm).",
        "Bedienung: Tabellenblatt HIER_MASSE_AENDERN, dann das passende Makro «NeuBerechnen». Skizzen musst du nicht anfassen.",
    ]),
    ("p", "Die Ordner 01 bis 07 auf der Festplatte und in Google Drive gehören zusammen: Rastersystem, Boxen, Besteck, Gewürz, weitere Haushaltsorganizer, Testdrucke, Dokumentation. Pro Modell liegen typischerweise FCStd, STL, STEP, ein Vorschaubild und eine Kurzanleitung bereit."),

    ("h1", "2. Gridfinity-Kompatibilität und Abweichungen"),
    ("p", "Das System folgt der bekannten Gridfinity-Schnittstelle, damit Füsse und Taschen zusammenpassen. Credits: gridfinity.xyz, gridfinity-rebuilt-openscad (MIT) und Zack Freedman. Hausraster ist trotzdem ein eigenes System mit bewussten Abweichungen:"),
    ("table", [
        ["Merkmal", "Gridfinity-Nähe", "Hausraster"],
        ["Raster / Höhe", "42 mm / 7 mm", "identisch, nicht ändern"],
        ["Box aussen", "42n − 0,5 mm", "identisch"],
        ["Obere Öffnung", "oft 41,75 mm (0,25 mm Plateau)", "41,90 mm (0,10 mm Plateau) → gemessenes Seitenspiel typisch 0,20 mm, nicht 0,25 mm"],
        ["Plattenhöhe", "häufig 4,65–5,00 mm je nach Profil", "5,45 mm (Boden 0,8 mm plus Taschenprofil)"],
        ["Wandstärke", "oft 0,95 mm", "1,20 mm (3 × 0,4 mm)"],
        ["Magnete", "häufig vorgesehen", "keine, magnetfrei"],
        ["Plattenstoss", "verschiedene Clips", "eigener Doppel-Schwalbenschwanz, Verbinder_Spiel 0,20 mm (nach Testdruck anpassen)"],
        ["Schublade", "nicht standardisiert", "Schubladenspiel 1,00 mm je Seite (nach Testdruck anpassen)"],
    ]),
    ("p", "Fremde Gridfinity-Boxen können auf Hausraster-Platten sitzen, und Hausraster-Boxen auf typischen Gridfinity-Platten – in der Theorie der Schnittstelle. Ob die Abweichung am oberen Plateau und an der Plattenhöhe in der Praxis stört, muss ein Testdruck zeigen. Das ist nicht geprüft."),

    ("h1", "3. Installation von Mod und Makros unter Windows"),
    ("h2", "3.1 Was du brauchst"),
    ("ul", [
        "FreeCAD 1.1 (die Entwicklung und die Screenshots in diesem Handbuch liefen mit FreeCAD 1.1.4, AppImage-Stand 20260928).",
        "Die Ordner FreeCAD_Mod/Hausraster, FreeCAD_Mod/HausrasterPhase3 und FreeCAD_Mod/HausrasterPhase4 sowie die Makros im Ordner macros/ der Lieferung.",
        "Unter Windows liegen Benutzereinstellungen typischerweise in %APPDATA%\\FreeCAD\\.",
    ]),
    ("h2", "3.2 Mod-Ordner kopieren"),
    ("ol", [
        "Windows-Taste, «%APPDATA%\\FreeCAD» eingeben und Enter. Falls der Ordner Mod noch nicht existiert, anlegen.",
        "Dorthin die drei Ordner kopieren, sodass folgende Pfade entstehen:",
        "%APPDATA%\\FreeCAD\\Mod\\Hausraster",
        "%APPDATA%\\FreeCAD\\Mod\\HausrasterPhase3",
        "%APPDATA%\\FreeCAD\\Mod\\HausrasterPhase4",
        "FreeCAD einmal vollständig beenden und neu starten. In Einsteiger-Modus bzw. Addon-Liste sollte Hausraster erscheinen; ein fehlender Eintrag ist kein Problem, solange die Makros die Quellen finden.",
    ]),
    ("p", "Hinweis: In FreeCAD 1.1 kann beim Start die Warnung erscheinen, in Hausraster/Init.py sei __file__ nicht definiert. Das ist eine bekannte Warnung. Die Init.py der Lieferung wurde deshalb nicht verändert."),
    ("h2", "3.3 Makros kopieren"),
    ("ol", [
        "Den Ordner %APPDATA%\\FreeCAD\\Macro öffnen (ggf. anlegen).",
        "Dorthin kopieren: Hausraster_NeuBerechnen.FCMacro, Schubladenplaner.FCMacro, Hausraster_Phase3_NeuBerechnen.FCMacro, Hausraster_Phase4_NeuBerechnen.FCMacro.",
        "In FreeCAD unter Macro → Macros die Dateien prüfen. Ein Makro immer nur auf das passende Modell anwenden (Phase 2 für Platten/Basisbox, Phase 3 für Besteck/Gewürz, Phase 4 für die erweiterten Boxen).",
    ]),
    ("h2", "3.4 Typischer Arbeitsablauf"),
    ("ol", [
        "Die gewünschte FCStd öffnen – zum Beispiel HR_Bestecksortierer_450x350.FCStd oder HR_Box_2x3x3_mittel.FCStd. Unter einem neuen Namen speichern, wenn du die Vorlage behalten willst.",
        "Im Modellbaum das Tabellenblatt HIER_MASSE_AENDERN doppelklicken.",
        "Nur die Spalte «Wert» ändern, Einheit und Hinweis stehen lassen.",
        "Das passende NeuBerechnen-Makro ausführen.",
        "Das Ergebnis ansehen, als STL oder STEP exportieren, unter neuem Namen speichern.",
    ]),
    ("warn", "Bekannte Besonderheit: In manchen FreeCAD-Versionen liefert das Tabellenblatt für Textzellen (z. B. Modelltyp) einen führenden Apostroph, also 'besteck statt besteck. Das Phase-3-Makro kann dann mit «Unbekannter Modelltyp: 'besteck» abbrechen. Workaround: den Apostroph im Wert entfernen oder den Modelltyp erneut ohne Anführungszeichen eintragen und das Makro noch einmal starten. Der bestehende Parser wurde in Phase 5 nicht verändert."),

    ("h1", "4. Alle Modelle"),
    ("p", "Die Vorschaubilder unten sind gerenderte Modellansichten (matplotlib aus den STL), keine FreeCAD-Fenster. Die echten GUI-Screenshots folgen in Kapitel 5. Massenangaben sind Schätzungen bei 100 % Füllung und PLA 1,24 g/cm³, keine Wägungen."),

    ("h2", "4.1 Grundplatten, Verbinder, Rastclip (Ordner 01)"),
    ("img", str(m("01_rastersystem/HR_Grundplatte_3x3.png")), "Grundplatte 3×3, gerenderte Vorschau"),
    ("img", str(m("01_rastersystem/HR_Plattenverbinder.png")), "Plattenverbinder (Doppel-Schwalbenschwanz)"),
    ("img", str(m("01_rastersystem/HR_Rastclip.png")), "Optionaler Rastclip aus Phase 2"),
    ("p", "Parameter (Auswahl): Einheiten_X / Einheiten_Y typisch 1–6, so dass keine Seite über 256 mm wächst (6 × 42 − 0,5 = 251,50 mm). Verbinder = 1 legt Taschen an den Stosskanten an. Ränder (Rand_X_links usw.) nehmen Restmasse der Schublade auf. Verbinder_Spiel Standard 0,20 mm, nach Testdruck anpassen. Schubladenspiel 1,00 mm je Seite, nach Testdruck anpassen."),
    ("p", "Ungültig: Schublade, deren Nutzfläche nach Abzug des Spiels kleiner als eine Rastereinheit ist (Beispiel 30 × 30 mm, korrekt abgelehnt). Platte, die den P2S-Bauraum überschreitet. Das Macro teilt grosse Schubladen selbstständig."),
    ("p", "Beispiele aus der Abschlussprüfung, Spiel 1,00 mm je Seite:"),
    ("table", [
        ["Schublade", "Nutzfläche", "Platten", "Bemerkung"],
        ["450 × 350 mm", "448 × 348 mm", "vier 5×4 (224 × 174 × 5,45 mm, je ca. 90,85 g)", "Reste in den Aussenrändern"],
        ["500 × 400 mm", "498 × 398 mm", "5×4, 5×5, 6×4, 6×5 (Breite 252 mm, knapp unter 256 mm)", "11 × 9 Einheiten"],
        ["387 × 293 mm (ungerades Mass)", "385 × 291 mm", "4×6 (171,50 × 252) und 5×6 (213,50 × 252)", "39 mm Resttiefe als Randstreifen, nicht in die Aussenplatte integriert"],
    ]),

    ("h2", "4.2 Boxen (Ordner 02) und Haushaltsvarianten (Ordner 05)"),
    ("img", str(m("02_boxen/HR_Box_1x1x3.png")), "Basisbox 1×1×3"),
    ("img", str(m("02_boxen/HR_Box_2x3x3_mittel.png")), "Mittlere Box 2×3×3"),
    ("img", str(m("02_boxen/HR_Box_3x2x3_Trennwaende_Box.png")), "Box mit herausnehmbaren Trennwänden"),
    ("img", str(m("02_boxen/HR_Box_2x3x3_Deckel_Deckel.png")), "Deckel zur Box"),
    ("img", str(m("02_boxen/HR_Box_1x6x3_lang.png")), "Lange 1×6-Box, 251,50 mm – vor dem Druck drehen prüfen"),
    ("img", str(m("05_haushalt/HR_Schreibtisch_4x3x3.png")), "Schreibtisch-Organizer 4×3×3 (Ordner 05)"),
    ("p", "Parameter: Einheiten_X/Y 1–6, Einheiten_Z typisch 2–6 (höher möglich, auf Bauraum und Stabilität achten). Fachanzahl_X/Y teilt den Innenraum; zu schmale Fächer werden abgewiesen (Beispiel 8×8 in einer zu kleinen Box, korrekt abgelehnt). Wandstaerke nur als Vielfaches von 0,4 mm (0,8 / 1,2 / 1,6 / 2,0 / 2,4). Wert 1,3 mm wird korrekt abgelehnt. Verriegelungsart 0 = keine, 1 = Rastclip über die Stapellippe, 2 = Deckel mit Noppen. Trennwände sitzen in inneren Rippen/Nuten, sie schneiden die 1,20-mm-Wand nicht auf. Deckel_Spiel Standard 0,25 mm, nach Testdruck anpassen."),
    ("p", "Geprüfte Soll-Bounding-Boxen (Auszug Phase 5): 1×1×3 = 41,50 × 41,50 × 25,40 mm; 2×3×3 = 83,50 × 125,50 × 25,40 mm; 3×2×4 mit Fächern 3×2 = 125,50 × 83,50 × 32,40 mm; 1×6×2 = 41,50 × 251,50 × 18,40 mm. Trennwand-Interferenz in der Nut: 0,0000 mm³."),

    ("h2", "4.3 Bestecksortierer (Ordner 03)"),
    ("img", str(m("03_besteck/HR_Bestecksortierer_450x350_Segment_1_1.png")), "Bestecksegment, Variante 450 × 350 mm"),
    ("p", "Der Einsatz füllt die Nutzfläche der Schublade und wird in Segmente unter 250 mm geteilt, die mit dem Hausraster-Schwalbenschwanz verbunden werden. Höhe Standard 45 mm, Wand 1,20 mm. Geprüft für 450 × 350, 500 × 400 und das ungerade Mass 387 × 293 (Segmente 213,40 × 145,50 und 171,60 × 145,50 × 45 mm). Fachbreiten sind Vorgaben bzw. Annahmen, kein ausgemessenes Besteck."),

    ("h2", "4.4 Gewürzorganizer (Ordner 04)"),
    ("img", str(m("04_gewuerz/HR_Stufenregal_180x120_E3_Schale.png")), "Stufenregal als leichte Schale (180 × 120, 3 Ebenen)"),
    ("img", str(m("04_gewuerz/HR_Schraege_200x200_Schale.png")), "Schräger Gewürzeinsatz als Schale"),
    ("img", str(m("04_gewuerz/HR_Gewuerzhalter_D55_Halter.png")), "Einzelhalter, hier Durchmesser 55 mm"),
    ("p", "Es gibt die älteren Vollkörper und die leichten Schalen (Dateiname …_Schale). Die Schalen haben geschlossene, abwischbare Ober- und Frontflächen, unten Rippen, Wand Standard 2,0 mm. Gedruckt werden sie auf der flachen äusseren X-Wand, sodass das YZ-Profil die Schichtform ist. Glasdurchmesser typisch 45 / 55 / 70 mm, zulässig 20–120 mm. Ein Durchmesser 200 mm wird korrekt abgelehnt. Halter D45 / D55 / D70 / D50 sind gültig (D50 in der Abschlussprüfung neu gerechnet, ca. 33,46 g Schätzung)."),

    ("h2", "4.5 Testdrucke (Ordner 06)"),
    ("img", str(m("06_testdrucke/HR_Passung_Fuss_1x1_Druckanordnung.png")), "Fuss-Passung 1×1, Druckanordnung"),
    ("img", str(m("06_testdrucke/HR_Passung_Verbinder_Spielstufen_Druckanordnung.png")), "Verbinder-Spielstufen 0,10 bis 0,30 mm"),
    ("p", "Diese Teile sind dazu da, Spielwerte am echten Druck zu finden – nicht die fertige Schublade als Erstes zu drucken."),

    ("h1", "5. Schritt für Schritt in FreeCAD"),
    ("p", "Alle Bilder in diesem Kapitel sind echte Screenshots der FreeCAD-GUI 1.1.4, aufgenommen unter einer virtuellen Anzeige (Xvfb) mit Fenstergrab, interner Ansicht und Bildschirmfoto. Es sind keine nachgebauten Attrappen. Demo-Dateien lagen in einem temporären Ordner; die Lieferdateien wurden nicht überschrieben."),
    ("img", str(g("00_freecad_start_fenster.png")), "FreeCAD nach dem Start (Willkommensdialog lässt sich mit «Done» schliessen)."),

    ("h2", "5.1 Tabellenblatt öffnen"),
    ("ol", [
        "Die Datei öffnen, hier als Beispiel HR_Bestecksortierer_450x350.FCStd (in der Demo unter einem Arbeitsnamen).",
        "Im Modellbaum HIER_MASSE_AENDERN doppelklicken.",
        "Du siehst die Parameter in Spalte A, die Werte in Spalte B. Nur Spalte B ändern.",
    ]),
    ("img", str(g("01_besteck_450_vorher_fenster.png")), "Vorher: Besteckeinsatz für 450 × 350 mm, 3D-Ansicht und Modellbaum mit vier Segmenten plus Verbinder."),
    ("img", str(g("02_tabellenblatt_geoeffnet_fenster.png")), "Tabellenblatt HIER_MASSE_AENDERN, noch mit Schubladenbreite 450 und -tiefe 350."),

    ("h2", "5.2 Schublade von 450 × 350 auf 500 × 400 umstellen und neu berechnen"),
    ("ol", [
        "Schubladenbreite auf 500, Schubladentiefe auf 400 setzen (lichte Innenmasse, nicht die Korpus-Aussenmasse).",
        "Das Phase-3-Makro Hausraster_Phase3_NeuBerechnen ausführen (Macro → Macros → Ausführen). Für Platten nimmst du den Schubladenplaner bzw. Hausraster_NeuBerechnen, für Phase-4-Boxen Hausraster_Phase4_NeuBerechnen.",
        "Zurück in die 3D-Ansicht wechseln und mit der Maus oder «Ansicht einpassen» das neue Ergebnis betrachten. Der Modellname in der Datei ändert sich nicht von allein – unter neuem Namen speichern.",
    ]),
    ("img", str(g("03_masse_500x400_eingetragen_fenster.png")), "Breite 500 und Tiefe 400 sind im Blatt eingetragen, noch vor dem Neuberechnen."),
    ("img", str(g("04_besteck_500_nachher_fenster.png")), "Nachher: derselbe Besteckeinsatz, jetzt auf 500 × 400 mm gerechnet. Die Statusleiste zeigt ein grösseres Sichtfeld (hier ca. 657 × 332 mm statt zuvor ca. 586 × 305 mm)."),

    ("h2", "5.3 STL exportieren"),
    ("ol", [
        "Im Baum das gewünschte Teil anklicken (ein Segment, nicht das ganze Dokument).",
        "Datei → Exportieren → STL wählen, oder das Teil als Mesh anlegen und speichern.",
        "Die mitgelieferten STL der Lieferung sind bereits auf Wasserdichtigkeit geprüft (trimesh, nach dem Zusammenführen der Knoten). Ein frischer Export aus der GUI ist gleichwertig, wenn du dasselbe Teil exportierst.",
    ]),
    ("img", str(g("05_stl_export_fenster.png")), "Echter STL-Export: im Baum erscheint das Mesh «STL_Export», die Geometrie liegt als Gitter über dem Körper. Die Exportdatei wurde in einem temporären Ordner geschrieben, nicht in die Lieferung."),

    ("h2", "5.4 Neue Boxgrösse und Fachanzahl"),
    ("ol", [
        "Eine Box-Vorlage öffnen, z. B. HR_Box_2x3x3_mittel.FCStd, und unter neuem Namen speichern.",
        "Im Blatt Einheiten_X, Einheiten_Y, Einheiten_Z sowie Fachanzahl_X und Fachanzahl_Y ändern.",
        "Hausraster_Phase4_NeuBerechnen ausführen.",
    ]),
    ("img", str(g("06_box_2x3x3_vorher_fenster.png")), "Vorher: Box 2×3×3 ohne Innenfächer."),
    ("img", str(g("07_box_parameter_geaendert_fenster.png")), "Parameter geändert: Einheiten 3×3×4, Fachanzahl 3×2, noch vor dem Neuberechnen."),
    ("img", str(g("08_box_3x3x4_faecher_nachher_fenster.png")), "Nachher: Box 3×3×4 mit festem 3×2-Fächerbild."),

    ("h2", "5.5 Glasdurchmesser am Halter ändern"),
    ("ol", [
        "z. B. HR_Gewuerzhalter_D55.FCStd öffnen.",
        "Im Blatt Glasdurchmesser von 55 auf 70 setzen.",
        "Hausraster_Phase3_NeuBerechnen ausführen.",
    ]),
    ("img", str(g("09_halter_D55_vorher_fenster.png")), "Vorher: Halter für 55 mm."),
    ("img", str(g("10_halter_D70_eingetragen_fenster.png")), "Glasdurchmesser 70 im Tabellenblatt."),
    ("img", str(g("11_halter_D70_nachher_fenster.png")), "Nachher: der Halter ist erkennbar grösser (Sichtfeld ca. 238 × 124 mm statt zuvor ca. 199 × 104 mm)."),

    ("h2", "5.6 Grundplatten aufteilen"),
    ("p", "Für eine fertige Schublade startest du das Makro Schubladenplaner, trägst Breite, Tiefe und Schubladenspiel ein und lässt den Plan in einen leeren Ordner schreiben. Die folgenden Bilder zeigen dasselbe Planungsergebnis als 3D-Körper: die Platten einer 450×350- und einer 500×400-Schublade liegen zur Ansicht nebeneinander (nicht so in die Schublade legen – in der Schublade stossen sie an den Verbinderkanten an)."),
    ("img", str(g("12_grundplatten_geteilt_450_fenster.png")), "450 × 350 mm: vier 5×4-Platten."),
    ("img", str(g("12b_grundplatten_geteilt_500_fenster.png")), "500 × 400 mm: 5×4, 5×5, 6×4 und 6×5."),

    ("h2", "5.7 Steckverbindungen prüfen (Interferenz und Schnitt)"),
    ("p", "In der GUI wurde eine 3×3-Grundplatte mit einer mittig aufgesetzten Box 1×1×3 zusammengesetzt. Die boolesche Schnittmenge (common) von Platte und Box hat das Volumen 0,0000 mm³ – die Körper durchdringen sich also in der Prüfung nicht. Anschliessend wurde die Baugruppe in der Mitte der Box aufgeschnitten, damit man den Sitz des Fusses in der Tasche sieht."),
    ("img", str(g("13_passung_platte_box_clip_fenster.png")), "Platte 3×3 und aufgesetzte Box 1×1×3. Im Baum liegen zusätzlich die Interferenzkörper (leer, weil das Volumen 0 ist) und ein Plattenverbinder am Ursprung."),
    ("img", str(g("14_passung_schnitt_isometrie_fenster.png")), "Echter geometrischer Schnitt durch Platte und Box: der Fuss sitzt in der Tasche, ohne dass sich die Körper im CAD durchdringen."),
    ("note", "Der Plattenverbinder lag in dieser Aufnahme an seiner Standardlage am Koordinatenursprung (Mitte der 3×3-Platte), nicht in einer Randtasche zweier gestossener Platten. Die CAD-Interferenz Platte/Clip war deshalb ebenfalls 0,0000 mm³, sagt aber nichts über die Passung in der echten Tasche. Dafür sind die Testdrucke «Verbinder-Spielstufen» in Ordner 06 gedacht. Eine zusätzliche Frontansicht des Schnitts wurde versucht, die Kamera blieb jedoch nahe an der isometrischen Richtung; sie wird hier nicht als eigene Frontansicht ausgegeben."),

    ("h1", "6. Vorbereitung in Bambu Studio"),
    ("warn", "Bambu Studio war in der Erstellungsumgebung nicht installiert. Es gibt deshalb keine echten Studio-Screenshots. Die folgenden Werte sind Startvorschläge für den Bambu Lab P2S Combo mit 0,4-mm-Düse, keine am Drucker gemessenen Optimalwerte und kein Ersatz für die Vorschau in Studio."),
    ("h2", "6.1 Datei laden und Drucker wählen"),
    ("ol", [
        "Bambu Studio öffnen.",
        "Drucker Bambu Lab P2S wählen, Düse 0,4 mm. Kein fremdes Druckerprofil verwenden.",
        "Material PLA oder PETG wählen (siehe Kapitel 8).",
        "Die STL des Einzelteils laden, nicht einen fremden G-Code unverändert übernehmen.",
    ]),
    ("h2", "6.2 Drucklage"),
    ("ul", [
        "Grundplatten: grosse Fläche, Boden auf die Druckplatte.",
        "Boxen: auf den Füssen stehend. Fussprofil und Stapellippe sind 45°-gängig, konstruktiv ohne Stützen vorgesehen.",
        "Deckel und Trennwände: flach auf die grosse Fläche.",
        "Plattenverbinder und Segmentverbinder: flach.",
        "Rastclip: auf die Seite, C-Profil liegt auf der Platte.",
        "Gewürzschalen: auf der flachen äusseren X-Wand (das YZ-Profil wird zur Schichtform). Die erste Schicht ist ein C-Profil, keine volle Rechteckfläche – Haftung in der Vorschau und am ersten Versuch besonders beachten.",
        "Besteck- und Gewürz-Vollkörper: auf den flachen Boden. Halter mit der Öffnung nach oben.",
    ]),
    ("h2", "6.3 Prozesswerte (Startvorschläge)"),
    ("table", [
        ["Einstellung", "Vorschlag", "Hinweis"],
        ["Schichthöhe", "0,20 mm", "Vorschlag, keine Messung. Feine Clips darfst du probeweise auf 0,16 mm setzen."],
        ["Wände / Perimeter", "3 Linien", "Passt zur Standardwand 1,20 mm bei 0,4-mm-Düse."],
        ["Füllung", "15 %", "Vorschlag für Organizer. 100 %-Werte in den Masse-Schätzungen dienen nur der Vergleichbarkeit, nicht als Druckempfehlung."],
        ["Stützen", "aus", "Konstruktiv nicht vorgesehen. Trotzdem die Studio-Vorschau auf Überhänge prüfen."],
        ["Brim / Haftgrenze", "an für kleine Teile und Clips", "Platten und grosse Boxen kommen meist ohne Brim aus, wenn das Bett haftet."],
        ["Rand / Skirt", "1–2 Runden", "Nur zum Anfördern, nicht als Ersatz für den Brim."],
        ["Naht und Feinheit", "Studio-Standard zuerst", "Nicht ohne Grund an exotischen Profilen drehen."],
    ]),
    ("h2", "6.4 Lange Teile drehen"),
    ("p", "Der P2S hat 256 × 256 mm Bettfläche. Eine 1×6-Box ist 251,50 mm lang, eine 6×5-Platte 252 × 220 mm. Das liegt knapp unter dem Limit. Vor dem Slicen in der Draufsicht prüfen, ob Laschen der Bauplatte, ausgeschlossene Zonen oder ein Brim das Teil über den Rand schieben. Im Zweifel das Teil in der XY-Ebene drehen, bis die lange Kante frei liegt. Teile über 256 mm gehören nicht auf das Bett – dafür gibt es die Segmentierung."),

    ("h1", "7. Testdruck-Reihenfolge"),
    ("p", "Bitte nicht mit der vollen Schublade beginnen. Die Reihenfolge spart Filament und gibt dir die Spielwerte, bevor grosse Teile laufen."),
    ("ol", [
        "Fuss-Passung 1×1 aus Ordner 06 (Druckanordnung, Schätzung rund 12,5 g bei 100 % – der echte Druck mit 15 % Füllung liegt deutlich darunter). Ziel: der Fuss sitzt spielfrei-klein in der Tasche, ohne zu klemmen oder zu klappern.",
        "Verbinder-Spielstufen 0,10 / 0,15 / 0,20 / 0,25 / 0,30 mm. Den Clip wählen, der sich fest, aber ohne Gewalt fügt. Den gewählten Wert als Verbinder_Spiel ins Tabellenblatt schreiben (nach Testdruck anpassen).",
        "Segmentverbinder-Passung (zwei kurze Schienen plus Clip), bevor du einen ganzen Besteckkasten oder ein langes Regal zusammensteckst.",
        "Kleine 3×3-Grundplatte und Box 1×1×3. Rastclip nach Bedarf.",
        "Erst dann die geplanten Schubladenplatten, anschliessend die Einsätze (Besteck, Gewürzhalter, Schalen).",
        "Schalen: zuerst das kleine Stufenregal 180 × 120, dann grössere Segmente. Auf Durchbiegung unter vollen Gläsern achten.",
        "Deckel und Trennwände erst, wenn die Boxmasse und das Deckel_Spiel stimmen.",
        "Schubladenspiel anpassen, wenn der komplette Plattensatz in der echten Schublade klemmt oder zu viel Luft hat (Standard 1,00 mm je Seite, nach Testdruck anpassen).",
    ]),

    ("h1", "8. Küche und Material"),
    ("ul", [
        "PLA: gut für Schreibtisch und trockene Schränke. Nicht spülmaschinenfest. Verformt sich schon bei mässiger Wärme (heisses Spülwasser, Sonne auf der Arbeitsplatte, warme Töpfe in der Nähe). Nur feucht abwischen.",
        "PETG: in der Regel formstabiler und für feuchte Küche, Bad oder wärmere Flaschen besser geeignet. Auch PETG ist nicht automatisch spülmaschinenfest. Es gelten die Angaben des jeweiligen Filamentherstellers; sie wurden hier nicht nachgeprüft.",
        "Lebensmittelechtheit wird nicht behauptet. Der Filamentname allein reicht dafür nicht. Sie hängt von Zertifikat, Druckführung (Temperatur, geschlossene Perimeter, keine unzugänglichen Poren) und Reinigung ab und wurde nicht geprüft.",
        "Die Gewürzorganeizer halten Gläser und Dosen, sie sind kein direkter Kontakt zu offenen Lebensmitteln.",
        "Schalen innen abwischbar konstruiert; aggressive Reiniger und heisse Spülgänge nicht angenommen.",
    ]),

    ("h1", "9. Gesamt-Testprotokoll"),
    ("p", "Grundsatz: Es werden nur tatsächlich durchgeführte Tests berichtet. Keine erfundenen Ergebnisse. Eine geometrische Prüfung ersetzt keinen realen Testdruck. Bestehende Dateien aus früheren Phasen wurden nicht überschrieben."),
    ("h2", "9.1 Was geprüft wurde"),
    ("table", [
        ["Lieferung", "CAD / Geometrie", "STL (trimesh, wasserdicht)", "Echter P2S-Druck", "FreeCAD-GUI"],
        ["Phase 2", "29 bestanden, 0 nicht", "23 / 23", "nicht durchgeführt", "damals nicht (nur Headless)"],
        ["Phase 3", "112 bestanden, 0 nicht", "35 / 35", "nicht durchgeführt", "damals nicht"],
        ["Schalen-Ergänzung", "46 / 46", "14 / 14", "nicht durchgeführt", "damals nicht"],
        ["Phase 4", "74 / 74", "21 / 21 neue STL", "nicht durchgeführt", "damals nicht"],
        ["Phase 5 Abschluss", "85 / 85, all_ok = True", "Exporte der Lieferung ergänzt und geprüft", "nicht durchgeführt", "durchgeführt, siehe Kap. 5"],
    ]),
    ("p", "Die CAD-Prüfungen umfassen typischerweise Shape.isValid(), genau einen Solid, Bounding Box gegen das Sollmass, P2S-Bauraum 256 mm, Wand- bzw. Randsonden, boolesche Interferenz 0 mm³ an Fugen und Nuten, und ein Recompute der FCStd. STL gelten nach dem Zusammenführen der Knoten (trimesh process=True / is_volume) als geschlossen; rohe FreeCAD-STL können vor diesem Schritt unverbunden wirken."),
    ("h2", "9.2 Phase-5-Abschlussprüfung im Einzelnen"),
    ("p", "Parametrik aller Modellfamilien, ohne die Produktionsdateien zu überschreiben:"),
    ("ul", [
        "Raster 450×350, 500×400 und ungerades Mass 387×293: Pläne gültig, Platten im Bauraum, Spiel 1,00 mm als «nach Testdruck anpassen» ausgewiesen. 30×30 mm korrekt abgelehnt.",
        "Besteck 450 / 500 / 387: jeweils 2×2 Segmente plus Verbinder gültig.",
        "Stufen-Schale 180 / 250 / 400 (D55 / D45 / D70) gültig; D200 korrekt abgelehnt. Schräge Schale 450, 500 (neue Grösse) und 387×293 gültig. Halter D45 / D55 / D70 / D50 gültig.",
        "Boxen 1×1×3, 2×3×3, 3×2×4 mit Fächern 3×2, 4×3×3 mit Fächern 4×3, 1×6×2: Soll-Bounding-Box getroffen. Phase-4-Trennwände plus Deckel (Art 2) gültig, Trennwand-Interferenz 0 mm³. Fachanzahl 8×8 und Wand 1,3 mm korrekt abgelehnt.",
        "GUI-Passung Platte/Box: Interferenz 0,0000 mm³, Schnittbild siehe Kapitel 5.7.",
    ]),
    ("h2", "9.3 Exportvollständigkeit"),
    ("p", "Vor der Handbuch-Erstellung wurden fehlende Vorschaubilder und Kurzanleitungen als neue Dateien ergänzt (64 Dateien, Liste in tests/phase5/ergaenzte_dateien.json). Bestehende Dateien wurden nicht überschrieben. Stand der lokalen Lieferung nach dieser Ergänzung:"),
    ("table", [
        ["Ordner", "FCStd", "STL", "STEP", "PNG", "Kurzanleitung"],
        ["01 Rastersystem", "11", "11", "11", "11", "5"],
        ["02 Boxen", "10", "15", "15", "15", "10"],
        ["03 Besteck", "3", "12", "12", "12", "4"],
        ["04 Gewürz", "15", "34", "34", "34", "17"],
        ["05 Haushalt", "6", "8", "8", "8", "6"],
        ["06 Testdrucke", "3", "13", "13", "13", "4"],
    ]),
    ("p", "Ein Planordner für das ungerade Mass 387 × 293 wurde geprüft, aber nicht als neues Produktionsverzeichnis in 01 veröffentlicht."),
    ("h2", "9.4 Was nicht durchgeführt wurde"),
    ("ul", [
        "Kein echter Testdruck auf dem Bambu Lab P2S, keine Wägung, keine Temperatur- oder Haftmessung, keine Lebensdauerprüfung.",
        "Keine Bambu-Studio-Screenshots (Studio nicht installiert).",
        "Keine Front-Schnittansicht in brauchbarer Kamerarichtung (siehe Hinweis in 5.7).",
        "Keine Prüfung fremder Gridfinity-Teile auf Hausraster-Platten in der Realität.",
        "Das Apostroph-Problem am Modelltyp ist dokumentiert, der bestehende Parser wurde nicht geändert.",
    ]),

    ("h1", "10. Praktisch zu prüfende Punkte"),
    ("ol", [
        "Fuss in der Tasche: zu straff, passend oder klappernd? Spiel oder Fussmass nach dem Testdruck anpassen.",
        "Plattenverbinder: welche Spielstufe (0,10–0,30 mm) fügt sich fest und ohne Gewalt? Wert als Verbinder_Spiel übernehmen (nach Testdruck anpassen).",
        "Segmentverbinder an Besteck und Gewürz: gleiches Spiel, zwei Segmente fluchten in der Höhe.",
        "Schubladenspiel: kompletter Plattensatz in der echten, gemessenen Schublade (lichte Weite). Standard 1,00 mm je Seite, nach Testdruck anpassen.",
        "Lange 6-Einheiten-Teile: sitzen sie auf dem Bett inkl. Brim und Laschen?",
        "Rastclip an der Stapellippe: hält, lässt sich aber ohne Bruch lösen.",
        "Deckel: liegt auf der inneren Lippe, Deckel_Spiel 0,25 mm nach Testdruck anpassen. Noppen (Art 2) nicht übermässig klemmen.",
        "Trennwände: gleiten in die Nut, stehen fest, lassen sich ohne Gewalt herausnehmen.",
        "Schalen: erste Schicht auf der Seitenwand, keine Durchbiegung unter vollen Gläsern, besonders oben und am hohen Schrägen-Segment.",
        "Halter: der tatsächliche Glasdurchmesser plus etwas Luft; nicht nur den Nenndruck auf der Verpackung verwenden.",
        "Reinigung und Wärme: PLA fern von Spülmaschine und Sonne; PETG nur so weit, wie der Hersteller es für das Filament beschreibt.",
        "Nach jeder Anpassung: Modell unter neuem Namen speichern, neu berechnen, neues STL slicen – nicht ein altes Mesh weiterverwenden.",
    ]),

    ("h1", "11. Offene Punkte"),
    ("ul", [
        "Echte Testdrucke auf dem P2S stehen noch aus. Erst danach sollten Spielwerte festgeschrieben werden.",
        "Modelltyp-Apostroph im Phase-3-Makro (Workaround in Kapitel 3.4).",
        "Init.py-Warnung (__file__) beim GUI-Start, unverändert gelassen.",
        "Bambu-Studio-Bilder fehlen, weil die Anwendung hier nicht zur Verfügung stand.",
        "Plattenverbinder in der GUI-Aufnahme nicht in einer Randtasche platziert (Kapitel 5.7).",
        "Plan 387 × 293 nicht als eigener Ordner in 01 abgelegt.",
        "Gridfinity-Mischbetrieb in der Praxis ungeprüft.",
    ]),
    ("p", "Ende des Handbuchs. Bei den Testdrucken die Punkte aus Kapitel 10 der Reihe nach abhaken und die gefundenen Spielwerte im Tabellenblatt festhalten."),
)


def table_html(rows):
    head, *body = rows
    th = "".join(f"<th>{html.escape(c)}</th>" for c in head)
    trs = []
    for r in body:
        trs.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def list_html(items, ordered=False):
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + f"</{tag}>"


def build_html() -> str:
    parts = ["""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Hausraster – Gesamthandbuch (Phase 5)</title>
<style>
@page { size: A4; margin: 16mm 16mm 18mm 16mm; }
html, body { font-family: "Calibri", "Segoe UI", "Liberation Sans", Arial, sans-serif;
  font-size: 11pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 18pt; color: #16324f; border-bottom: 2px solid #16324f;
  page-break-before: always; margin-top: 0; padding-bottom: 4px; }
h1:first-of-type { page-break-before: auto; }
h2 { font-size: 13.5pt; color: #1c4a73; margin-top: 1.2em; }
h3 { font-size: 12pt; color: #1c4a73; }
p { margin: 0.55em 0; }
.note, .warn { padding: 8px 12px; margin: 0.8em 0; border-radius: 3px; }
.note { background: #eef5fb; border-left: 4px solid #2a6aa3; }
.warn { background: #fbf3e8; border-left: 4px solid #b36b16; }
figure { margin: 0.9em 0 1.1em 0; page-break-inside: avoid; text-align: center; }
figure img { max-width: 100%; max-height: 118mm; height: auto; border: 1px solid #ccc; }
figcaption { font-size: 9.5pt; color: #333; margin-top: 4px; text-align: left; }
table { border-collapse: collapse; width: 100%; margin: 0.7em 0 1em 0;
  font-size: 9.5pt; page-break-inside: auto; }
th, td { border: 1px solid #9aa7b5; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #e4edf5; }
ol, ul { margin: 0.4em 0 0.8em 1.2em; padding: 0; }
li { margin: 0.2em 0; }
</style>
</head>
<body>
"""]
    first_h1 = True
    for block in BLOCKS:
        kind = block[0]
        if kind == "h1":
            parts.append(f"<h1>{html.escape(block[1])}</h1>")
        elif kind == "h2":
            parts.append(f"<h2>{html.escape(block[1])}</h2>")
        elif kind == "h3":
            parts.append(f"<h3>{html.escape(block[1])}</h3>")
        elif kind == "p":
            parts.append(f"<p>{html.escape(block[1])}</p>")
        elif kind == "note":
            parts.append(f"<p class='note'><strong>Hinweis.</strong> {html.escape(block[1])}</p>")
        elif kind == "warn":
            parts.append(f"<p class='warn'><strong>Wichtig.</strong> {html.escape(block[1])}</p>")
        elif kind == "ul":
            parts.append(list_html(block[1], False))
        elif kind == "ol":
            parts.append(list_html(block[1], True))
        elif kind == "table":
            parts.append(table_html(block[1]))
        elif kind == "img":
            src, cap = block[1], block[2]
            uri = Path(src).resolve().as_uri()
            parts.append(
                f"<figure><img src='{html.escape(uri)}' alt='{html.escape(cap)}'>"
                f"<figcaption>{html.escape(cap)}</figcaption></figure>"
            )
    parts.append("</body></html>")
    return "".join(parts)


def next_list_num_id(doc):
    """Neue Nummerierung, die wieder bei 1 beginnt (sonst läuft List Number durchs ganze Dokument)."""
    numbering = doc.part.numbering_part._element
    nums = numbering.findall(qn("w:num"))
    abstracts = numbering.findall(qn("w:abstractNum"))
    next_nid = max([int(n.get(qn("w:numId"))) for n in nums] + [0]) + 1
    # List Number style typically uses abstract 1 or the one referenced by an existing num
    abstract_id = "1"
    if nums:
        ref = nums[0].find(qn("w:abstractNumId"))
        if ref is not None and ref.get(qn("w:val")):
            abstract_id = ref.get(qn("w:val"))
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(next_nid))
    aid = OxmlElement("w:abstractNumId")
    aid.set(qn("w:val"), abstract_id)
    num.append(aid)
    lvlov = OxmlElement("w:lvlOverride")
    lvlov.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:startOverride")
    start.set(qn("w:val"), "1")
    lvlov.append(start)
    num.append(lvlov)
    numbering.append(num)
    return next_nid


def apply_num_id(paragraph, num_id):
    pPr = paragraph._p.get_or_add_pPr()
    old = pPr.find(qn("w:numPr"))
    if old is not None:
        pPr.remove(old)
    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    nid = OxmlElement("w:numId")
    nid.set(qn("w:val"), str(num_id))
    numPr.append(ilvl)
    numPr.append(nid)
    pPr.append(numPr)


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar"); fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    run._r.append(instr)
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld2)


def set_run_font(run, name="Calibri", size=11, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:cs"), name)


def shade_paragraph(p, hex_color):
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    pPr.append(shd)


def build_docx():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(16)
    section.right_margin = Mm(16)
    section.top_margin = Mm(16)
    section.bottom_margin = Mm(18)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    for i in range(1, 4):
        hs = doc.styles[f"Heading {i}"]
        hs.font.color.rgb = RGBColor(0x16, 0x32, 0x4F)
        hs.font.name = "Calibri"
        hs._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")

    header = section.header.paragraphs[0]
    header.text = "Hausraster – Gesamthandbuch (Phase 5)  ·  12. November 2026"
    for r in header.runs:
        set_run_font(r, size=9, color=(0x44, 0x44, 0x44))
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = footer.add_run("Seite ")
    set_run_font(r, size=9, color=(0x44, 0x44, 0x44))
    add_page_field(footer)

    usable = Mm(210) - Mm(16) - Mm(16)

    for block in BLOCKS:
        kind = block[0]
        if kind == "h1":
            doc.add_heading(block[1], level=1)
        elif kind == "h2":
            doc.add_heading(block[1], level=2)
        elif kind == "h3":
            doc.add_heading(block[1], level=3)
        elif kind == "p":
            p = doc.add_paragraph(block[1])
            p.paragraph_format.space_after = Pt(8)
        elif kind in ("note", "warn"):
            label = "Hinweis. " if kind == "note" else "Wichtig. "
            p = doc.add_paragraph()
            r = p.add_run(label + block[1])
            set_run_font(r, size=10.5)
            shade_paragraph(p, "EEF5FB" if kind == "note" else "FBF3E8")
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.space_before = Pt(6)
        elif kind == "ul":
            for item in block[1]:
                doc.add_paragraph(item, style="List Bullet")
        elif kind == "ol":
            num_id = next_list_num_id(doc)
            for item in block[1]:
                p = doc.add_paragraph(item, style="List Number")
                apply_num_id(p, num_id)
        elif kind == "table":
            rows = block[1]
            cols = len(rows[0])
            table = doc.add_table(rows=len(rows), cols=cols)
            table.style = "Table Grid"
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    c = table.cell(i, j)
                    c.text = ""
                    p = c.paragraphs[0]
                    r = p.add_run(cell)
                    set_run_font(r, size=9, bold=(i == 0))
                    if i == 0:
                        shade_paragraph(p, "E4EDF5")
            doc.add_paragraph()
        elif kind == "img":
            src, cap = block[1], block[2]
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(src, width=usable)
            cp = doc.add_paragraph(cap)
            cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in cp.runs:
                set_run_font(r, size=9, color=(0x33, 0x33, 0x33))
            cp.paragraph_format.space_after = Pt(12)

    doc.save(str(OUT_DOCX))


def build_md():
    lines = []
    for block in BLOCKS:
        kind = block[0]
        if kind == "h1":
            lines += ["", f"# {block[1]}", ""]
        elif kind == "h2":
            lines += ["", f"## {block[1]}", ""]
        elif kind == "h3":
            lines += ["", f"### {block[1]}", ""]
        elif kind == "p":
            lines += [block[1], ""]
        elif kind == "note":
            lines += [f"> **Hinweis.** {block[1]}", ""]
        elif kind == "warn":
            lines += [f"> **Wichtig.** {block[1]}", ""]
        elif kind == "ul":
            lines += [f"- {i}" for i in block[1]] + [""]
        elif kind == "ol":
            lines += [f"{n}. {i}" for n, i in enumerate(block[1], 1)] + [""]
        elif kind == "table":
            rows = block[1]
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("| " + " | ".join("---" for _ in rows[0]) + " |")
            for r in rows[1:]:
                lines.append("| " + " | ".join(r) + " |")
            lines.append("")
        elif kind == "img":
            lines += [f"![{block[2]}]({block[1]})", "", f"*{block[2]}*", ""]
    OUT_MD.write_text("\n".join(lines).lstrip() + "\n", encoding="utf-8")


def main():
    html_text = build_html()
    OUT_HTML.write_text(html_text, encoding="utf-8")
    print("HTML", OUT_HTML, OUT_HTML.stat().st_size)
    build_md()
    print("MD", OUT_MD, OUT_MD.stat().st_size)
    build_docx()
    print("DOCX", OUT_DOCX, OUT_DOCX.stat().st_size)
    chrome = None
    for c in ("google-chrome", "chromium", "chromium-browser"):
        if subprocess.run(["which", c], capture_output=True).returncode == 0:
            chrome = c
            break
    if not chrome:
        raise SystemExit("kein Chrome/Chromium für PDF")
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--print-to-pdf={OUT_PDF}",
        f"file://{OUT_HTML}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print("chrome rc", r.returncode)
    if r.stderr:
        print(r.stderr[-800:])
    if not OUT_PDF.exists():
        raise SystemExit("PDF fehlt")
    print("PDF", OUT_PDF, OUT_PDF.stat().st_size)


if __name__ == "__main__":
    main()
