/**
 * Schraubenlöcher für gedruckte Teile: Durchgangsloch, Kernloch zum Gewindeschneiden und Loch für Gewindeeinsätze,
 * dazu Senk- und Zylinderkopf und Schraubdome. Alle Maße in mm. Die Normwerte sind Nennwerte; gedruckte Löcher fallen
 * meist etwas kleiner aus, deshalb gibt es einen einstellbaren Zuschlag. Nichts davon ist gedruckt geprüft.
 */

import { bereinigen, type Form } from "./zeichnen";

export type Schraube = "M2" | "M2.5" | "M3" | "M4" | "M5";
export type Zweck = "durchgang" | "kern" | "einsatz";
export type Kopf = "ohne" | "senk" | "zylinder";

export interface Schraubenmasse {
  nenn: number;
  /** Durchgangsloch mittel nach ISO 273 */
  durchgang: number;
  /** Kernlochdurchmesser für metrisches Regelgewinde (Gewindebohrer) */
  kern: number;
  /** typischer Außendurchmesser eines Messing-Gewindeeinsatzes zum Einschmelzen (Datenblatt prüfen) */
  einsatzAussen: number;
  /** Senkkopf 90° (ISO 10642), Kopfdurchmesser */
  senkKopf: number;
  /** Zylinderkopf (ISO 4762): Kopfdurchmesser und Kopfhöhe */
  zylKopf: number;
  zylHoehe: number;
}

export const SCHRAUBEN: Record<Schraube, Schraubenmasse> = {
  M2: { nenn: 2, durchgang: 2.4, kern: 1.6, einsatzAussen: 3.2, senkKopf: 4.4, zylKopf: 3.8, zylHoehe: 2 },
  "M2.5": { nenn: 2.5, durchgang: 2.9, kern: 2.05, einsatzAussen: 3.6, senkKopf: 5.5, zylKopf: 4.5, zylHoehe: 2.5 },
  M3: { nenn: 3, durchgang: 3.4, kern: 2.5, einsatzAussen: 4.6, senkKopf: 6.7, zylKopf: 5.5, zylHoehe: 3 },
  M4: { nenn: 4, durchgang: 4.5, kern: 3.3, einsatzAussen: 5.6, senkKopf: 9, zylKopf: 7, zylHoehe: 4 },
  M5: { nenn: 5, durchgang: 5.5, kern: 4.2, einsatzAussen: 6.4, senkKopf: 11.2, zylKopf: 8.5, zylHoehe: 5 },
};

export const SCHRAUBEN_NAMEN = Object.keys(SCHRAUBEN) as Schraube[];

export interface Einstellungen {
  /** Zuschlag auf Durchgangs- und Kernloch, weil gedruckte Löcher kleiner werden */
  zuschlag: number;
  /** Abzug vom Außendurchmesser des Einsatzes (Presssitz im Kunststoff) */
  einsatzAbzug: number;
  /** Spiel am Schraubenkopf (Senkung und Gegenbohrung) */
  kopfSpiel: number;
}

export const STANDARD: Einstellungen = { zuschlag: 0.1, einsatzAbzug: 0.4, kopfSpiel: 0.3 };

/** Lochdurchmesser für Größe und Zweck. */
export function lochDurchmesser(groesse: Schraube, zweck: Zweck, e: Einstellungen = STANDARD): number {
  const m = SCHRAUBEN[groesse];
  if (zweck === "durchgang") return bereinigen(m.durchgang + e.zuschlag);
  if (zweck === "kern") return bereinigen(m.kern + e.zuschlag);
  return bereinigen(m.einsatzAussen - e.einsatzAbzug);
}

export interface KopfFelder {
  senk_art: "keine" | "senkung" | "gegenbohrung";
  senk_d_mm?: number;
  senk_t_mm?: number;
  senk_seite?: "oben";
}

/** Felder für Senkung oder Gegenbohrung zum gewählten Kopf (nur sinnvoll beim Durchgangsloch). */
export function kopfFelder(groesse: Schraube, kopf: Kopf, e: Einstellungen = STANDARD): KopfFelder {
  const m = SCHRAUBEN[groesse];
  if (kopf === "senk") return { senk_art: "senkung", senk_d_mm: bereinigen(m.senkKopf + e.kopfSpiel), senk_seite: "oben" };
  if (kopf === "zylinder") {
    return { senk_art: "gegenbohrung", senk_d_mm: bereinigen(m.zylKopf + e.kopfSpiel), senk_t_mm: bereinigen(m.zylHoehe + e.kopfSpiel), senk_seite: "oben" };
  }
  return { senk_art: "keine" };
}

export interface DomEingabe {
  x: number;
  y: number;
  groesse: Schraube;
  zweck: Zweck;
  /** Höhe des Doms über der Fußhöhe */
  hoehe: number;
  /** Fußhöhe: Oberseite der Platte, auf der der Dom steht */
  fuss: number;
  /** Wandstärke um das Loch */
  wand: number;
  /** Tiefe des Lochs von oben; leer = bis zum Fuß */
  tiefe?: number;
}

/** Schraubdom: Zylinder mit Loch. Das Loch beginnt in der Fußhöhe (die Platte darunter bleibt heil). */
export function schraubdom(d: DomEingabe, e: Einstellungen = STANDARD): Form[] {
  const loch = lochDurchmesser(d.groesse, d.zweck, e);
  const aussen = bereinigen(loch + 2 * d.wand);
  const tiefe = Math.min(d.tiefe ?? d.hoehe, d.hoehe);
  const start = bereinigen(d.fuss + d.hoehe - tiefe);
  return [
    { typ: "kreis", x: d.x, y: d.y, r: bereinigen(aussen / 2), loch: false, z_mm: d.fuss, h_mm: d.hoehe },
    { typ: "kreis", x: d.x, y: d.y, r: bereinigen(loch / 2), loch: true, z_mm: start },
  ];
}

/** Hinweis zum Zweck, für die Oberfläche. */
export function zweckText(zweck: Zweck): string {
  if (zweck === "durchgang") return "Durchgangsloch: die Schraube geht frei durch.";
  if (zweck === "kern") return "Kernloch: die Schraube schneidet das Gewinde selbst (Blech- oder Gewindeformschraube) oder wird nachgeschnitten.";
  return "Gewindeeinsatz zum Einschmelzen: Außendurchmesser des Einsatzes minus Abzug. Datenblatt des Einsatzes prüfen (Außendurchmesser, Länge).";
}
