/**
 * Import von Umrissen aus SVG- und DXF-Dateien.
 *
 * Gelesen werden nur geschlossene Konturen in der Ebene. Daraus entstehen Rechtecke, Kreise und Vielecke;
 * Kurven und Bögen werden in Linienzüge zerlegt. Konturen, die innerhalb einer anderen liegen, werden nach
 * der Gerade-Ungerade-Regel zu Löchern. Die Prüfung der Formen (z. B. Selbstüberschneidung) bleibt beim Sidecar.
 */

import { bereinigen, Form, MAX_FORMEN, Punkt } from "./zeichnen";

export type Kontur =
  | { typ: "kreis"; x: number; y: number; r: number }
  | { typ: "rechteck"; x: number; y: number; b: number; t: number; radius: number }
  | { typ: "polygon"; punkte: Punkt[] };

export interface ImportErgebnis {
  konturen: Kontur[];
  hinweise: string[];
  /** Vorschlag: Millimeter je Einheit der Datei */
  einheitMm: number;
  /** Ob die Einheit aus der Datei stammt (sonst Annahme 1 mm) */
  einheitBekannt: boolean;
  /** Format der Quelle, für die Anzeige */
  quelle: "svg" | "dxf";
}

const KURVEN_SCHRITTE = 16;
const MAX_PUNKTE = 2000;

// ------------------------------------------------------------------ Hilfen

type Matrix = [number, number, number, number, number, number]; // a b c d e f

const EINS: Matrix = [1, 0, 0, 1, 0, 0];

function mal(m: Matrix, n: Matrix): Matrix {
  return [
    m[0] * n[0] + m[2] * n[1],
    m[1] * n[0] + m[3] * n[1],
    m[0] * n[2] + m[2] * n[3],
    m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4],
    m[1] * n[4] + m[3] * n[5] + m[5],
  ];
}

function anwenden(m: Matrix, p: Punkt): Punkt {
  return [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]];
}

function zahlen(text: string): number[] {
  return (text.match(/[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g) || []).map(Number);
}

function parseTransform(text: string | null): Matrix {
  let m: Matrix = EINS;
  if (!text) return m;
  for (const treffer of text.matchAll(/(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)/g)) {
    const w = zahlen(treffer[2]);
    let t: Matrix = EINS;
    switch (treffer[1]) {
      case "matrix":
        if (w.length === 6) t = w as Matrix;
        break;
      case "translate":
        t = [1, 0, 0, 1, w[0] ?? 0, w[1] ?? 0];
        break;
      case "scale":
        t = [w[0] ?? 1, 0, 0, w[1] ?? w[0] ?? 1, 0, 0];
        break;
      case "rotate": {
        const a = ((w[0] ?? 0) * Math.PI) / 180;
        const dreh: Matrix = [Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0];
        t = w.length >= 3 ? mal(mal([1, 0, 0, 1, w[1], w[2]], dreh), [1, 0, 0, 1, -w[1], -w[2]]) : dreh;
        break;
      }
      case "skewX":
        t = [1, 0, Math.tan(((w[0] ?? 0) * Math.PI) / 180), 1, 0, 0];
        break;
      case "skewY":
        t = [1, Math.tan(((w[0] ?? 0) * Math.PI) / 180), 0, 1, 0, 0];
        break;
    }
    m = mal(m, t);
  }
  return m;
}

/** Nur Verschiebung und gleichmäßige oder getrennte Skalierung, keine Drehung oder Scherung. */
function achsparallel(m: Matrix): boolean {
  return Math.abs(m[1]) < 1e-9 && Math.abs(m[2]) < 1e-9;
}

function gleich(a: Punkt, b: Punkt, tol = 1e-6): boolean {
  return Math.abs(a[0] - b[0]) <= tol && Math.abs(a[1] - b[1]) <= tol;
}

/** Entfernt aufeinanderfolgende Doppelpunkte und den schließenden Punkt, der dem ersten gleicht. */
function bereinigePunkte(punkte: Punkt[]): Punkt[] {
  const aus: Punkt[] = [];
  for (const p of punkte) if (!aus.length || !gleich(aus[aus.length - 1], p)) aus.push(p);
  while (aus.length > 1 && gleich(aus[0], aus[aus.length - 1])) aus.pop();
  return aus;
}

function ellipsePunkte(cx: number, cy: number, rx: number, ry: number, schritte = 72): Punkt[] {
  return Array.from({ length: schritte }, (_, i) => {
    const w = (2 * Math.PI * i) / schritte;
    return [cx + rx * Math.cos(w), cy + ry * Math.sin(w)] as Punkt;
  });
}

// ------------------------------------------------------------------ SVG-Pfade

function bezier(p0: Punkt, p1: Punkt, p2: Punkt, p3: Punkt): Punkt[] {
  const aus: Punkt[] = [];
  for (let i = 1; i <= KURVEN_SCHRITTE; i++) {
    const t = i / KURVEN_SCHRITTE;
    const u = 1 - t;
    aus.push([
      u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
      u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
    ]);
  }
  return aus;
}

/** SVG-Bogen (Endpunktform) in Punkte zerlegen, nach der SVG-Spezifikation (F.6.5). */
function bogen(von: Punkt, rx: number, ry: number, drehung: number, gross: boolean, sweep: boolean, nach: Punkt): Punkt[] {
  if (gleich(von, nach)) return [];
  rx = Math.abs(rx);
  ry = Math.abs(ry);
  if (rx < 1e-9 || ry < 1e-9) return [nach];
  const phi = (drehung * Math.PI) / 180;
  const c = Math.cos(phi);
  const s = Math.sin(phi);
  const dx = (von[0] - nach[0]) / 2;
  const dy = (von[1] - nach[1]) / 2;
  const x1 = c * dx + s * dy;
  const y1 = -s * dx + c * dy;
  const lambda = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
  if (lambda > 1) {
    rx *= Math.sqrt(lambda);
    ry *= Math.sqrt(lambda);
  }
  const zaehler = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
  const nenner = rx * rx * y1 * y1 + ry * ry * x1 * x1;
  const faktor = (gross === sweep ? -1 : 1) * Math.sqrt(Math.max(0, zaehler / nenner));
  const cxs = (faktor * rx * y1) / ry;
  const cys = (-faktor * ry * x1) / rx;
  const cx = c * cxs - s * cys + (von[0] + nach[0]) / 2;
  const cy = s * cxs + c * cys + (von[1] + nach[1]) / 2;
  const winkel = (ux: number, uy: number, vx: number, vy: number) => {
    const a = Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
    return a;
  };
  const theta1 = winkel(1, 0, (x1 - cxs) / rx, (y1 - cys) / ry);
  let delta = winkel((x1 - cxs) / rx, (y1 - cys) / ry, (-x1 - cxs) / rx, (-y1 - cys) / ry);
  if (!sweep && delta > 0) delta -= 2 * Math.PI;
  if (sweep && delta < 0) delta += 2 * Math.PI;
  const schritte = Math.max(4, Math.ceil(Math.abs(delta) / (Math.PI / 36)));
  const aus: Punkt[] = [];
  for (let i = 1; i <= schritte; i++) {
    const a = theta1 + (delta * i) / schritte;
    aus.push([cx + rx * Math.cos(a) * c - ry * Math.sin(a) * s, cy + rx * Math.cos(a) * s + ry * Math.sin(a) * c]);
  }
  aus[aus.length - 1] = nach;
  return aus;
}

/** Zerlegt ein SVG-Pfaddatum in Linienzüge. geschlossen = mit Z beendet. */
export function pfadZuLinienzuegen(d: string): { punkte: Punkt[]; geschlossen: boolean }[] {
  const ergebnis: { punkte: Punkt[]; geschlossen: boolean }[] = [];
  const befehle = d.match(/[a-zA-Z][^a-zA-Z]*/g) || [];
  let aktuell: Punkt[] = [];
  let pos: Punkt = [0, 0];
  let start: Punkt = [0, 0];
  let letzteKontrolle: Punkt | null = null;
  let letzterBefehl = "";

  const abschliessen = (geschlossen: boolean) => {
    if (aktuell.length > 1) ergebnis.push({ punkte: aktuell, geschlossen });
    aktuell = [];
  };

  for (const roh of befehle) {
    const art = roh[0];
    const klein = art === art.toLowerCase();
    const w = art.toLowerCase() === "a" ? (roh.slice(1).match(/[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[01]/g) || []).map(Number) : zahlen(roh.slice(1));
    const rel = (p: Punkt): Punkt => (klein ? [pos[0] + p[0], pos[1] + p[1]] : p);
    const a = art.toLowerCase();
    if (a === "z") {
      if (aktuell.length) {
        abschliessen(true);
        pos = start;
        aktuell = [];
      }
      letzteKontrolle = null;
      letzterBefehl = a;
      continue;
    }
    let i = 0;
    const anzahl: Record<string, number> = { m: 2, l: 2, h: 1, v: 1, c: 6, s: 4, q: 4, t: 2, a: 7 };
    const n = anzahl[a];
    if (!n) continue;
    let erster = true;
    while (i + n <= w.length) {
      const arg = w.slice(i, i + n);
      i += n;
      if (a === "m") {
        const p = rel([arg[0], arg[1]]);
        if (erster) {
          abschliessen(false);
          start = p;
          aktuell = [p];
        } else {
          aktuell.push(p);
        }
        pos = p;
        letzteKontrolle = null;
      } else if (a === "l" || a === "h" || a === "v") {
        let p: Punkt;
        if (a === "l") p = rel([arg[0], arg[1]]);
        else if (a === "h") p = [klein ? pos[0] + arg[0] : arg[0], pos[1]];
        else p = [pos[0], klein ? pos[1] + arg[0] : arg[0]];
        if (!aktuell.length) aktuell = [pos];
        aktuell.push(p);
        pos = p;
        letzteKontrolle = null;
      } else if (a === "c" || a === "s") {
        const c1: Punkt = a === "c" ? rel([arg[0], arg[1]]) : letzteKontrolle && /[cs]/i.test(letzterBefehl) ? [2 * pos[0] - letzteKontrolle[0], 2 * pos[1] - letzteKontrolle[1]] : pos;
        const c2 = rel(a === "c" ? [arg[2], arg[3]] : [arg[0], arg[1]]);
        const ende = rel(a === "c" ? [arg[4], arg[5]] : [arg[2], arg[3]]);
        if (!aktuell.length) aktuell = [pos];
        aktuell.push(...bezier(pos, c1, c2, ende));
        letzteKontrolle = c2;
        pos = ende;
      } else if (a === "q" || a === "t") {
        const k: Punkt = a === "q" ? rel([arg[0], arg[1]]) : letzteKontrolle && /[qt]/i.test(letzterBefehl) ? [2 * pos[0] - letzteKontrolle[0], 2 * pos[1] - letzteKontrolle[1]] : pos;
        const ende = rel(a === "q" ? [arg[2], arg[3]] : [arg[0], arg[1]]);
        // quadratisch -> kubisch
        const c1: Punkt = [pos[0] + (2 / 3) * (k[0] - pos[0]), pos[1] + (2 / 3) * (k[1] - pos[1])];
        const c2: Punkt = [ende[0] + (2 / 3) * (k[0] - ende[0]), ende[1] + (2 / 3) * (k[1] - ende[1])];
        if (!aktuell.length) aktuell = [pos];
        aktuell.push(...bezier(pos, c1, c2, ende));
        letzteKontrolle = k;
        pos = ende;
      } else if (a === "a") {
        const ende = rel([arg[5], arg[6]]);
        if (!aktuell.length) aktuell = [pos];
        aktuell.push(...bogen(pos, arg[0], arg[1], arg[2], arg[3] === 1, arg[4] === 1, ende));
        pos = ende;
        letzteKontrolle = null;
      }
      erster = false;
      letzterBefehl = a;
    }
    letzterBefehl = a;
  }
  abschliessen(false);
  return ergebnis;
}

// ------------------------------------------------------------------ SVG

function laenge(text: string | null, referenz = 0): { wert: number; einheit: string } | null {
  if (!text) return null;
  const m = text.trim().match(/^([-+]?(?:\d+\.?\d*|\.\d+))\s*(mm|cm|in|pt|pc|px|%)?$/);
  if (!m) return null;
  return { wert: Number(m[1]) * (m[2] === "%" ? referenz / 100 : 1), einheit: m[2] || "" };
}

const MM_JE_EINHEIT: Record<string, number> = { mm: 1, cm: 10, in: 25.4, pt: 25.4 / 72, pc: 25.4 / 6, px: 25.4 / 96 };

export function leseSvg(text: string): ImportErgebnis {
  const hinweise: string[] = [];
  const konturen: Kontur[] = [];
  const dok = new DOMParser().parseFromString(text, "image/svg+xml");
  const wurzel = dok.documentElement;
  if (!wurzel || wurzel.nodeName.toLowerCase() !== "svg" || dok.getElementsByTagName("parsererror").length) {
    return { konturen, hinweise: ["Die Datei ist keine gültige SVG-Datei."], einheitMm: 1, einheitBekannt: false, quelle: "svg" };
  }

  // Maßstab aus width und viewBox
  let einheitMm = 1;
  let einheitBekannt = false;
  const vb = zahlen(wurzel.getAttribute("viewBox") || "");
  const breite = laenge(wurzel.getAttribute("width"));
  if (breite && breite.einheit && breite.einheit !== "%" && MM_JE_EINHEIT[breite.einheit]) {
    const mm = breite.wert * MM_JE_EINHEIT[breite.einheit];
    if (vb.length === 4 && vb[2] > 0) {
      einheitMm = mm / vb[2];
      einheitBekannt = true;
    } else if (breite.einheit !== "px") {
      einheitMm = MM_JE_EINHEIT[breite.einheit];
      einheitBekannt = true;
    }
  }
  if (!einheitBekannt) hinweise.push("Die Datei nennt keine Größe in Millimetern. Der Maßstab 1 Einheit = 1 mm ist eine Annahme und lässt sich ändern.");

  let ignoriert = 0;
  const ueberspringen = new Set(["defs", "clippath", "mask", "symbol", "metadata", "title", "desc", "style", "script", "pattern", "marker"]);

  const besuche = (el: Element, m: Matrix) => {
    const name = el.localName.toLowerCase();
    if (ueberspringen.has(name)) return;
    if (el.getAttribute("display") === "none" || /display\s*:\s*none/.test(el.getAttribute("style") || "")) return;
    const mt = mal(m, parseTransform(el.getAttribute("transform")));
    const num = (k: string, std = 0) => {
      const v = laenge(el.getAttribute(k));
      return v ? v.wert : std;
    };
    switch (name) {
      case "svg":
      case "g":
      case "a":
        for (const kind of Array.from(el.children)) besuche(kind, mt);
        return;
      case "rect": {
        const x = num("x");
        const y = num("y");
        const b = num("width");
        const t = num("height");
        if (b <= 0 || t <= 0) return;
        const rxA = el.getAttribute("rx");
        const ryA = el.getAttribute("ry");
        let rx = rxA !== null ? num("rx") : ryA !== null ? num("ry") : 0;
        const ry = ryA !== null ? num("ry") : rx;
        if (rxA === null && ryA !== null) rx = ry;
        if (achsparallel(mt) && Math.abs(Math.abs(mt[0]) - Math.abs(mt[3])) < 1e-9 * Math.max(1, Math.abs(mt[0]))) {
          const s = Math.abs(mt[0]);
          const [x0, y0] = anwenden(mt, [x, y]);
          const [x1, y1] = anwenden(mt, [x + b, y + t]);
          const radius = Math.abs(rx - ry) < 1e-9 ? Math.min(rx, b / 2, t / 2) * s : 0;
          if (rx !== ry) hinweise.push("Ein Rechteck mit ungleichen Eckenradien wurde mit eckigen Ecken übernommen.");
          konturen.push({ typ: "rechteck", x: Math.min(x0, x1), y: Math.min(y0, y1), b: Math.abs(x1 - x0), t: Math.abs(y1 - y0), radius });
        } else {
          if (rx > 0) hinweise.push("Gedrehte Rechtecke mit runden Ecken wurden mit eckigen Ecken übernommen.");
          konturen.push({ typ: "polygon", punkte: [[x, y], [x + b, y], [x + b, y + t], [x, y + t]].map((p) => anwenden(mt, p as Punkt)) });
        }
        return;
      }
      case "circle":
      case "ellipse": {
        const cx = num("cx");
        const cy = num("cy");
        const rx = name === "circle" ? num("r") : num("rx");
        const ry = name === "circle" ? rx : num("ry");
        if (rx <= 0 || ry <= 0) return;
        const gleichmaessig = achsparallel(mt) && Math.abs(Math.abs(mt[0]) - Math.abs(mt[3])) < 1e-9 * Math.max(1, Math.abs(mt[0]));
        if (rx === ry && gleichmaessig) {
          const [x, y] = anwenden(mt, [cx, cy]);
          konturen.push({ typ: "kreis", x, y, r: rx * Math.abs(mt[0]) });
        } else {
          konturen.push({ typ: "polygon", punkte: ellipsePunkte(cx, cy, rx, ry).map((p) => anwenden(mt, p)) });
        }
        return;
      }
      case "polygon":
      case "polyline": {
        const w = zahlen(el.getAttribute("points") || "");
        const punkte: Punkt[] = [];
        for (let i = 0; i + 1 < w.length; i += 2) punkte.push(anwenden(mt, [w[i], w[i + 1]]));
        const sauber = bereinigePunkte(punkte);
        if (sauber.length >= 3) {
          konturen.push({ typ: "polygon", punkte: sauber });
          if (name === "polyline" && !gleich(punkte[0], punkte[punkte.length - 1])) hinweise.push("Ein offener Linienzug wurde geschlossen.");
        }
        return;
      }
      case "path": {
        for (const lz of pfadZuLinienzuegen(el.getAttribute("d") || "")) {
          const sauber = bereinigePunkte(lz.punkte.map((p) => anwenden(mt, p)));
          if (sauber.length < 3) continue;
          if (!lz.geschlossen && !gleich(lz.punkte[0], lz.punkte[lz.punkte.length - 1])) hinweise.push("Ein offener Pfad wurde geschlossen.");
          konturen.push({ typ: "polygon", punkte: sauber });
        }
        return;
      }
      case "use":
      case "image":
      case "text":
      case "tspan":
        ignoriert += 1;
        return;
      default:
        for (const kind of Array.from(el.children)) besuche(kind, mt);
    }
  };
  besuche(wurzel, EINS);
  if (ignoriert) hinweise.push(`${ignoriert} Element(e) (Text, Bild oder Verweis) wurden ignoriert. Text vorher in Pfade umwandeln.`);
  if (!konturen.length) hinweise.push("Es wurden keine Umrisse gefunden.");
  return { konturen, hinweise: [...new Set(hinweise)], einheitMm, einheitBekannt, quelle: "svg" };
}

// ------------------------------------------------------------------ DXF

/** Bogen zwischen zwei Punkten mit Bulge-Wert (Polylinie). */
function bulgeBogen(a: Punkt, b: Punkt, bulge: number): Punkt[] {
  const sehne = Math.hypot(b[0] - a[0], b[1] - a[1]);
  if (sehne < 1e-12) return [];
  const winkel = 4 * Math.atan(bulge);
  const radius = sehne / (2 * Math.sin(Math.abs(winkel) / 2));
  const mx = (a[0] + b[0]) / 2;
  const my = (a[1] + b[1]) / 2;
  const abstand = Math.sqrt(Math.max(0, radius * radius - (sehne / 2) ** 2)) * (bulge > 0 ? 1 : -1) * (Math.abs(winkel) > Math.PI ? -1 : 1);
  const nx = -(b[1] - a[1]) / sehne;
  const ny = (b[0] - a[0]) / sehne;
  const cx = mx + nx * abstand;
  const cy = my + ny * abstand;
  const start = Math.atan2(a[1] - cy, a[0] - cx);
  const schritte = Math.max(4, Math.ceil(Math.abs(winkel) / (Math.PI / 36)));
  const aus: Punkt[] = [];
  for (let i = 1; i < schritte; i++) {
    const w = start + (winkel * i) / schritte;
    aus.push([cx + radius * Math.cos(w), cy + radius * Math.sin(w)]);
  }
  aus.push(b);
  return aus;
}

const DXF_EINHEITEN: Record<number, number> = { 1: 25.4, 2: 304.8, 4: 1, 5: 10, 6: 1000 };

export function leseDxf(text: string): ImportErgebnis {
  const hinweise: string[] = [];
  const konturen: Kontur[] = [];
  const zeilen = text.split(/\r?\n/).map((z) => z.trim());
  const paare: Array<[number, string]> = [];
  for (let i = 0; i + 1 < zeilen.length; i += 2) {
    const code = Number(zeilen[i]);
    if (!Number.isFinite(code)) {
      return { konturen, hinweise: ["Die Datei ist keine gültige ASCII-DXF-Datei."], einheitMm: 1, einheitBekannt: false, quelle: "dxf" };
    }
    paare.push([code, zeilen[i + 1]]);
  }
  if (!paare.some(([c, v]) => c === 0 && v === "SECTION")) {
    return { konturen, hinweise: ["Die Datei ist keine gültige ASCII-DXF-Datei (Binär-DXF wird nicht gelesen)."], einheitMm: 1, einheitBekannt: false, quelle: "dxf" };
  }

  // Einheit aus $INSUNITS
  let einheitMm = 1;
  let einheitBekannt = false;
  for (let i = 0; i < paare.length - 1; i++) {
    if (paare[i][0] === 9 && paare[i][1] === "$INSUNITS" && paare[i + 1][0] === 70) {
      const faktor = DXF_EINHEITEN[Number(paare[i + 1][1])];
      if (faktor) {
        einheitMm = faktor;
        einheitBekannt = true;
      }
    }
  }
  if (!einheitBekannt) hinweise.push("Die Datei nennt keine bekannte Einheit. Der Maßstab 1 Einheit = 1 mm ist eine Annahme und lässt sich ändern.");

  // Entitäten einsammeln
  type Entitaet = { art: string; felder: Array<[number, string]> };
  const entitaeten: Entitaet[] = [];
  let inEntities = false;
  let aktuell: Entitaet | null = null;
  for (let i = 0; i < paare.length; i++) {
    const [code, wert] = paare[i];
    if (code === 0 && wert === "SECTION") {
      inEntities = paare[i + 1]?.[0] === 2 && paare[i + 1][1] === "ENTITIES";
      aktuell = null;
      continue;
    }
    if (code === 0 && wert === "ENDSEC") {
      inEntities = false;
      aktuell = null;
      continue;
    }
    if (!inEntities) continue;
    if (code === 0) {
      aktuell = { art: wert, felder: [] };
      entitaeten.push(aktuell);
    } else if (aktuell) {
      aktuell.felder.push([code, wert]);
    }
  }

  const zahl = (e: Entitaet, code: number, std = 0) => {
    const f = e.felder.find(([c]) => c === code);
    return f ? Number(f[1]) : std;
  };
  const segmente: Punkt[][] = [];
  let ignoriert = new Set<string>();
  for (let i = 0; i < entitaeten.length; i++) {
    const e = entitaeten[i];
    if (e.art === "CIRCLE") {
      const r = zahl(e, 40);
      if (r > 0) konturen.push({ typ: "kreis", x: zahl(e, 10), y: zahl(e, 20), r });
    } else if (e.art === "LWPOLYLINE") {
      const punkte: Punkt[] = [];
      const bulges: number[] = [];
      let haengt = false;
      for (const [c, v] of e.felder) {
        if (c === 10) {
          punkte.push([Number(v), 0]);
          bulges.push(0);
          haengt = true;
        } else if (c === 20 && haengt) {
          punkte[punkte.length - 1][1] = Number(v);
        } else if (c === 42 && punkte.length) {
          bulges[punkte.length - 1] = Number(v);
        }
      }
      const geschlossen = (zahl(e, 70) & 1) === 1;
      const pfad: Punkt[] = [];
      const n = punkte.length;
      for (let k = 0; k < n; k++) {
        pfad.push(punkte[k]);
        if (k < n - 1 || geschlossen) {
          const naechster = punkte[(k + 1) % n];
          if (bulges[k]) pfad.push(...bulgeBogen(punkte[k], naechster, bulges[k]).slice(0, -1));
        }
      }
      const sauber = bereinigePunkte(pfad);
      if (geschlossen && sauber.length >= 3) konturen.push({ typ: "polygon", punkte: sauber });
      else if (sauber.length >= 2) segmente.push(pfad);
    } else if (e.art === "POLYLINE") {
      const geschlossen = (zahl(e, 70) & 1) === 1;
      const punkte: Punkt[] = [];
      let j = i + 1;
      while (j < entitaeten.length && entitaeten[j].art === "VERTEX") {
        punkte.push([zahl(entitaeten[j], 10), zahl(entitaeten[j], 20)]);
        if (zahl(entitaeten[j], 42)) ignoriert.add("Bögen in alten Polylinien (POLYLINE) wurden als gerade Strecken gelesen");
        j++;
      }
      i = j - 1;
      const sauber = bereinigePunkte(punkte);
      if (geschlossen && sauber.length >= 3) konturen.push({ typ: "polygon", punkte: sauber });
      else if (sauber.length >= 2) segmente.push(punkte);
    } else if (e.art === "LINE") {
      segmente.push([[zahl(e, 10), zahl(e, 20)], [zahl(e, 11), zahl(e, 21)]]);
    } else if (e.art === "ARC") {
      const r = zahl(e, 40);
      let a0 = zahl(e, 50);
      let a1 = zahl(e, 51);
      if (a1 <= a0) a1 += 360;
      const schritte = Math.max(2, Math.ceil((a1 - a0) / 5));
      const cx = zahl(e, 10);
      const cy = zahl(e, 20);
      const pfad: Punkt[] = [];
      for (let k = 0; k <= schritte; k++) {
        const w = ((a0 + ((a1 - a0) * k) / schritte) * Math.PI) / 180;
        pfad.push([cx + r * Math.cos(w), cy + r * Math.sin(w)]);
      }
      segmente.push(pfad);
    } else if (["ELLIPSE", "SPLINE", "INSERT", "HATCH", "TEXT", "MTEXT", "DIMENSION"].includes(e.art)) {
      ignoriert.add(e.art === "INSERT" ? "Blöcke (INSERT)" : e.art === "SPLINE" || e.art === "ELLIPSE" ? `${e.art === "SPLINE" ? "Splines" : "Ellipsen"}` : e.art);
    }
  }
  if (ignoriert.size) hinweise.push(`Nicht unterstützt und ignoriert: ${[...ignoriert].join(", ")}.`);

  // Linien und Bögen zu geschlossenen Konturen verketten
  const tol = 1e-4 * Math.max(1, ...segmente.flat().map((p) => Math.max(Math.abs(p[0]), Math.abs(p[1]))));
  const unbenutzt = segmente.map((s) => s.slice());
  let offen = 0;
  while (unbenutzt.length) {
    let kette = unbenutzt.shift()!;
    let weiter = true;
    while (weiter && !gleich(kette[0], kette[kette.length - 1], tol)) {
      weiter = false;
      for (let i = 0; i < unbenutzt.length; i++) {
        const s = unbenutzt[i];
        const ende = kette[kette.length - 1];
        const anfang = kette[0];
        if (gleich(ende, s[0], tol)) kette = [...kette, ...s.slice(1)];
        else if (gleich(ende, s[s.length - 1], tol)) kette = [...kette, ...s.slice(0, -1).reverse()];
        else if (gleich(anfang, s[s.length - 1], tol)) kette = [...s.slice(0, -1), ...kette];
        else if (gleich(anfang, s[0], tol)) kette = [...s.slice(1).reverse(), ...kette];
        else continue;
        unbenutzt.splice(i, 1);
        weiter = true;
        break;
      }
    }
    const sauber = bereinigePunkte(kette);
    if (gleich(kette[0], kette[kette.length - 1], tol) && sauber.length >= 3) konturen.push({ typ: "polygon", punkte: sauber });
    else offen += 1;
  }
  if (offen) hinweise.push(`${offen} offene Linienzug/-züge ohne geschlossenen Umriss wurden ignoriert.`);
  if (!konturen.length) hinweise.push("Es wurden keine geschlossenen Umrisse gefunden.");
  return { konturen, hinweise, einheitMm, einheitBekannt, quelle: "dxf" };
}

// ------------------------------------------------------------------ Umwandlung in Formen

function inPolygon(p: Punkt, poly: Punkt[]): boolean {
  let innen = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) innen = !innen;
  }
  return innen;
}

function umriss(k: Kontur): Punkt[] {
  if (k.typ === "polygon") return k.punkte;
  if (k.typ === "rechteck") return [[k.x, k.y], [k.x + k.b, k.y], [k.x + k.b, k.y + k.t], [k.x, k.y + k.t]];
  return ellipsePunkte(k.x, k.y, k.r, k.r, 32);
}

function distanzZuStrecke(p: Punkt, a: Punkt, b: Punkt): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  const u = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2));
  return Math.hypot(p[0] - (a[0] + u * dx), p[1] - (a[1] + u * dy));
}

/** Douglas-Peucker für geschlossene Linienzüge. */
export function vereinfachen(punkte: Punkt[], toleranz: number): Punkt[] {
  if (punkte.length <= 3 || toleranz <= 0) return punkte;
  // Ausgangspunkte: Punkt 0 und der am weitesten entfernte
  let weit = 1;
  let maxD = -1;
  for (let i = 1; i < punkte.length; i++) {
    const d = Math.hypot(punkte[i][0] - punkte[0][0], punkte[i][1] - punkte[0][1]);
    if (d > maxD) {
      maxD = d;
      weit = i;
    }
  }
  const teil = (von: number, bis: number, liste: Punkt[]): Punkt[] => {
    let idx = -1;
    let dmax = toleranz;
    for (let i = von + 1; i < bis; i++) {
      const d = distanzZuStrecke(liste[i], liste[von], liste[bis]);
      if (d > dmax) {
        dmax = d;
        idx = i;
      }
    }
    if (idx < 0) return [liste[von]];
    return [...teil(von, idx, liste), ...teil(idx, bis, liste)];
  };
  const a = punkte.slice(0, weit + 1);
  const b = [...punkte.slice(weit), punkte[0]];
  const ergebnis = [...teil(0, a.length - 1, a), ...teil(0, b.length - 1, b)];
  return ergebnis.length >= 3 ? ergebnis : punkte;
}

export interface FormenErgebnis {
  formen: Form[];
  hinweise: string[];
  breite: number;
  tiefe: number;
  anzahlLoecher: number;
}

/**
 * Wandelt Konturen in Formen um: Maßstab anwenden, y umdrehen (SVG/DXF-y zeigt nach unten bzw. oben je nach
 * Quelle), auf den Ursprung verschieben, innenliegende Konturen zu Löchern machen, Vielecke vereinfachen.
 */
export function zuFormen(erg: ImportErgebnis, massstab: number): FormenErgebnis {
  const hinweise = [...erg.hinweise];
  const leer: FormenErgebnis = { formen: [], hinweise, breite: 0, tiefe: 0, anzahlLoecher: 0 };
  if (!(massstab > 0) || !Number.isFinite(massstab)) {
    hinweise.push("Der Maßstab muss größer als 0 sein.");
    return leer;
  }
  if (!erg.konturen.length) return leer;
  const spiegeln = erg.quelle === "svg"; // SVG: y nach unten; DXF: y nach oben
  // Alle Punkte in Millimeter, y bei SVG gespiegelt
  const t = (p: Punkt): Punkt => [p[0] * massstab, (spiegeln ? -p[1] : p[1]) * massstab];
  const skaliert: Kontur[] = erg.konturen.map((k) => {
    if (k.typ === "kreis") {
      const [x, y] = t([k.x, k.y]);
      return { typ: "kreis", x, y, r: k.r * massstab };
    }
    if (k.typ === "rechteck") {
      const [x0, y0] = t([k.x, k.y]);
      const [x1, y1] = t([k.x + k.b, k.y + k.t]);
      return { typ: "rechteck", x: Math.min(x0, x1), y: Math.min(y0, y1), b: Math.abs(x1 - x0), t: Math.abs(y1 - y0), radius: k.radius * massstab };
    }
    return { typ: "polygon", punkte: k.punkte.map(t) };
  });
  // Auf den Ursprung verschieben
  const alle = skaliert.flatMap(umriss);
  const minX = Math.min(...alle.map((p) => p[0]));
  const minY = Math.min(...alle.map((p) => p[1]));
  const maxX = Math.max(...alle.map((p) => p[0]));
  const maxY = Math.max(...alle.map((p) => p[1]));
  // Bei Kreisen die echte Ausdehnung statt der Näherung verwenden
  let bx0 = minX, by0 = minY, bx1 = maxX, by1 = maxY;
  for (const k of skaliert) {
    if (k.typ === "kreis") {
      bx0 = Math.min(bx0, k.x - k.r);
      by0 = Math.min(by0, k.y - k.r);
      bx1 = Math.max(bx1, k.x + k.r);
      by1 = Math.max(by1, k.y + k.r);
    }
  }
  const verschiebung = (p: Punkt): Punkt => [bereinigen(p[0] - bx0), bereinigen(p[1] - by0)];
  const verschoben: Kontur[] = skaliert.map((k) => {
    if (k.typ === "kreis") {
      const [x, y] = verschiebung([k.x, k.y]);
      return { ...k, x, y, r: bereinigen(k.r) };
    }
    if (k.typ === "rechteck") {
      const [x, y] = verschiebung([k.x, k.y]);
      return { ...k, x, y, b: bereinigen(k.b), t: bereinigen(k.t), radius: bereinigen(k.radius) };
    }
    return { typ: "polygon", punkte: k.punkte.map(verschiebung) };
  });

  // Vielecke vereinfachen, bis sie in die Punktgrenze passen
  let toleranz = 0.02;
  let punkteGesamt = 0;
  let vereinfacht: Kontur[] = verschoben;
  for (const tol of [0.02, 0.05, 0.1, 0.2, 0.5]) {
    toleranz = tol;
    vereinfacht = verschoben.map((k) => (k.typ === "polygon" ? { typ: "polygon", punkte: vereinfachen(k.punkte, tol) } : k));
    punkteGesamt = vereinfacht.reduce((s, k) => s + (k.typ === "polygon" ? k.punkte.length : 0), 0);
    if (punkteGesamt <= MAX_PUNKTE) break;
  }
  if (toleranz > 0.02) hinweise.push(`Die Umrisse wurden auf ${toleranz} mm genau vereinfacht (zu viele Punkte).`);
  if (punkteGesamt > MAX_PUNKTE) hinweise.push(`Die Umrisse haben noch ${punkteGesamt} Punkte (empfohlen: höchstens ${MAX_PUNKTE}). Datei vereinfachen.`);

  // Verschachtelung: gerade Tiefe = Material, ungerade = Loch
  const umrisse = vereinfacht.map(umriss);
  const formen: Form[] = [];
  let loecher = 0;
  vereinfacht.forEach((k, i) => {
    const probe = umrisse[i][0];
    let tiefe = 0;
    umrisse.forEach((u, j) => {
      if (j !== i && inPolygon(probe, u)) tiefe += 1;
    });
    const loch = tiefe % 2 === 1;
    if (loch) loecher += 1;
    if (k.typ === "kreis") formen.push({ typ: "kreis", x: k.x, y: k.y, r: k.r, loch });
    else if (k.typ === "rechteck") formen.push({ typ: "rechteck", x: k.x, y: k.y, b: k.b, t: k.t, loch, ...(k.radius > 0 ? { radius: k.radius } : {}) });
    else formen.push({ typ: "polygon", punkte: k.punkte, loch });
  });
  if (formen.length > MAX_FORMEN) {
    hinweise.push(`Es sind ${formen.length} Umrisse, höchstens ${MAX_FORMEN} sind möglich. Es wurden nur die ersten ${MAX_FORMEN} übernommen.`);
    formen.length = MAX_FORMEN;
  }
  if (!formen.some((f) => !f.loch)) hinweise.push("Alle Umrisse liegen ineinander und ergeben nur Löcher. Es fehlt eine äußere Form.");
  return { formen, hinweise: [...new Set(hinweise)], breite: bereinigen(bx1 - bx0), tiefe: bereinigen(by1 - by0), anzahlLoecher: loecher };
}

/** Liest eine Datei als Text; FileReader, weil nicht jede Umgebung Blob.text() kennt. */
export function dateiText(datei: Blob): Promise<string> {
  return new Promise((ok, fehler) => {
    const leser = new FileReader();
    leser.onload = () => ok(String(leser.result ?? ""));
    leser.onerror = () => fehler(leser.error ?? new Error("Datei nicht lesbar"));
    leser.readAsText(datei);
  });
}
