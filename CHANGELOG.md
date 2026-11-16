# Änderungsprotokoll

## Unveröffentlicht

- Lokale Wiederherstellungskopie und Schutz ungespeicherter Änderungen.
- Abbrechbare Exportaufträge mit sichtbarem Status und aufklappbaren Fehlerdetails.
- Vollständige 3D-Teilevorschau mit Sichtbarkeitsschaltern, Zwischenspeicher und Überspringen überholter Anfragen.
- Gespeicherte Druck-/Materialprofile und Loch/Stift-Kalibrierprojekt mit fünf Spielmaßen.
- Dauerhafte Skizzenbedingungen für Rechtecke und Kreise (mittig, Abstand, gleiche Größe, parallel).
- Stückliste berücksichtigt den Projektbauraum anstelle fest vorgegebener 256 mm.
- Regressionstests für Wiederherstellung, Bedingungen, Vorschau, Abbruch und Bauraum.

## 0.5.0

- 3D-Ansicht: Schnittebene (waagerecht und senkrecht, mit Schieber und Seitenwechsel) und Messen zwischen zwei Punkten.
- Druckausrichtung: Bewertung der sechs Lagen nach Überhang, Auflage und Höhe mit Empfehlung. Schraubdeckel des Gehäuses, Stopfen und Drehknopf werden druckfertig gedreht exportiert.
- Zeichnen: Schraubenlöcher voreinstellen (Durchgang, Kernloch, Gewindeeinsatz, M2 bis M5, Senk- und Zylinderkopf) und Schraubdome.
- Druckhinweise gelten jetzt auch für Ersatzteile, Kabelmanagement und Gehäuse. Kabelkanal, 90°-Ecke und Kabelauslass melden die 1,8 mm hohe Stufe zwischen Buchse und Boden (Stützen nur auf dem Druckbett einschalten); die Anleitung nennt das jetzt.
- Nicht gedruckt geprüft.
- Der Windows-Installer ist `CAD-Studio-0.5.0-Setup.exe` und `CAD-Studio-0.5.0.msi` auf der Releases-Seite. FreeCAD 1.1.x muss separat installiert sein. Der Installer ist nicht code-signiert, Windows SmartScreen kann warnen. Ein Hardware-Test auf Marcels PC ist noch nicht ausgeführt.

## 0.4.0

- Zeichnen: Vieleck-Punkte ziehen, einfügen und löschen; Langloch; Vieleck mit Eckenradius; Senkung, Gegenbohrung und Sechskant-Tasche an Löchern; Text (Pixelschrift); Gruppen mit Umschalt-Klick; Seitenlöcher; Drehteile aus einem Profil.
- Export: Druckhinweise zu Überhängen und dünnen Stellen bei eigenen Teilen.
- 3D-Ansicht mit der echten Geometrie (aus FreeCAD) beim Zeichnen, bei Ersatzteilen, Kabelmanagement und Gehäuse; Druckhinweise erscheinen dort live.
- Auto-Bestückung: Wünsche mit Seite (links, rechts, vorne, hinten) und Gruppe, Strahlsuche über mehrere Anordnungen, bessere Aufteilung des Rests als beim Zeilenverfahren.
- Nicht gedruckt geprüft; Maße und Toleranzen sind Modellwerte.
- Der Windows-Installer ist `CAD-Studio-0.4.0-Setup.exe` und `CAD-Studio-0.4.0.msi` auf der Releases-Seite. FreeCAD 1.1.x muss separat installiert sein. Der Installer ist nicht code-signiert, Windows SmartScreen kann warnen. Ein Hardware-Test auf Marcels PC ist noch nicht ausgeführt.

## 0.3.0

- Der Windows-Installer bleibt als GitHub Release liegen: `CAD-Studio-0.3.0-Setup.exe` und `CAD-Studio-0.3.0.msi`.
- FreeCAD 1.1.x muss separat installiert sein. Der Installer enthält FreeCAD nicht.
- Der Installer ist nicht code-signiert. Windows SmartScreen kann warnen.
- Ein Hardware-Test auf Marcels PC ist noch nicht ausgeführt.

## 0.2.0

- Schubladen-Konfigurator mit Hausraster 0.2-qs1, STL, FCStd, Stückliste und Montageplan.
- Eigene Teile zeichnen, inklusive SVG- und DXF-Umrissen.
- Ersatzteil-Generator mit acht parametrischen Teilen.
- Modulares Kabelmanagement mit gemeinsamer Steckverbindung.
- Elektronikgehäuse mit Schraub- und Schiebedeckel, Platinenstützen und Öffnungen.
- Oberfläche mit FrohnLabs-Wortmarke, dunkler Kopfleiste und Bambu-Grün.
- Im Schubladenplan steht der Box-Typ und die Feldgröße. Eine 1×1-Box zeigt nur „1×1“.

Ein Start auf Windows-Hardware und ein Druck auf dem P2S sind nicht ausgeführt.
