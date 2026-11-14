/** Client-Logik für den 2D-Editor. Die Plattenaufteilung bleibt beim Sidecar. */

export const RASTER_MM = 42;
export const HOEHENEINHEIT_MM = 7;
export const LIPPE_MM = 4.4;

export type BoxArt = "raster" | "besteck";

export interface Box {
  id: string;
  name: string;
  x: number;
  y: number;
  ex: number;
  ey: number;
  ez: number;
  rotation: number;
  fachX: number;
  fachY: number;
  stapellippe: boolean;
  deckel: boolean;
  herausnehmbar: boolean;
  kabelkerben: boolean;
  art: BoxArt;
}

export interface KatalogEintrag {
  id: string;
  name: string;
  text: string;
  ex: number;
  ey: number;
  ez: number;
  fachX?: number;
  fachY?: number;
  deckel?: boolean;
  kabelkerben?: boolean;
  art?: BoxArt;
}

export const KATALOG: KatalogEintrag[] = [
  { id: "klein", name: "Kleine Box", text: "1 × 1 Feld", ex: 1, ey: 1, ez: 3 },
  { id: "schmal", name: "Schmale Box", text: "1 × 2 Felder", ex: 1, ey: 2, ez: 3 },
  { id: "mittel", name: "Mittlere Box", text: "2 × 2 Felder, vier Fächer", ex: 2, ey: 2, ez: 3, fachX: 2, fachY: 2 },
  { id: "gross", name: "Große Box", text: "2 × 3 Felder", ex: 2, ey: 3, ez: 3 },
  { id: "besteckfach", name: "Besteckfach", text: "1 × 4 Felder mit Unterteilungen", ex: 1, ey: 4, ez: 2, fachX: 1, fachY: 4 },
  { id: "deckel", name: "Box mit Deckel", text: "2 × 2, Deckel liegt lose auf", ex: 2, ey: 2, ez: 3, deckel: true },
  { id: "kabel", name: "Kabelbox", text: "3 × 3 mit Kerben für Kabel", ex: 3, ey: 3, ez: 4, fachX: 2, fachY: 2, kabelkerben: true },
  {
    id: "besteck",
    name: "Bestecksortierer",
    text: "Eigener Einsatz, mindestens 6 × 2 Felder",
    ex: 6,
    ey: 3,
    ez: 4,
    art: "besteck",
  },
];

export function boxBeschriftung(box: Pick<Box, "name" | "x" | "y" | "ex" | "ey" | "rotation">): string {
  return lageplanZeilen(box).join(" ");
}

export function lageplanZeilen(box: Pick<Box, "name" | "x" | "y" | "ex" | "ey" | "rotation">): string[] {
  const [, , breite, tiefe] = footprint(box);
  const mass = `${breite}×${tiefe}`;
  if (breite <= 1 && tiefe <= 1) return [mass];
  const typ = box.name.replace(/\s+Kopie$/, "").replace(/\s+B(?:\d+|-[0-9a-f]{4,})$/i, "").trim() || "Box";
  return [typ, mass];
}

/** Schriftgröße in Bildschirmpixeln: mindestens 13, größer bei größeren Boxen, aber innerhalb der Fläche. */
export function lageplanSchriftPx(boxBreitePx: number, boxHoehePx: number, zeilen: string[]): number {
  const zeichen = Math.max(1, ...zeilen.map((zeile) => zeile.length));
  const nachBreite = (Math.max(0, boxBreitePx) * 0.9) / (zeichen * 0.58);
  const nachHoehe = (Math.max(0, boxHoehePx) * 0.8) / (zeilen.length * 1.25);
  const passend = Math.min(nachBreite, nachHoehe);
  if (!Number.isFinite(passend) || passend <= 0) return 13;
  if (passend < 12) return Math.max(9, passend);
  return Math.min(22, Math.max(13, passend));
}

export function footprint(box: Pick<Box, "x" | "y" | "ex" | "ey" | "rotation">): [number, number, number, number] {
  const rot = ((box.rotation % 360) + 360) % 360;
  let ex = box.ex;
  let ey = box.ey;
  if (rot === 90 || rot === 270) {
    ex = box.ey;
    ey = box.ex;
  }
  return [box.x, box.y, ex, ey];
}

export function ueberlappt(a: Box, b: Box): boolean {
  const [ax, ay, aw, ah] = footprint(a);
  const [bx, by, bw, bh] = footprint(b);
  return ax < bx + bw && bx < ax + aw && ay < by + bh && by < ay + ah;
}

export function kollisionen(boxen: Box[]): { boxen: [string, string]; text: string }[] {
  const fund = [];
  for (let i = 0; i < boxen.length; i++) {
    for (let j = i + 1; j < boxen.length; j++) {
      if (ueberlappt(boxen[i], boxen[j])) {
        fund.push({
          boxen: [boxen[i].id, boxen[j].id] as [string, string],
          text: `${boxen[i].name} und ${boxen[j].name} überlappen sich.`,
        });
      }
    }
  }
  return fund;
}

export function ausserhalb(box: Box, ex: number, ey: number): boolean {
  const [x, y, w, h] = footprint(box);
  return x < 0 || y < 0 || x + w > ex || y + h > ey;
}

export function freieZellen(boxen: Box[], ex: number, ey: number): { x: number; y: number }[] {
  const belegt = new Set<string>();
  for (const box of boxen) {
    const [x, y, w, h] = footprint(box);
    for (let i = x; i < x + w; i++) {
      for (let j = y; j < y + h; j++) belegt.add(`${i},${j}`);
    }
  }
  const frei = [];
  for (let j = 0; j < ey; j++) {
    for (let i = 0; i < ex; i++) {
      if (!belegt.has(`${i},${j}`)) frei.push({ x: i, y: j });
    }
  }
  return frei;
}

export function boxHoeheMm(box: Pick<Box, "ez" | "stapellippe" | "art">): number {
  if (box.art === "besteck") return box.ez * HOEHENEINHEIT_MM;
  return box.ez * HOEHENEINHEIT_MM + (box.stapellippe ? LIPPE_MM : 0);
}

export function naechsteId(boxen: Box[]): string {
  const nums = boxen.map((b) => Number(/^B(\d+)$/.exec(b.id)?.[1] || 0));
  return `B${Math.max(0, ...nums) + 1}`;
}

export function neueBox(vorlage: KatalogEintrag, boxen: Box[], einheitenX: number, einheitenY: number): Box | null {
  const id = naechsteId(boxen);
  const kandidat: Box = {
    id,
    name: `${vorlage.name} ${id}`,
    x: 0,
    y: 0,
    ex: vorlage.ex,
    ey: vorlage.ey,
    ez: vorlage.ez,
    rotation: 0,
    fachX: vorlage.fachX ?? 1,
    fachY: vorlage.fachY ?? 1,
    stapellippe: vorlage.art !== "besteck",
    deckel: Boolean(vorlage.deckel),
    herausnehmbar: false,
    kabelkerben: Boolean(vorlage.kabelkerben),
    art: vorlage.art ?? "raster",
  };
  const [, , w, h] = footprint(kandidat);
  for (let y = 0; y <= einheitenY - h; y++) {
    for (let x = 0; x <= einheitenX - w; x++) {
      kandidat.x = x;
      kandidat.y = y;
      const stoesst = boxen.some((b) => ueberlappt(kandidat, b));
      if (!stoesst) return { ...kandidat };
    }
  }
  kandidat.x = 0;
  kandidat.y = 0;
  return { ...kandidat };
}

export function dupliziere(box: Box, boxen: Box[], einheitenX: number, einheitenY: number): Box {
  const kopie: Box = { ...box, id: naechsteId(boxen), name: `${box.name} Kopie` };
  const [, , w, h] = footprint(box);
  const versuche: [number, number][] = [
    [box.x + w, box.y],
    [box.x, box.y + h],
    [box.x - w, box.y],
    [box.x, box.y - h],
  ];
  for (const [x, y] of versuche) {
    kopie.x = x;
    kopie.y = y;
    if (ausserhalb(kopie, einheitenX, einheitenY)) continue;
    if (boxen.some((b) => ueberlappt(kopie, b))) continue;
    return { ...kopie };
  }
  return { ...kopie, x: box.x, y: box.y };
}

export function parseMm(wert: string): number {
  const zahl = Number(String(wert).trim().replace(",", "."));
  return Number.isFinite(zahl) ? zahl : NaN;
}
