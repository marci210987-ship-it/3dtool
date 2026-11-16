# Intelligente Positionierung im Zeichenblatt

## Bedienung

Eine Form im Blatt oder in der Formenliste wählen. Die Aktionen stehen direkt in den Eigenschaften:

- **Auf Bauteilmitte setzen** bindet beide Achsen an die Bauteilmitte. **Horizontal zentrieren** und **Vertikal zentrieren** binden nur die jeweilige Achse. Ein verschobener Ursprung wird berücksichtigt.
- Runde Formen haben ein direktes Feld **Durchmesser (mm)**; Dezimalkomma wird unterstützt. Ungültige Eingaben verändern die Geometrie nicht und werden beim Verlassen zurückgesetzt.
- **Abstand zur Bauteilkante** eingeben und **Links**, **Rechts**, **Unten** oder **Oben** wählen. Gemessen wird vom Formrand zum achsparallelen Bauteilrahmen, nicht von der Lochmitte. Die Abstände werden angezeigt; negative Werte zeigen einen Überstand.
- **Bezug für Mittelpunkt** wählen und **Mittelpunkt übernehmen**: Beide Achsen folgen der gewählten Form. Kreisbezüge werden abgewiesen.
- Bei Kreisen: **Kreis um Mittelpunkt erstellen**, Durchmesser und **Material entfernen (Loch)** oder **Material hinzufügen** wählen, dann **Kreis erstellen**. Der neue Kreis folgt dem ursprünglichen Mittelpunkt, auch über mehrere Bezugskreise hinweg. Die Höhe des Materialkreises kann anschließend wie bisher geändert werden.
- Drei oder mehr Formen mit Umschalt-Klick wählen. **Gleichmäßig verteilen ↔ / ↕** verteilt die Mittelpunkte zwischen den beiden äußeren Formen; diese bleiben stehen. Die verteilte Achse wird freigegeben.

**Einrasten** in der Werkzeugleiste schaltet die geometrischen Fangpunkte um. Erkannt werden Kreis- und Formmitten, die Bauteilmitte, Ecken und Kantenmittelpunkte von Polygonen und gedrehten Rechtecken. Eine Markierung hebt den tatsächlich getroffenen Punkt hervor; gestrichelte Linien zeigen Fluchten. Die Fangtoleranz beträgt etwa acht Bildschirmpixel. Das gewählte Maßraster bleibt unabhängig davon aktiv. Einrasten allein legt keine parametrische Bindung an.

## Beziehungen und manuelles Bearbeiten

Größenänderungen und Bewegungen freier Materialformen führen gebundene Positionen nach. Auch ein geänderter Lochdurchmesser erhält einen eingestellten Randabstand. Manuelle x-/y-Eingaben oder Ziehen lösen nur die geänderten Achsen. **Positionsbindung lösen** gibt beide Achsen frei. Änderungen und Bindungen sind rückgängig machbar.

Beim Löschen einer Bezugsform bleibt die abhängige Form an ihrer letzten Position stehen; der verlorene Bezug wird gelöst. Formkopien aus Mustern bekommen eigene IDs und freie Positionen. Das Duplizieren eines ganzen Teils erhält dessen interne Beziehungen.

## Architektur und Dateiformat

`ui/src/positionierung.ts` enthält die reine Rechenlogik; `position-panel.tsx` die Kontextaktionen. `zeichenblatt.tsx` löst bei jeder Änderung der Formen die Beziehungen auf, bevor Vorschau, Projektdatei oder Exportauftrag die Koordinaten erhalten. Der bestehende Python-/FreeCAD-Pfad arbeitet weiterhin mit vollständig berechneten Geometriekoordinaten.

Neue optionale Felder je Form: `form_id` (stabile ID innerhalb des Teils) und `position.x` / `position.y`. Jede Achse enthält `quelle` (`teil` oder Form-ID), `lage` (`mitte`, `min`, `max`) und optional `abstand` in mm. Alte Projektdateien bleiben gültig; `FORMAT_VERSION` bleibt 1. Die Daten werden beim Speichern und Laden vom Sidecar erhalten.

## Grenzen

- Zentrieren und Kantenabstände beziehen sich auf den achsparallelen Außenrahmen **freier Materialformen**, nicht auf Flächenschwerpunkte oder den kürzesten Abstand zur Kontur. Gebundene Aufsätze beeinflussen ihren eigenen Bauteilbezug nicht. Bei gedrehten, runden oder konkaven Teilen kann eine am Außenrahmen ausgerichtete Form daher außerhalb des Materials liegen. Die bestehende Geometrieprüfung bleibt zuständig.
- Ein reines Drehprofil ohne Materialform stellt für diese Kontextaktionen keinen Bauteilrahmen bereit.
- Beziehungen werden im CAD-Studio-Zeicheneditor aufgelöst. Direkte Änderungen an JSON-Dateien oder später im FCStd-Tabellenblatt berechnen diese Beziehungen nicht neu.
- Materialformen werden wie bisher zuerst vereinigt und danach alle Löcher abgezogen. Ein Materialkreis füllt ein vorhandenes Loch nicht automatisch wieder auf.
- Verteilung verwendet gleiche Mittelpunktabstände, nicht gleiche Lücken zwischen unterschiedlich großen Formen.
- Kein neuer Installer und kein Druck-/Passungstest gehören zu dieser Änderung.

## Tests

Rechenfälle: `ui/src/positionierung.test.ts`; UI-Abläufe: `ui/src/positionierung-ui.test.tsx`; Browser inklusive schmaler Ansicht und sichtbarer Fangmarkierung: `tests/e2e/positionierung.spec.ts`; Projekt-/Exportvertrag und echter FreeCAD-Export: `tests/test_positionierung.py`. Die Python-Fälle sind im Windows-CI-Lauf aufgenommen. Ergebnisse stehen im aktuellen Nachtrag von `TESTBERICHT.md`.
