/** Datenmodell und Rechenlogik für eigene, gezeichnete Teile. Die Prüfung der Formen bleibt beim Sidecar. */

export type Punkt = [number, number];

export type KantenArt = "keine" | "fase" | "rund";

/** Optionen, die jede Form haben kann. */
export interface FormOptionen {
  z_mm?: number;
  h_mm?: number;
  /** Fase oder Rundung am Oberrand der Form bzw. am Lochrand */
  kante_art?: KantenArt;
  kante_mm?: number;
  /** Material: Verjüngung nach oben; Loch: Aufweitung nach oben (Senkung) */
  schraege_mm?: number;
}

export type Form =
  | ({ typ: "rechteck"; x: number; y: number; b: number; t: number; loch: boolean; radius?: number; keil_mm?: number; winkel?: number } & FormOptionen)
  | ({ typ: "kreis"; x: number; y: number; r: number; loch: boolean } & FormOptionen)
  | ({ typ: "polygon"; punkte: Punkt[]; loch: boolean } & FormOptionen);

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
  // "+ 0" macht aus -0 eine 0
  return Math.round(wert * 1000) / 1000 + 0;
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

/** Mitte eines gedrehten Rechtecks (die Drehung geschieht um diese Mitte). */
function rechteckMitte(form: { x: number; y: number; b: number; t: number }): [number, number] {
  return [form.x + form.b / 2, form.y + form.t / 2];
}

export function formBox(form: Form): [number, number, number, number] {
  if (form.typ === "rechteck") {
    const winkel = form.winkel ?? 0;
    if (winkel % 180 === 0) return [form.x, form.y, form.x + form.b, form.y + form.t];
    const w = (winkel * Math.PI) / 180;
    const c = Math.abs(Math.cos(w));
    const s = Math.abs(Math.sin(w));
    const r = form.radius ?? 0;
    const hx = (form.b / 2 - r) * c + (form.t / 2 - r) * s + r;
    const hy = (form.b / 2 - r) * s + (form.t / 2 - r) * c + r;
    const [mx, my] = rechteckMitte(form);
    return [bereinigen(mx - hx), bereinigen(my - hy), bereinigen(mx + hx), bereinigen(my + hy)];
  }
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

/** Höchster Punkt einer Material-Form; bei einem Keil die hintere, höhere Kante. */
export function formOberkante(form: Form, teilHoehe: number): number {
  const { z, h } = formHoehen(form, teilHoehe);
  const keil = form.typ === "rechteck" ? form.keil_mm ?? 0 : 0;
  return z + h + Math.max(0, keil);
}

/** Höchste Oberkante aller Formen, die Material hinzufügen (sonst die Standardhöhe). */
export function gesamthoehe(teil: Pick<Eigenteil, "formen" | "hoehe_mm">): number {
  let hoechste = 0;
  for (const f of teil.formen) {
    if (f.loch) continue;
    hoechste = Math.max(hoechste, formOberkante(f, teil.hoehe_mm));
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
  /** Welches Maß der Form diese Angabe ist; nur dann lässt sie sich per Eingabe ändern */
  feld?: MassFeld;
}

export type MassFeld = "b" | "t" | "d";

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
  const teile = [
    form.z_mm !== undefined ? `z ${zahlText(form.z_mm)}` : "",
    form.h_mm !== undefined ? `h ${zahlText(form.h_mm)}` : "",
    form.typ === "rechteck" && form.keil_mm ? `Keil ${zahlText(form.keil_mm)}` : "",
    form.schraege_mm ? `Schräge ${zahlText(form.schraege_mm)}` : "",
    form.kante_art && form.kante_art !== "keine" && form.kante_mm ? `${form.kante_art === "fase" ? "Fase" : "Rundung"} ${zahlText(form.kante_mm)}` : "",
  ].filter(Boolean);
  if (teile.length) {
    const [x0, y0, x1, y1] = formBox(form);
    liste.push({ text: teile.join(" · "), x: (x0 + x1) / 2, y: (y0 + y1) / 2 - abstand });
  }
  return liste;
}

function formMasse(form: Form, abstand: number, mitKanten: boolean): Massangabe[] {
  if (form.typ === "rechteck" && (form.winkel ?? 0) % 180 !== 0) {
    const [, , , y1] = formBox(form);
    const [mx] = rechteckMitte(form);
    return [{ text: `${zahlText(form.b)} × ${zahlText(form.t)} ∠ ${zahlText(form.winkel ?? 0)}°`, x: mx, y: y1 + abstand }];
  }
  if (form.typ === "rechteck") {
    const oben = form.y + form.t + abstand;
    const rechts = form.x + form.b + abstand;
    return [
      { text: zahlText(form.b), x: form.x + form.b / 2, y: oben, feld: "b", linie: [form.x, oben - abstand / 2, form.x + form.b, oben - abstand / 2] },
      { text: zahlText(form.t), x: rechts, y: form.y + form.t / 2, feld: "t", linie: [rechts - abstand / 2, form.y, rechts - abstand / 2, form.y + form.t] },
    ];
  }
  if (form.typ === "kreis") {
    return [{ text: `Ø ${zahlText(form.r * 2)}`, x: form.x, y: form.y, feld: "d" }];
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
    id: "rampe",
    name: "Rampe (Keil)",
    text: "Platte 60 × 40 mit Keil: vorn 3 mm, hinten 13 mm hoch",
    erzeuge: () => ({
      name: "Rampe",
      hoehe_mm: 3,
      formen: [rechteck(0, 0, 60, 40, { keil_mm: 10 })],
    }),
  },
  {
    id: "senkung",
    name: "Platte mit Senkungen",
    text: "60 × 30 × 4 mm, zwei konische Senkungen für Schrauben",
    erzeuge: () => ({
      name: "Platte mit Senkungen",
      hoehe_mm: 4,
      formen: [rechteck(0, 0, 60, 30, { radius: 3 }), bohrung(12, 15, 1.75, { schraege_mm: 1.75 }), bohrung(48, 15, 1.75, { schraege_mm: 1.75 })],
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
  return Math.max(0, Math.min(1, formOberkante(form, teil.hoehe_mm) / gesamt));
}

// ---------------------------------------------------------------- Einrasten und Ausrichten

export interface FangErgebnis {
  punkt: Punkt;
  /** x- bzw. y-Linie, an der eingerastet wurde (für die Anzeige der Hilfslinien) */
  fangX?: number;
  fangY?: number;
}

/** Punkte einer Form, an denen andere einrasten: Ecken, Kantenmitten, Mitte, Vieleck-Ecken. */
export function fangpunkteVon(form: Form): Punkt[] {
  const [x0, y0, x1, y1] = formBox(form);
  const xm = (x0 + x1) / 2;
  const ym = (y0 + y1) / 2;
  const punkte: Punkt[] = [
    [x0, y0], [xm, y0], [x1, y0],
    [x0, ym], [xm, ym], [x1, ym],
    [x0, y1], [xm, y1], [x1, y1],
  ];
  if (form.typ === "polygon") punkte.push(...form.punkte.map((p) => [p[0], p[1]] as Punkt));
  if (form.typ === "rechteck" && (form.winkel ?? 0) % 180 !== 0) {
    const [mx, my] = rechteckMitte(form);
    for (const [dx, dy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      punkte.push(drehePunkt([mx + (dx * form.b) / 2, my + (dy * form.t) / 2], [mx, my], form.winkel ?? 0));
    }
  }
  return punkte;
}

export function fangpunkte(formen: Form[], ausser: number | null = null): Punkt[] {
  return formen.flatMap((f, i) => (i === ausser ? [] : fangpunkteVon(f)));
}

/** Rastet einen Punkt je Achse an der nächsten Fluchtlinie der Fangpunkte ein (innerhalb der Schwelle). */
export function einrasten(p: Punkt, punkte: Punkt[], schwelle: number): FangErgebnis {
  let bestX: number | undefined;
  let bestY: number | undefined;
  for (const [fx, fy] of punkte) {
    if (Math.abs(fx - p[0]) <= schwelle && (bestX === undefined || Math.abs(fx - p[0]) < Math.abs(bestX - p[0]))) bestX = fx;
    if (Math.abs(fy - p[1]) <= schwelle && (bestY === undefined || Math.abs(fy - p[1]) < Math.abs(bestY - p[1]))) bestY = fy;
  }
  return { punkt: [bestX ?? p[0], bestY ?? p[1]], fangX: bestX, fangY: bestY };
}

/**
 * Verschiebt eine Form um (dx, dy) und rastet dabei ihre Kanten und Mitte an Kanten und Mitten
 * der anderen Formen ein. Liefert die korrigierte Verschiebung.
 */
export function verschiebenMitFang(form: Form, dx: number, dy: number, andere: Form[], schwelle: number): { dx: number; dy: number; fangX?: number; fangY?: number } {
  const [x0, y0, x1, y1] = formBox(form);
  const meineX = [x0 + dx, (x0 + x1) / 2 + dx, x1 + dx];
  const meineY = [y0 + dy, (y0 + y1) / 2 + dy, y1 + dy];
  const ziele = andere.flatMap(fangpunkteVon);
  let besteX: { delta: number; linie: number } | undefined;
  let besteY: { delta: number; linie: number } | undefined;
  for (const [fx, fy] of ziele) {
    for (const mx of meineX) {
      const d = fx - mx;
      if (Math.abs(d) <= schwelle && (!besteX || Math.abs(d) < Math.abs(besteX.delta))) besteX = { delta: d, linie: fx };
    }
    for (const my of meineY) {
      const d = fy - my;
      if (Math.abs(d) <= schwelle && (!besteY || Math.abs(d) < Math.abs(besteY.delta))) besteY = { delta: d, linie: fy };
    }
  }
  return { dx: bereinigen(dx + (besteX?.delta ?? 0)), dy: bereinigen(dy + (besteY?.delta ?? 0)), fangX: besteX?.linie, fangY: besteY?.linie };
}

export type AusrichtModus = "mitte-x" | "mitte-y" | "links" | "rechts" | "unten" | "oben";

/** Bezugsrahmen: Außenmaß aller anderen Formen, die Material hinzufügen. */
export function bezugsrahmen(formen: Form[], ausser: number): [number, number, number, number] | null {
  const boxen = formen.filter((f, i) => i !== ausser && !f.loch).map(formBox);
  if (!boxen.length) return null;
  return [
    Math.min(...boxen.map((b) => b[0])),
    Math.min(...boxen.map((b) => b[1])),
    Math.max(...boxen.map((b) => b[2])),
    Math.max(...boxen.map((b) => b[3])),
  ];
}

/** Richtet eine Form am Bezugsrahmen aus. Gibt die Form unverändert zurück, wenn es keinen Rahmen gibt. */
export function ausrichten(form: Form, modus: AusrichtModus, rahmen: [number, number, number, number] | null): Form {
  if (!rahmen) return form;
  const [x0, y0, x1, y1] = formBox(form);
  const [rx0, ry0, rx1, ry1] = rahmen;
  switch (modus) {
    case "mitte-x": return verschieben(form, (rx0 + rx1) / 2 - (x0 + x1) / 2, 0);
    case "mitte-y": return verschieben(form, 0, (ry0 + ry1) / 2 - (y0 + y1) / 2);
    case "links": return verschieben(form, rx0 - x0, 0);
    case "rechts": return verschieben(form, rx1 - x1, 0);
    case "unten": return verschieben(form, 0, ry0 - y0);
    case "oben": return verschieben(form, 0, ry1 - y1);
  }
}

// ---------------------------------------------------------------- Muster und Spiegeln

/** Höchstzahl an Formen je Teil (wie im Sidecar). */
export const MAX_FORMEN = 200;

/** Kopie einer Form, um (dx, dy) verschoben. */
export function kopieren(form: Form, dx: number, dy: number): Form {
  return verschieben(form, dx, dy);
}

/** Gitter aus Spalten × Zeilen. Gibt nur die Kopien zurück, nicht das Original (Position 0/0). */
export function gitter(form: Form, spalten: number, zeilen: number, abstandX: number, abstandY: number): Form[] {
  const kopien: Form[] = [];
  for (let z = 0; z < Math.max(1, zeilen); z++) {
    for (let sp = 0; sp < Math.max(1, spalten); sp++) {
      if (sp === 0 && z === 0) continue;
      kopien.push(verschieben(form, bereinigen(sp * abstandX), bereinigen(z * abstandY)));
    }
  }
  return kopien;
}

/** Reihe: wie ein Gitter mit einer Zeile, in beliebiger Richtung. Anzahl zählt das Original mit. */
export function reihe(form: Form, anzahl: number, dx: number, dy: number): Form[] {
  const kopien: Form[] = [];
  for (let i = 1; i < Math.max(1, anzahl); i++) kopien.push(verschieben(form, bereinigen(i * dx), bereinigen(i * dy)));
  return kopien;
}

function drehePunkt(p: Punkt, mitte: Punkt, grad: number): Punkt {
  const w = (grad * Math.PI) / 180;
  const dx = p[0] - mitte[0];
  const dy = p[1] - mitte[1];
  return [bereinigen(mitte[0] + dx * Math.cos(w) - dy * Math.sin(w)), bereinigen(mitte[1] + dx * Math.sin(w) + dy * Math.cos(w))];
}

/** Ob sich die Form drehen lässt: Rechtecke bleiben achsparallel und sind ausgenommen. */
export function laesstSichDrehen(form: Form): boolean {
  return !(form.typ === "rechteck" && form.keil_mm);
}

/**
 * Kreismuster um eine Mitte. Anzahl zählt das Original mit. Bei 360° oder mehr verteilen sich die Formen
 * gleichmäßig auf den Vollkreis, sonst über den Bogen von der Ausgangslage bis zum Winkel (gegen den Uhrzeigersinn).
 * Gibt nur die Kopien zurück; Rechtecke ergeben eine leere Liste.
 */
export function kreismuster(form: Form, mitte: Punkt, anzahl: number, gesamtWinkel = 360): Form[] {
  if (!laesstSichDrehen(form) || anzahl < 2) return [];
  const schritt = gesamtWinkel >= 360 ? gesamtWinkel / anzahl : gesamtWinkel / (anzahl - 1);
  const kopien: Form[] = [];
  for (let i = 1; i < anzahl; i++) {
    const grad = i * schritt;
    if (form.typ === "kreis") {
      const [x, y] = drehePunkt([form.x, form.y], mitte, grad);
      kopien.push({ ...form, x, y });
    } else if (form.typ === "polygon") {
      kopien.push({ ...form, punkte: form.punkte.map((p) => drehePunkt(p, mitte, grad)) });
    } else {
      // Rechteck: Mitte auf den Kreis, Drehwinkel um denselben Betrag erhöhen
      const [cx, cy] = rechteckMitte(form);
      const [nx, ny] = drehePunkt([cx, cy], mitte, grad);
      kopien.push({ ...form, x: bereinigen(nx - form.b / 2), y: bereinigen(ny - form.t / 2), winkel: bereinigen(((form.winkel ?? 0) + grad) % 360) });
    }
  }
  return kopien;
}

/**
 * Spiegelt eine Form an einer senkrechten (achse "x": x = pos) oder waagrechten Achse (achse "y": y = pos).
 * Ein Keil läuft nach dem Spiegeln an der waagrechten Achse in die Gegenrichtung (vorn und hinten tauschen).
 */
export function spiegeln(form: Form, achse: "x" | "y", pos: number, teilHoehe: number): Form {
  const sp = (v: number) => bereinigen(2 * pos - v);
  if (form.typ === "kreis") {
    return achse === "x" ? { ...form, x: sp(form.x) } : { ...form, y: sp(form.y) };
  }
  if (form.typ === "polygon") {
    return { ...form, punkte: form.punkte.map(([x, y]) => (achse === "x" ? [sp(x), y] : [x, sp(y)]) as Punkt) };
  }
  if (form.winkel && form.winkel % 180 !== 0) {
    // Gedrehtes Rechteck: Mitte spiegeln, Drehwinkel ändert das Vorzeichen
    const [cx, cy] = rechteckMitte(form);
    const [nx, ny] = achse === "x" ? [sp(cx), cy] : [cx, sp(cy)];
    return { ...form, x: bereinigen(nx - form.b / 2), y: bereinigen(ny - form.t / 2), winkel: bereinigen(-form.winkel) };
  }
  if (achse === "x") return { ...form, x: sp(form.x + form.b) };
  const gespiegelt = { ...form, y: sp(form.y + form.t) };
  if (form.keil_mm) {
    const { z, h } = formHoehen(form, teilHoehe);
    // Vorn war h, hinten h + keil. Nach dem Spiegeln ist vorn h + keil und hinten h.
    gespiegelt.h_mm = bereinigen(h + form.keil_mm);
    gespiegelt.z_mm = z;
    gespiegelt.keil_mm = -form.keil_mm;
  }
  return gespiegelt;
}

/** Vorschlag für den Abstand zweier Kopien: Breite bzw. Tiefe der Form plus 5 mm. */
export function abstandsvorschlag(form: Form): { x: number; y: number } {
  const [x0, y0, x1, y1] = formBox(form);
  return { x: bereinigen(x1 - x0 + 5), y: bereinigen(y1 - y0 + 5) };
}

/** Mittelpunkt der Form (Mitte ihrer Bounding-Box). */
export function formMitte(form: Form): Punkt {
  const [x0, y0, x1, y1] = formBox(form);
  return [bereinigen((x0 + x1) / 2), bereinigen((y0 + y1) / 2)];
}

/** Wert in der Anzeige-Schreibweise (deutsch, mit Komma) für das Eingabefeld eines Maßes. */
export function masswertText(form: Form, feld: MassFeld): string {
  if (form.typ === "rechteck") return String(feld === "b" ? form.b : form.t).replace(".", ",");
  if (form.typ === "kreis") return String(bereinigen(form.r * 2)).replace(".", ",");
  return "";
}

/** Setzt ein Maß (Breite, Tiefe oder Durchmesser). Liefert null, wenn der Wert ungültig oder zu klein ist. */
export function masseSetzen(form: Form, feld: MassFeld, text: string): Form | null {
  const wert = Number(text.trim().replace(",", "."));
  if (text.trim() === "" || !Number.isFinite(wert) || wert < MIN_MM) return null;
  if (form.typ === "rechteck" && (feld === "b" || feld === "t")) {
    const neu = bereinigen(wert);
    // Eckenradius darf nicht größer werden als die halbe kürzere Seite
    const b = feld === "b" ? neu : form.b;
    const t = feld === "t" ? neu : form.t;
    const radius = form.radius ? Math.min(form.radius, bereinigen(Math.min(b, t) / 2)) : form.radius;
    return { ...form, b, t, ...(form.radius !== undefined ? { radius } : {}) };
  }
  if (form.typ === "kreis" && feld === "d") return { ...form, r: bereinigen(wert / 2) };
  return null;
}
