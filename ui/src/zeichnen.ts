/** Datenmodell und Rechenlogik für eigene, gezeichnete Teile. Die Prüfung der Formen bleibt beim Sidecar. */

export type Punkt = [number, number];

export type Form =
  | { typ: "rechteck"; x: number; y: number; b: number; t: number; loch: boolean; radius?: number; z_mm?: number; h_mm?: number }
  | { typ: "kreis"; x: number; y: number; r: number; loch: boolean; z_mm?: number; h_mm?: number }
  | { typ: "polygon"; punkte: Punkt[]; loch: boolean; z_mm?: number; h_mm?: number };

export type KantenArt = "keine" | "fase" | "rund";

export interface Eigenteil {
  id: string;
  name: string;
  hoehe_mm: number;
  boden_mm: number;
  anzahl: number;
  formen: Form[];
  notiz: string;
  platziert: boolean;
  x_mm: number;
  y_mm: number;
  drehung: number;
  kante_oben_art: KantenArt;
  kante_oben_mm: number;
  kante_unten_mm: number;
}

export const MIN_MM = 0.4;

export function runden(wert: number, raster: number): number {
  if (!(raster > 0)) return wert;
  return Math.round(wert / raster) * raster;
}

export function bereinigen(wert: number): number {
  return Math.round(wert * 1000) / 1000;
}

export function neueTeilId(vorhanden: Eigenteil[]): string {
  const belegt = new Set(vorhanden.map((t) => t.id));
  let n = 1;
  while (belegt.has(`E${n}`)) n += 1;
  return `E${n}`;
}

export function neuesTeil(vorhanden: Eigenteil[]): Eigenteil {
  const id = neueTeilId(vorhanden);
  return { id, name: `Eigenes Teil ${id.slice(1)}`, hoehe_mm: 10, boden_mm: 0, anzahl: 1, formen: [], notiz: "", platziert: false, x_mm: 0, y_mm: 0, drehung: 0, kante_oben_art: "keine", kante_oben_mm: 0, kante_unten_mm: 0 };
}

export function formBox(form: Form): [number, number, number, number] {
  if (form.typ === "rechteck") return [form.x, form.y, form.x + form.b, form.y + form.t];
  if (form.typ === "kreis") return [form.x - form.r, form.y - form.r, form.x + form.r, form.y + form.r];
  const xs = form.punkte.map((p) => p[0]);
  const ys = form.punkte.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** Außenmaß der Formen, die Material hinzufügen (wie im Sidecar). */
/** Starthöhe und Höhe einer Material-Form: ohne Angabe von 0 bis zur Teilhöhe, mit z_mm bis zur Teilhöhe. */
export function formHoehen(form: Form, teilHoehe: number): { z: number; h: number } {
  const z = form.z_mm ?? 0;
  const h = form.h_mm ?? teilHoehe - z;
  return { z, h };
}

/** Höchste Oberkante aller Formen, die Material hinzufügen (sonst die Standardhöhe). */
export function gesamthoehe(teil: Pick<Eigenteil, "formen" | "hoehe_mm">): number {
  let hoechste = 0;
  for (const f of teil.formen) {
    if (f.loch) continue;
    const { z, h } = formHoehen(f, teil.hoehe_mm);
    hoechste = Math.max(hoechste, z + h);
  }
  return hoechste > 0 ? bereinigen(hoechste) : teil.hoehe_mm;
}

export function aussenmass(formen: Form[]): { breite: number; tiefe: number } | null {
  const hinzu = formen.filter((f) => !f.loch);
  if (!hinzu.length) return null;
  const boxen = hinzu.map(formBox);
  const x0 = Math.min(...boxen.map((b) => b[0]));
  const y0 = Math.min(...boxen.map((b) => b[1]));
  const x1 = Math.max(...boxen.map((b) => b[2]));
  const y1 = Math.max(...boxen.map((b) => b[3]));
  return { breite: bereinigen(x1 - x0), tiefe: bereinigen(y1 - y0) };
}

export function verschieben(form: Form, dx: number, dy: number): Form {
  if (form.typ === "polygon") {
    return { ...form, punkte: form.punkte.map(([x, y]) => [bereinigen(x + dx), bereinigen(y + dy)] as Punkt) };
  }
  return { ...form, x: bereinigen(form.x + dx), y: bereinigen(form.y + dy) };
}

export function rechteckAus(a: Punkt, b: Punkt, loch: boolean): Form | null {
  const x = Math.min(a[0], b[0]);
  const y = Math.min(a[1], b[1]);
  const breite = Math.abs(a[0] - b[0]);
  const tiefe = Math.abs(a[1] - b[1]);
  if (breite < MIN_MM || tiefe < MIN_MM) return null;
  return { typ: "rechteck", x: bereinigen(x), y: bereinigen(y), b: bereinigen(breite), t: bereinigen(tiefe), loch };
}

export function kreisAus(mitte: Punkt, rand: Punkt, loch: boolean): Form | null {
  const r = Math.hypot(rand[0] - mitte[0], rand[1] - mitte[1]);
  if (r * 2 < MIN_MM) return null;
  return { typ: "kreis", x: bereinigen(mitte[0]), y: bereinigen(mitte[1]), r: bereinigen(r), loch };
}

export function polygonAus(punkte: Punkt[], loch: boolean): Form | null {
  if (punkte.length < 3) return null;
  return { typ: "polygon", punkte: punkte.map(([x, y]) => [bereinigen(x), bereinigen(y)] as Punkt), loch };
}

/** Wie der Sidecar: ein Eigenteil aus dem Projekt wird mit Standardwerten ergänzt. */
export function teilVonServer(roh: Record<string, unknown>): Eigenteil {
  return {
    id: String(roh.id),
    name: String(roh.name || roh.id),
    hoehe_mm: Number(roh.hoehe_mm ?? 10),
    boden_mm: Number(roh.boden_mm ?? 0),
    anzahl: Number(roh.anzahl ?? 1),
    formen: ((roh.formen as Form[]) || []).map((f) => ({ ...f })),
    notiz: String(roh.notiz || ""),
    platziert: Boolean(roh.platziert),
    x_mm: Number(roh.x_mm ?? 0),
    y_mm: Number(roh.y_mm ?? 0),
    drehung: Number(roh.drehung ?? 0),
    kante_oben_art: (["fase", "rund"].includes(String(roh.kante_oben_art)) ? roh.kante_oben_art : "keine") as KantenArt,
    kante_oben_mm: Number(roh.kante_oben_mm ?? 0),
    kante_unten_mm: Number(roh.kante_unten_mm ?? 0),
  };
}

/** Belegte Fläche in der Schublade nach Drehung, in Millimetern (x, y, Breite, Tiefe). */
export function rechteckMm(teil: Eigenteil): { x: number; y: number; b: number; t: number } | null {
  const mass = aussenmass(teil.formen);
  if (!mass) return null;
  const gedreht = teil.drehung % 180 === 90;
  return { x: teil.x_mm, y: teil.y_mm, b: gedreht ? mass.tiefe : mass.breite, t: gedreht ? mass.breite : mass.tiefe };
}

export interface Massangabe {
  text: string;
  x: number;
  y: number;
  /** Maßlinie in Weltkoordinaten (x1, y1, x2, y2), falls vorhanden */
  linie?: [number, number, number, number];
}

/** Zahl für die Anzeige: deutsch, höchstens eine Nachkommastelle, ohne ",0". */
export function zahlText(wert: number): string {
  const rund = Math.round(wert * 10) / 10;
  return String(rund).replace(".", ",");
}

/**
 * Maßangaben einer Form in Weltkoordinaten (mm, y nach oben).
 * abstand: Abstand der Maßlinie von der Kante; mitKanten: Kantenlängen eines Vielecks.
 */
export function massangaben(form: Form, abstand: number, mitKanten = false): Massangabe[] {
  const liste = formMasse(form, abstand, mitKanten);
  if (form.z_mm !== undefined || form.h_mm !== undefined) {
    const [x0, y0, x1, y1] = formBox(form);
    const text = [form.z_mm !== undefined ? `z ${zahlText(form.z_mm)}` : "", form.h_mm !== undefined ? `h ${zahlText(form.h_mm)}` : ""].filter(Boolean).join(" ");
    liste.push({ text, x: (x0 + x1) / 2, y: (y0 + y1) / 2 - abstand });
  }
  return liste;
}

function formMasse(form: Form, abstand: number, mitKanten: boolean): Massangabe[] {
  if (form.typ === "rechteck") {
    const oben = form.y + form.t + abstand;
    const rechts = form.x + form.b + abstand;
    return [
      { text: zahlText(form.b), x: form.x + form.b / 2, y: oben, linie: [form.x, oben - abstand / 2, form.x + form.b, oben - abstand / 2] },
      { text: zahlText(form.t), x: rechts, y: form.y + form.t / 2, linie: [rechts - abstand / 2, form.y, rechts - abstand / 2, form.y + form.t] },
    ];
  }
  if (form.typ === "kreis") {
    return [{ text: `Ø ${zahlText(form.r * 2)}`, x: form.x, y: form.y }];
  }
  if (!mitKanten) {
    const [x0, y0, x1, y1] = formBox(form);
    return [{ text: `${zahlText(x1 - x0)} × ${zahlText(y1 - y0)}`, x: (x0 + x1) / 2, y: y1 + abstand }];
  }
  return form.punkte.map((p, i) => {
    const q = form.punkte[(i + 1) % form.punkte.length];
    return { text: zahlText(Math.hypot(q[0] - p[0], q[1] - p[1])), x: (p[0] + q[0]) / 2, y: (p[1] + q[1]) / 2 };
  });
}

export interface Vorlage {
  id: string;
  name: string;
  text: string;
  erzeuge: () => Partial<Eigenteil>;
}

const rechteck = (x: number, y: number, b: number, t: number, extra: Partial<Extract<Form, { typ: "rechteck" }>> = {}): Form => ({
  typ: "rechteck", x, y, b, t, loch: false, ...extra,
});
const bohrung = (x: number, y: number, r: number, extra: Partial<Extract<Form, { typ: "kreis" }>> = {}): Form => ({
  typ: "kreis", x, y, r, loch: true, ...extra,
});

/** Startpunkte zum Weiterbearbeiten; alle Maße in mm. */
export const VORLAGEN: Vorlage[] = [
  {
    id: "platte",
    name: "Platte mit Bohrungen",
    text: "60 × 40 × 4 mm, runde Ecken, vier Löcher Ø 4",
    erzeuge: () => ({
      name: "Platte mit Bohrungen",
      hoehe_mm: 4,
      formen: [rechteck(0, 0, 60, 40, { radius: 4 }), bohrung(8, 8, 2), bohrung(52, 8, 2), bohrung(8, 32, 2), bohrung(52, 32, 2)],
    }),
  },
  {
    id: "winkel",
    name: "Winkelhalter",
    text: "Grundplatte mit Wand, 50 × 30 mm, 30 mm hoch",
    erzeuge: () => ({
      name: "Winkelhalter",
      hoehe_mm: 4,
      formen: [rechteck(0, 0, 50, 30), rechteck(0, 26, 50, 4, { z_mm: 0, h_mm: 30 }), bohrung(25, 12, 2.5)],
    }),
  },
  {
    id: "stufe",
    name: "Stufenblock",
    text: "Sockel 60 × 40 × 6 mm mit Aufsatz bis 12 mm",
    erzeuge: () => ({
      name: "Stufenblock",
      hoehe_mm: 6,
      formen: [rechteck(0, 0, 60, 40), rechteck(10, 5, 40, 30, { z_mm: 6, h_mm: 6 })],
    }),
  },
  {
    id: "mulde",
    name: "Schale mit Mulde",
    text: "50 × 50 × 20 mm, Mulde mit 2 mm Boden, Rundung oben",
    erzeuge: () => ({
      name: "Schale",
      hoehe_mm: 20,
      boden_mm: 2,
      kante_oben_art: "rund" as KantenArt,
      kante_oben_mm: 1,
      formen: [rechteck(0, 0, 50, 50, { radius: 6 }), rechteck(3, 3, 44, 44, { radius: 4, loch: true })],
    }),
  },
  {
    id: "stabhalter",
    name: "Stabhalter",
    text: "40 × 20 × 25 mm mit zwei Bohrungen Ø 8, Fase oben",
    erzeuge: () => ({
      name: "Stabhalter",
      hoehe_mm: 25,
      kante_oben_art: "fase" as KantenArt,
      kante_oben_mm: 1,
      formen: [rechteck(0, 0, 40, 20), bohrung(10, 10, 4), bohrung(30, 10, 4)],
    }),
  },
];

/** Farbanteil 0..1 einer Form nach ihrer Oberkante im Verhältnis zur Gesamthöhe (für die Vorschau). */
export function hoehenanteil(form: Form, teil: Pick<Eigenteil, "formen" | "hoehe_mm">): number {
  const gesamt = gesamthoehe(teil);
  if (!(gesamt > 0)) return 1;
  const { z, h } = formHoehen(form, teil.hoehe_mm);
  return Math.max(0, Math.min(1, (z + h) / gesamt));
}
