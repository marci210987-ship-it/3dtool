# Bedienungsanleitung – Schubladen-Konfigurator

CAD Studio ist für den eigenen Hausgebrauch gedacht. Die Oberfläche ist auf Deutsch, alle Maße sind Millimeter. Es ist kein allgemeines CAD-Programm: es gibt keine Skizzen, keine Arbeits­ebenen und keine Befehlszeile. Die Kopfleiste ist dunkelblau mit der FrohnLabs-Wortmarke, Aktionen sind grün, der Arbeitsbereich hell.

Der Druckerbezug ist ein Bambu Lab P2S mit 256 × 256 × 256 mm Bauraum. Das Raster ist das Hausraster 0.2-qs1, 42 mm je Feld, 7 mm je Höhenstufe, anschlussfähig an Gridfinity.

## Installer herunterladen

Die Windows-Dateien liegen auf der [Releases-Seite](https://github.com/marci210987-ship-it/3dtool/releases): `CAD-Studio-0.5.0-Setup.exe` oder `CAD-Studio-0.5.0.msi`. FreeCAD 1.1.x muss separat installiert sein. Der Installer ist nicht code-signiert, Windows SmartScreen kann warnen. Ein Hardware-Test auf Marcels PC ist noch nicht ausgeführt.

## Start

Auf der Startseite liegen fünf Bereiche. **Schubladen-Konfigurator**, **Eigene Teile zeichnen**, **Ersatzteile**, **Kabelmanagement** und **Elektronikgehäuse** sind benutzbar.

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

Auf jeder Box steht der Typ und die Feldgröße, zum Beispiel „Große Box“ und „2×3“. Eine Box von einem Feld zeigt nur „1×1“, damit der Text in der Fläche bleibt. Die gewählte Box ist grün mit weißer Schrift. Freie Felder sind hellgrün. Überlappende Boxen werden rot und mit einem Hinweis gezeigt. Solange eine Überlappung, ein Überstand oder eine zu große Höhe besteht, lässt sich nichts exportieren.

Die 3D-Ansicht in diesem Schritt ist eine **vereinfachte Vorschau**. Sie ist ausdrücklich nicht die Druckgeometrie.

## 4. Eigene Teile zeichnen

Jedes Teil besteht aus Formen in der Draufsicht (Ursprung links unten, Millimeter): Rechteck, Kreis und Vieleck. Eine Form fügt Material hinzu. Eine Form mit „Loch“ schneidet es weg. Das Teil wird auf die eingestellte **Höhe** gerade nach oben gezogen. Mit **Boden unter Löchern** (mm) werden Löcher zu Sacklöchern; 0 heißt durchgehend.

- Werkzeug wählen, mit gedrückter Maustaste ziehen (Rechteck, Kreis) oder Punkte anklicken (Vieleck; Klick auf den ersten Punkt, Enter oder „Fertig“ schließt).
- **Rückgängig / Wiederholen:** Knöpfe in der Werkzeugleiste oder Strg+Z und Strg+Y (Strg+Umschalt+Z) mit dem Zeichenblatt im Fokus. Aufeinanderfolgende Eingaben in Zahlenfeldern zählen als ein Schritt; ein Ziehen ist ein Schritt.
- **Maße anzeigen:** Breite, Tiefe und Durchmesser stehen am Blatt, auch live beim Ziehen. Bei der gewählten Form kommen Vieleck-Kantenlängen dazu. Der Haken „Maße anzeigen“ schaltet sie aus.
- **Maße per Eingabe ändern:** Ein Klick auf ein Maß am Blatt (Breite, Tiefe eines Rechtecks, Durchmesser eines Kreises) öffnet ein Eingabefeld. Enter übernimmt, Esc bricht ab. Zu kleine oder ungültige Werte werden nicht übernommen. Ein Eckenradius schrumpft mit, wenn die kürzere Seite kleiner wird.
- **Umriss importieren (SVG oder DXF):** In der Teileliste „Umriss importieren“ wählen. Das Tool liest geschlossene Umrisse: Rechtecke, Kreise, Ellipsen, Polygone, Pfade (Linien, Kurven, Bögen), bei DXF Polylinien (auch mit Bögen), Kreise sowie Linien und Bögen, die einen geschlossenen Umriss ergeben. Umrisse, die in einem anderen liegen, werden zu Löchern (Gerade-Ungerade-Regel). Du siehst Größe, Anzahl der Formen und Hinweise, stellst den Maßstab (mm je Einheit) und die Höhe ein und fügst das Ergebnis als neues Teil ein. Nicht unterstützt sind Text, Splines, Blöcke und Bilder; Text vorher in Pfade umwandeln. Die Datei darf höchstens 5 MB haben, es sind höchstens 200 Formen möglich.
- **Einrasten:** Beim Zeichnen und Verschieben rasten Formen an Ecken, Kanten und Mitten anderer Formen ein; orange Hilfslinien zeigen, woran. Der Haken „Einrasten“ schaltet das ab.
- **Muster, Kopie und Spiegeln** (aufklappbar bei der gewählten Form):
  - **Form kopieren** legt eine Kopie um 5 / 5 mm versetzt an.
  - **Reihe oder Gitter:** Spalten, Zeilen und Abstand von Mitte zu Mitte (Voreinstellung: Formgröße plus 5 mm). Das Original zählt mit; es entstehen nur die Kopien. Eine Reihe ist ein Gitter mit einer Zeile.
  - **Kreismuster** für Kreise, Vielecke und Rechtecke: Anzahl mit Original, Mitte (Voreinstellung: Mitte der übrigen Formen) und Gesamtwinkel. 360° verteilt gleichmäßig auf den Vollkreis, ein kleinerer Winkel auf den Bogen. Rechtecke drehen mit. Ein Rechteck mit Keil lässt sich nicht drehen.
  - **Spiegeln** an der senkrechten oder waagrechten Mittelachse der übrigen Formen (ohne andere Formen: an der eigenen Mitte), als Kopie oder mit „Original ersetzen“. Ein Keil läuft nach dem Spiegeln in die Gegenrichtung.
  - Höchstens 200 Formen je Teil; ein Muster, das darüber hinausginge, wird abgelehnt. Jeder Schritt ist mit Rückgängig zurücknehmbar.
- **Rechtecke drehen:** Das Feld „Drehwinkel“ (Grad, gegen den Uhrzeigersinn, um die Mitte) und die Knöpfe +15° und +90° drehen ein Rechteck, auch als Loch und mit Eckenradius oder Kante. Das Außenmaß und die Fangpunkte folgen der Drehung. Ein Rechteck mit Keil lässt sich nicht drehen.
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

### Erweiterte Formen (Stand: Tests mit FreeCAD, nicht gedruckt)

- **Langloch:** Werkzeug „Langloch“, von der Mitte des einen Endes zur Mitte des anderen ziehen. Die Breite steht in der Leiste. Intern ein Rechteck mit vollem Eckenradius und Drehwinkel.
- **Vieleck mit Rundung:** Beim gewählten Vieleck „Eckenradius“ setzen. Alle Ecken bekommen Kreisbögen. Der Radius darf höchstens die halbe kürzeste Seite sein. Nicht kombinierbar mit Fase oder Rundung der Kante.
- **Senkung am runden Loch:** Beim gewählten Loch „Senkung“ wählen: 90°-Senkung, Gegenbohrung oder Sechskant-Tasche (Schlüsselweite), oben oder unten.
- **Text:** Werkzeug „Text“, Inhalt, Höhe, erhaben (auf der Oberseite) oder vertieft. Es ist eine 5×7-Pixelschrift (Großbuchstaben, Ziffern, einige Zeichen; Ä Ö Ü ß werden zu AE OE UE SS). Ein Pixel (Höhe / 7) muss mindestens 0,4 mm groß sein.
- **Gruppen:** Umschalt-Klick wählt mehrere Formen. Ziehen verschiebt alle, dazu „Daneben kopieren“, Spiegeln und Löschen.
- **Seitenlöcher:** Bohrung oder Rechteck-Schlitz von einer der vier Wände, Position entlang der Wand, Höhe, Tiefe (0 = durch).
- **Drehteil:** Profil aus Punkten (Radius, Höhe), das um eine senkrechte Achse gedreht wird (Vorlagen Knopf, Hülse, Rolle, Kegelstumpf). Formen und Löcher lassen sich zusätzlich zeichnen.
- **Druckhinweise:** Beim Export meldet das Programm Überhänge (waagerechte Decken ab 10 mm Spannweite, Flächen steiler als 45°) und dünne Stellen unter 0,8 mm. Das sind Faustregeln für eine 0,4-mm-Düse, keine Slicer-Simulation, und sie verhindern den Export nicht.

### 3D-Ansicht

Unter dem Zeichenblatt, bei Ersatzteilen, Kabelmanagement und Gehäuse steht eine 3D-Ansicht. Sie zeigt die echte Geometrie, die FreeCAD auch für den Export baut (mit Text, Senkungen, Seitenlöchern und Drehteilen), nicht die vereinfachte Vorschau. Sie rechnet nach jeder Änderung nach kurzer Pause neu (meist unter einer Sekunde, der erste Aufruf etwas länger). Ziehen dreht, das Mausrad zoomt, die rechte Maustaste verschiebt; „Schräg“, „Vorne“, „Oben“ und „Seite“ setzen die Ansicht. Bei ungültigen Eingaben steht die Fehlermeldung statt eines Körpers. FreeCAD muss installiert sein. Darunter erscheinen die Druckhinweise.

### Wunschliste mit Seite und Gruppe

In der Wunschliste lässt sich je Boxsorte eine Seite (links, rechts, vorne, hinten) und eine Gruppe (A, B, C) wählen. Die Sorte wandert dann bevorzugt an diese Seite, Boxen derselben Gruppe liegen beieinander. Das Tool probiert mehrere Anordnungen und füllt den Rest mit möglichst wenigen, einheitlichen Boxen. Die Seite ist ein starker Wunsch, aber keine Pflicht: wenn der Platz fehlt, steht die Box anderswo.

### Schnitt, Messen und Druckausrichtung (3D-Ansicht)

- **Schnitt:** Unter der 3D-Ansicht schneidet „Schnitt“ das Modell waagerecht (Höhe) oder senkrecht (quer x, längs y) auf. Der Schieber stellt die Position in Millimetern ein, „Seite wechseln“ zeigt die andere Hälfte. Die Schnittfläche erscheint in Orange. So siehst du Wandstärken, Bohrungstiefen und Hohlräume.
- **Messen:** Haken „Messen“ setzen und zwei Punkte am Modell anklicken (beide am selben Teil). Es erscheinen Abstand, Δx, Δy, Δz und die Neigung. Ecken in der Nähe werden gefangen. Wer dreht oder zoomt, setzt dabei keinen Punkt.
- **Druckausrichtung:** Aufklappbar unter der Ansicht. Das Programm bewertet alle sechs Lagen des Teils nach Überhang (Flächen, die steiler als 45° von der Senkrechten nach unten zeigen), Auflagefläche auf dem Bett und Höhe und empfiehlt die beste. Eine andere Lage stellst du im Slicer ein (Bambu Studio: „Auf Fläche legen“). Das sind Faustregeln, keine Slicer-Simulation.
- Aufgrund dieser Auswertung werden der Schraubdeckel des Gehäuses sowie Stopfen und Drehknopf (Ersatzteile) jetzt druckfertig gedreht exportiert. Kabelkanal, 90°-Ecke und Kabelauslass zeigen bei der Auswertung einen großen Überhang an der Stufe zwischen Buchse und Kanalboden; Das Modell ist nicht geändert: eine 45°-Schräge an der Stufe würde das Problem nicht lösen, weil der ganze Kanalboden 1,8 mm über dem Bett liegt. Beim Drucken „Stützen nur auf dem Druckbett“ einschalten; die Druckhinweise melden die Stelle.

### Schraubenlöcher und Schraubdome

- **Schraubenloch voreinstellen:** Beim gewählten runden Loch aufklappen, Schraube (M2 bis M5) und Zweck wählen: Durchgangsloch (ISO 273 mittel), Kernloch zum Gewindeschneiden oder Loch für einen Gewindeeinsatz zum Einschmelzen (Außendurchmesser minus Abzug; Datenblatt des Einsatzes prüfen). Ein einstellbarer Zuschlag gleicht aus, dass gedruckte Löcher kleiner werden. Beim Durchgangsloch gibt es Senkkopf und Zylinderkopf (Gegenbohrung) mit Kopfspiel.
- **Schraubdom:** Unter den Eigenschaften „Schraubdom hinzufügen“: Zylinder mit Schraubenloch auf der Platte. Fußhöhe ist die Oberseite der Form darunter, das Loch beginnt dort und lässt die Platte heil.
- Die Zuschläge (0,1 mm, Abzug 0,4 mm, Kopfspiel 0,3 mm) sind Vorgaben und nicht gedruckt geprüft. Nach dem Probedruck stellst du sie ein.

Grenzen: keine modellierten Gewinde (nur Kernlöcher und Einsatzlöcher), keine frei geformten Flächen, keine Schriftarten (nur die 5×7-Pixelschrift). Ein Vieleck darf sich nicht selbst schneiden. Maße über 256 mm werden abgelehnt.

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

## Ersatzteile

Über die Kachel **Ersatzteile** entstehen einzelne Gebrauchsstücke, ohne Schublade. Acht Formen:

| Teil | Wofür |
|---|---|
| Kabelclip | ein oder mehrere Kabel, mit Schraubenlasche oder nur zum Kleben |
| Distanzhülse | Abstand um eine Schraube |
| Unterlegscheibe | flache Scheibe unter einem Schraubenkopf |
| Wandhaken | kleiner Haken mit Schraubenloch |
| Möbelfuß | runder Gleiter mit Sackloch |
| Drehknopf | für eine runde oder abgeflachte Welle |
| Stopfen | verschließt ein rundes Loch, Kragen liegt auf |
| Winkel | L-Verbindung mit einem Loch je Schenkel |

Ein Teil antippen legt es an. Die Maße stehen daneben, mit sinnvollen Grenzen. Zu dünne Wände (unter 1,2 mm bei einer 0,4-mm-Düse) und Teile über 256 mm werden auf Deutsch abgelehnt, der Knopf **Teil berechnen** bleibt dann aus. Unter den Feldern steht, wie das Teil auf das Druckbett gehört.

Solange noch nicht gerechnet wurde, ist die 3D-Ansicht eine **vereinfachte Vorschau**. Nach dem Berechnen kommt die Ansicht aus der STL-Datei, und grün wird es nur, wenn Datei, geschlossenes Netz und gültiger Körper stimmen. **Speichern** schreibt dasselbe Projektformat `.cadstudio.json`. Mehrere Ersatzteile können in einer Datei liegen.

Das Spiel am Stopfen (Vorgabe 0,3 mm) und die Passung der Bohrungen sind nicht an einem gedruckten Teil geprüft.

## Kabelmanagement

Über die Kachel **Kabelmanagement** entsteht ein Satz zusammengehöriger Teile, ohne Schublade. Alle Teile eines Satzes teilen sich dasselbe Profil: Innenbreite, Innenhöhe, Wandstärke, Spiel und Einstecktiefe. Die Vorgabe für das Spiel ist 0,20 mm. Das ist die Lücke im Modell. Ob sie gedruckt passt, ist nicht geprüft.

| Teil | Wofür |
|---|---|
| Kabelkanal | gerades Stück, Buchse am Anfang, Stecker am Ende. Länger als das Bett wird er in Stücke geteilt. Optional mit aufsteckbarem Deckel. |
| 90°-Ecke | Winkel mit derselben Buchse und demselben Stecker |
| Endkappe | schließt wahlweise das Stecker- oder das Buchsen-Ende |
| Wandhalter | Schelle um den Kanal, Lasche mit Schraubenloch |
| Kabelauslass | kurzes Stück mit einem Loch im Boden |

Ein Teil antippen fügt es mit dem Profil des gerade gewählten Teils hinzu. **Dieses Profil auf alle Teile übertragen** gleicht die anderen an. Weicht ein Teil ab, steht auf Deutsch, welches Maß nicht zusammenpasst, und **Teile berechnen** bleibt aus. Zu dünne Wände (unter 1,2 mm, und nur in 0,4-mm-Schritten) und Stücke über 256 mm werden ebenfalls abgelehnt.

Unter den Feldern steht, wie das Teil auf das Druckbett gehört: Kanäle und Ecken mit der Öffnung nach oben, Deckel und Lasche flach. Die Skizze und die 3D-Ansicht vor dem Berechnen sind vereinfacht und so beschriftet. Nach dem Berechnen kommt die Ansicht aus der STL-Datei. Grün wird es nur, wenn Datei, geschlossenes Netz und gültiger Körper stimmen. STL und FCStd lassen sich danach öffnen. **Speichern** schreibt dasselbe Projektformat `.cadstudio.json`.

## Elektronikgehäuse

Über die Kachel **Elektronikgehäuse** entsteht ein zweiteiliges Gehäuse. Du gibst den **Innenraum** ein, nicht das Außenmaß. Wand, Boden und Deckel sind mindestens 1,2 mm dick und ein Vielfaches von 0,4 mm. Die Ecken können gerundet sein. Das Spiel zum Deckel ist standardmäßig 0,20 mm. Das ist die Lücke im Modell. Ob sie gedruckt passt, ist nicht geprüft.

**Schraubdeckel:** vier Säulen in den Ecken, Kernloch 2,5 mm für eine M3-Blechschraube oder 2,0 mm für M2,5. Der Deckel hat die passenden Durchgangslöcher, auf Wunsch mit Senkung. **Schiebedeckel:** zwei Schienen innen, der Deckel wird von vorn eingeschoben.

**Platine:** eine Vorlage setzt Größe und Lochbild. Die Zahlen sind Nennwerte aus den Zeichnungen, kein vermessenes Brett.

- Raspberry Pi 4 und Raspberry Pi 5: 85 × 56 mm, vier Bohrungen Ø 2,7 mm im Raster 58 × 49 mm, 3,5 mm vom linken Rand und von beiden Längskanten. Quelle: Raspberry Pi Ltd, Mechanical Drawing der Pi 4 (RP-008343-DS) und die Mechanical Drawing der Pi 5.
- Arduino Uno R3 (A000066): 68,58 × 53,34 mm, vier Bohrungen Ø 3,2 mm, kein Rechteck. Ursprung an der USB-Kante unten links: (13,97 / 2,54), (15,24 / 50,80), (66,04 / 7,62), (66,04 / 35,56) mm. Quelle: Arduino-Datenblatt A000066, Abschnitt „Board Outline & Mounting Holes“, und die UNO-R3-Referenz.
- Eigenes Rechteck: vier Löcher, in der Platine zentriert, Abstand frei wählbar.

Die Stützen stehen unter diesen Löchern. Ein M2,5- oder M3-Kernloch oder ein Nennloch für ein Einpressgewinde (3,2 mm bzw. 4,0 mm, typische Herstellerangabe, nicht geprüft). Passt die Platine nicht in den Innenraum oder trifft eine Stütze eine Schraubensäule, bleibt der Export aus.

**Öffnungen:** Rechteck oder Rund auf vorne, hinten, links, rechts oder im Boden. Position ist die Mitte entlang der Wand, die zweite Zahl die Höhe von außen unten (beim Boden die Tiefe). Lüftungsschlitze und zwei Wandlaschen hinten lassen sich dazuschalten. Eine Öffnung an einer Schraubensäule oder durch den Rand wird abgelehnt.

Drucken: Gehäuse mit der Öffnung nach oben, Deckel flach. Die Vorschau vor dem Berechnen ist vereinfacht und so beschriftet. Danach kommt die Ansicht aus der STL. Grün wird es nur, wenn Datei, geschlossenes Netz und gültiger Körper für Gehäuse und Deckel stimmen. **Speichern** nutzt dasselbe Projektformat.

## Was die Dateien nicht versprechen

- Die Passung 1,0 mm und 0,20 mm ist nicht an einem gedruckten Teil geprüft.
- Die Gewichtsangabe ist aus dem CAD-Volumen geschätzt.
- Lebensmittel, Spülmaschine und Wärme sind nicht geprüft.
- Die Ursprungsplatten ohne den Zusatz QS1 sind fehlerhaft und werden nicht verwendet.

## Löcher und Formen intelligent positionieren

Im Zeichenblatt eine Form wählen. Im Bereich **Positionieren** stehen Bauteilmitte, getrennte Zentrierung, Randabstände und **Mittelpunkt übernehmen** bereit. Kreise können mit frei wählbarem Durchmesser und Materialmodus konzentrisch ergänzt werden. Mit Umschalt-Klick mindestens drei Formen wählen, um sie gleichmäßig zu verteilen. Bindungen folgen Größenänderungen; manuelle Positionseingaben lösen die geänderte Achse. Details und Grenzen: [POSITIONIERUNG.md](POSITIONIERUNG.md).
