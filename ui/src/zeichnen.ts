/** Datenmodell und Rechenlogik für eigene, gezeichnete Teile. Die Prüfung der Formen bleibt beim Sidecar. */

export type Punkt = [number, number];

export type Form =
  | { typ: "rechteck"; x: number; y: number; b: number; t: number; loch: boolean }
  | { typ: "kreis"; x: number; y: number; r: number; loch: boolean }
  | { typ: "polygon"; punkte: Punkt[]; loch: boolean };

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
  return { id, name: `Eigenes Teil ${id.slice(1)}`, hoehe_mm: 10, boden_mm: 0, anzahl: 1, formen: [], notiz: "", platziert: false, x_mm: 0, y_mm: 0, drehung: 0 };
}

export function formBox(form: Form): [number, number, number, number] {
  if (form.typ === "rechteck") return [form.x, form.y, form.x + form.b, form.y + form.t];
  if (form.typ === "kreis") return [form.x - form.r, form.y - form.r, form.x + form.r, form.y + form.r];
  const xs = form.punkte.map((p) => p[0]);
  const ys = form.punkte.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/** Außenmaß der Formen, die Material hinzufügen (wie im Sidecar). */
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
  };
}

/** Belegte Fläche in der Schublade nach Drehung, in Millimetern (x, y, Breite, Tiefe). */
export function rechteckMm(teil: Eigenteil): { x: number; y: number; b: number; t: number } | null {
  const mass = aussenmass(teil.formen);
  if (!mass) return null;
  const gedreht = teil.drehung % 180 === 90;
  return { x: teil.x_mm, y: teil.y_mm, b: gedreht ? mass.tiefe : mass.breite, t: gedreht ? mass.breite : mass.tiefe };
}
