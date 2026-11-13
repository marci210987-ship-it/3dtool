# Bedienungsanleitung – Schubladen-Konfigurator

CAD Studio ist für den eigenen Hausgebrauch gedacht. Die Oberfläche ist auf Deutsch, alle Maße sind Millimeter. Es ist kein allgemeines CAD-Programm: es gibt keine Skizzen, keine Arbeits­ebenen und keine Befehlszeile.

Der Druckerbezug ist ein Bambu Lab P2S mit 256 × 256 × 256 mm Bauraum. Das Raster ist das Hausraster 0.2-qs1, 42 mm je Feld, 7 mm je Höhenstufe, anschlussfähig an Gridfinity.

## Start

Auf der Startseite liegen vier Bereiche. **Schubladen-Konfigurator** und **Eigene Teile zeichnen** sind benutzbar. Ersatzteile, Kabelmanagement und Elektronikgehäuse stehen auf „in Vorbereitung“.

Darunter stehen die zuletzt geöffneten Projekte. Ein Klick lädt die Datei wieder, auch nach einem Neustart des Programms.

## 1. Schublade vermessen

- **Innenbreite** und **Innentiefe**: der freie Raum in der Schublade, dort wo die Platten stehen.
- **Nutzbare Höhe**: vom Schubladenboden bis zum höchsten Punkt, den eine Box erreichen darf.
- **Spiel zur Wand**: Abstand ringsum, damit die Platten nicht klemmen. Vorgabe 1,0 mm. Das ist kein gemessener Wert.
- **Verbinder-Spiel**: Luft in den Schwalbenschwanz-Taschen. Vorgabe 0,20 mm. Ebenfalls ungemessen.
- **Extra-Rand**: zusätzlicher leerer Streifen je Seite, zum Beispiel an einem Griff. Normalerweise 0.

„Raster erzeugen“ teilt die Fläche in 42-mm-Felder und in Grundplatten, die auf das Druckbett passen. Der Rest neben den ganzen Feldern wird nach Möglichkeit in die äußeren Platten eingearbeitet.

Wenn ein Rest nicht mehr in den Bauraum passt, bleibt ein **Randstreifen** übrig. Er wird als glatte Füllplatte in Plattenhöhe erzeugt (Teile S1, S2, …), ohne Verbinder. Du legst ihn lose neben die Grundplatten. Die Passung ist nicht geprüft.

## 2. Raster ansehen

Jede Platte hat eine Nummer (P1, P2, …), die Feldzahl und das Außenmaß. „passt aufs Druckbett“ bedeutet nur, dass Breite, Tiefe und Höhe unter 256 mm liegen. Es ist keine Aussage über die Druckzeit oder die Haftung.

## 3. Boxen stellen

Links stehen fertige Sorten:

| Sorte | Bedeutung |
|---|---|
| Kleine, schmale, mittlere, große Box | Normale Rasterboxen |
| Besteckfach | Schmale Box mit festen Unterteilungen |
| Box mit Deckel | Deckel als eigenes Teil, liegt auf der Stapellippe |
| Kabelbox | Fächer mit Kerben oben |
| Bestecksortierer | Eigener Einsatz des Besteck-Generators, mindestens etwa 6 × 2 Felder, wird in Segmente geteilt |

Eine Box antippen setzt sie auf das nächste freie Feld. Danach:

- **Wunschliste** (aufklappbar unter dem Editor): Anzahl je Sorte angeben, „Wünsche platzieren“ setzt sie zuerst (größte zuerst, bei Bedarf um 90° gedreht, dorthin, wo sie am meisten Kontakt zu Wand, Boxen und eigenen Teilen haben, also in Ecken und aneinander), optional füllt das Tool danach den Rest. Passt etwas nicht, steht in der Meldung, wie viele von wie vielen platziert wurden und warum. Zu hohe Sorten werden in der Höhe abgesenkt, wenn die Schublade niedrig ist.
- **Füllstil:** „Einheitliche Größe“ (Standard) wählt die Boxgröße mit den wenigsten Boxen und Größen, „Möglichst große Boxen“ nimmt überall die größte, „Kleine Boxen“ setzt lauter 1 × 1.
- **Freie Felder automatisch füllen**: setzt auf jedes freie Feld die größte passende Rasterbox (bis 3 × 3 Felder, so hoch wie die Schublade erlaubt, höchstens 3 Stufen). Vorhandene Boxen bleiben unverändert, und Felder unter platzierten eigenen Teilen bleiben frei.
- ziehen oder mit den Tasten Links, Rechts, Nach vorn, Nach hinten verschieben
- drehen (90°)
- duplizieren
- entfernen
- Höhe in 7-mm-Stufen ändern
- Fächer teilen, Deckel oder herausnehmbare Trennwände einschalten

Freie Felder sind hellgrün. Überlappende Boxen werden rot und mit einem Hinweis gezeigt. Solange eine Überlappung, ein Überstand oder eine zu große Höhe besteht, lässt sich nichts exportieren.

Die 3D-Ansicht in diesem Schritt ist eine **vereinfachte Vorschau**. Sie ist ausdrücklich nicht die Druckgeometrie.

## 4. Eigene Teile zeichnen

Jedes Teil besteht aus Formen in der Draufsicht (Ursprung links unten, Millimeter): Rechteck, Kreis und Vieleck. Eine Form fügt Material hinzu. Eine Form mit „Loch“ schneidet es weg. Das Teil wird auf die eingestellte **Höhe** gerade nach oben gezogen. Mit **Boden unter Löchern** (mm) werden Löcher zu Sacklöchern; 0 heißt durchgehend.

- Werkzeug wählen, mit gedrückter Maustaste ziehen (Rechteck, Kreis) oder Punkte anklicken (Vieleck; Klick auf den ersten Punkt, Enter oder „Fertig“ schließt).
- **Rückgängig / Wiederholen:** Knöpfe in der Werkzeugleiste oder Strg+Z und Strg+Y (Strg+Umschalt+Z) mit dem Zeichenblatt im Fokus. Aufeinanderfolgende Eingaben in Zahlenfeldern zählen als ein Schritt; ein Ziehen ist ein Schritt.
- **Maße anzeigen:** Breite, Tiefe und Durchmesser stehen am Blatt, auch live beim Ziehen. Bei der gewählten Form kommen Vieleck-Kantenlängen dazu. Der Haken „Maße anzeigen“ schaltet sie aus.
- **Einrasten:** Beim Zeichnen und Verschieben rasten Formen an Ecken, Kanten und Mitten anderer Formen ein; orange Hilfslinien zeigen, woran. Der Haken „Einrasten“ schaltet das ab.
- **Ausrichten:** Bei einer gewählten Form richten die Knöpfe Mitte ↔, Mitte ↕, Links, Rechts, Unten, Oben sie am Außenmaß der übrigen Formen aus (ein Loch zum Beispiel an der Plattenmitte).
- Das Raster rastet den Zeiger ein (0,1 bis 10 mm).
- „Auswählen“: Form anklicken und ziehen, Entf löscht. Zahlenfelder ändern die genauen Maße.
- **In die Schublade stellen:** Mit dem Haken „In die Schublade stellen“ erscheint ein Lageplan. Das Teil lässt sich ziehen, per Zahl setzen und um 90° drehen. Es steht auf der Platte und darf keine Box und kein anderes Teil überlappen, nicht aus der Schublade ragen und nicht höher sein als die nutzbare Höhe. Platzierte Teile erscheinen grau mit ihrer Nummer im Montageplan.
- Auf der Startseite gibt es „Eigene Teile zeichnen“ ohne Schublade. Dann entstehen nur diese Teile und eine Stückliste, kein Montageplan.

**Stufen und Ebenen**
- Jede Form kann **Starthöhe** und **Höhe** bekommen. Ohne Angabe reicht sie von 0 bis zur Standardhöhe. Mit Starthöhe reicht sie von dort bis zur Standardhöhe, sofern keine eigene Höhe gesetzt ist. So entstehen Sockel mit Aufsatz, Wände auf einer Platte oder Absätze.
- Bei Löchern bedeuten die Felder „ab Höhe“ und „Tiefe“: so lassen sich Taschen mitten im Teil schneiden. Ohne Angabe schneidet ein Loch ab dem Boden nach oben durch.
- Die Gesamthöhe ist die höchste Oberkante. Höhere Formen sind in der Vorschau dunkler.
- Alle Formen müssen zusammen **einen** Körper ergeben. Eine schwebende Form, die nichts berührt, meldet der Export.

**Vorlagen:** Unter „Aus Vorlage“ gibt es Platte mit Bohrungen, Winkelhalter, Stufenblock, Schale mit Mulde, Rampe, Platte mit Senkungen und Stabhalter. Sie legen ein neues Teil an, das du frei ändern kannst.

**Eigene Vorlagen:** Ein gültiges Teil lässt sich mit „Als Vorlage speichern“ ablegen (gleicher Name ersetzt). Sie erscheinen unter „Meine Vorlagen“, bleiben nach einem Neustart erhalten und lassen sich unter „Meine Vorlagen verwalten“ löschen. Die Position in der Schublade wird nicht mitgespeichert. Die Datei `vorlagen.json` liegt im Programmordner (neben den Einstellungen), unter Windows in `%APPDATA%\CADStudio`.

**Schräge, Keil und Kanten je Form**
- **Verjüngung nach oben** (Material): die Form wird nach oben schmaler, etwa ein Sockel mit schrägen Seiten. Muss kleiner als die halbe kleinste Seite sein.
- **Aufweitung nach oben** (Loch): ein Konus, zum Beispiel für Senkschrauben.
- **Keil** (nur Rechteck, Material): der Höhenzuwachs nach hinten (negativ: fällt nach hinten), für Rampen und geneigte Auflagen. Nicht mit Schräge, Eckenradius oder Teilkante kombinierbar.
- **Oberrand dieser Form / Lochrand:** Fase oder Rundung nur an der Oberkante dieser einen Form bzw. am Rand eines Lochs. Nicht mit Schräge oder Keil an derselben Form kombinierbar; die Teilkante oben lässt sich mit Formkanten an derselben Kante nicht sinnvoll kombinieren. Ist die Kante verdeckt oder passt der Wert nicht, meldet der Export das.

**Rundungen und Fasen**
- **Eckenradius** am Rechteck (Formfeld, 0 = eckig): höchstens die halbe kürzere Seite.
- **Obere Kante** des Teils: scharfkantig, Fase oder Rundung mit Größe in mm. Sie wirkt auf die Außenkante der Oberseite, nicht auf Löcher.
- **Fase unten** (mm): bricht die untere Außenkante, gegen den „Elefantenfuß“ beim Druck.
- Obere und untere Kante zusammen dürfen höchstens die halbe Höhe betragen. Passt ein Wert geometrisch nicht, meldet der Export das und bleibt gesperrt.

Grenzen: keine Gewinde, keine frei geformten Flächen, keine Texte. Ein Vieleck darf sich nicht selbst schneiden. Maße über 256 mm werden abgelehnt.

## 5. Berechnen und speichern

„Alle Teile berechnen“ startet FreeCAD im Hintergrund und erzeugt:

- jede Grundplatte (QS1-Geometrie, Verbinder-Taschen auf den Rippen)
- jede Box, inklusive Deckel oder Trennwänden, wenn angewählt
- einen Plattenverbinder je Stoßrippe (eine Datei, Anzahl in der Stückliste)
- einen Rastclip (Anzahl ist ein Vorschlag, keine gemessene Empfehlung)
- Stückliste (CSV und JSON)
- Montageübersicht als HTML, SVG, PDF und PNG, mit Teilenummern

Grün wird der Abschluss nur, wenn jede Datei vorhanden ist, das Dreiecksnetz geschlossen ist und die FCStd-Datei einen gültigen Körper mit Tabellenblatt enthält. Andernfalls steht dort **Nicht exportiert** und der Grund.

Die Projektdatei (`.cadstudio.json`) speichert Maße, Spiel und die Lage der Boxen. Die STL-Dateien liegen daneben im Exportordner.

## Was die Dateien nicht versprechen

- Die Passung 1,0 mm und 0,20 mm ist nicht an einem gedruckten Teil geprüft.
- Die Gewichtsangabe ist aus dem CAD-Volumen geschätzt.
- Lebensmittel, Spülmaschine und Wärme sind nicht geprüft.
- Die Ursprungsplatten ohne den Zusatz QS1 sind fehlerhaft und werden nicht verwendet.
