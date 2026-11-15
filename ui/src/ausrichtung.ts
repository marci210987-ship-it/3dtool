/**
 * Druckausrichtung: bewertet die sechs Lagen eines Körpers (je eine Seite nach unten) nach Überhang, Auflage und Höhe.
 * Rechnet auf dem Dreiecksnetz der 3D-Ansicht. Faustregel wie bei den Druckhinweisen: Flächen, die steiler als 45° über die
 * Senkrechte hinaus nach unten zeigen, brauchen ohne Stützen Hilfe. Das ist keine Slicer-Simulation.
 */

export type Vek3 = [number, number, number];

export interface NetzDaten {
  punkte: number[];
  dreiecke: number[];
}

export interface Lage {
  id: "gezeichnet" | "gedreht" | "vorne" | "hinten" | "links" | "rechts";
  name: string;
  /** Richtung, in die die untere Seite zeigt (Modellkoordinaten) */
  unten: Vek3;
  ueberhang_mm2: number;
  auflage_mm2: number;
  hoehe_mm: number;
}

const LAGEN: Array<Pick<Lage, "id" | "name" | "unten">> = [
  { id: "gezeichnet", name: "wie gezeichnet (Unterseite unten)", unten: [0, 0, -1] },
  { id: "gedreht", name: "umgedreht (Oberseite unten)", unten: [0, 0, 1] },
  { id: "vorne", name: "auf der Vorderseite", unten: [0, -1, 0] },
  { id: "hinten", name: "auf der Rückseite", unten: [0, 1, 0] },
  { id: "links", name: "auf der linken Seite", unten: [-1, 0, 0] },
  { id: "rechts", name: "auf der rechten Seite", unten: [1, 0, 0] },
];

const STEIL = 0.7072; // sin 45°: n·oben darunter heißt Überhang
const BETT_TOL = 0.05;

function runden(wert: number, stellen = 1): number {
  const f = 10 ** stellen;
  return Math.round(wert * f) / f;
}

/** Bewertet alle sechs Lagen. Die Reihenfolge der Rückgabe ist die der Lagen, nicht die der Güte. */
export function lagenBewerten(netz: NetzDaten): Lage[] {
  const p = netz.punkte;
  const t = netz.dreiecke;
  const n = Math.floor(t.length / 3);
  // Normalen und Flächen einmal berechnen
  const normale = new Float64Array(n * 3);
  const flaeche = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const a = t[i * 3] * 3;
    const b = t[i * 3 + 1] * 3;
    const c = t[i * 3 + 2] * 3;
    const ux = p[b] - p[a];
    const uy = p[b + 1] - p[a + 1];
    const uz = p[b + 2] - p[a + 2];
    const vx = p[c] - p[a];
    const vy = p[c + 1] - p[a + 1];
    const vz = p[c + 2] - p[a + 2];
    const nx = uy * vz - uz * vy;
    const ny = uz * vx - ux * vz;
    const nz = ux * vy - uy * vx;
    const laenge = Math.hypot(nx, ny, nz);
    if (laenge < 1e-12) continue;
    flaeche[i] = laenge / 2;
    normale[i * 3] = nx / laenge;
    normale[i * 3 + 1] = ny / laenge;
    normale[i * 3 + 2] = nz / laenge;
  }
  return LAGEN.map((lage) => {
    const [dx, dy, dz] = lage.unten;
    // „oben“ ist die Gegenrichtung; Höhe über der tiefsten Stelle in dieser Richtung
    const hoehe = (idx: number) => -(p[idx] * dx + p[idx + 1] * dy + p[idx + 2] * dz);
    let tief = Infinity;
    let hoch = -Infinity;
    for (let k = 0; k < p.length; k += 3) {
      const h = hoehe(k);
      if (h < tief) tief = h;
      if (h > hoch) hoch = h;
    }
    let ueberhang = 0;
    let auflage = 0;
    for (let i = 0; i < n; i++) {
      if (flaeche[i] === 0) continue;
      const nOben = -(normale[i * 3] * dx + normale[i * 3 + 1] * dy + normale[i * 3 + 2] * dz);
      if (nOben >= -STEIL) continue; // zeigt nicht steil genug nach unten
      // Auf dem Bett liegt ein Dreieck nur, wenn alle drei Ecken auf Betthöhe liegen (eine Spitze auf dem Bett genügt nicht)
      const hMax = Math.max(hoehe(t[i * 3] * 3), hoehe(t[i * 3 + 1] * 3), hoehe(t[i * 3 + 2] * 3));
      if (hMax - tief <= BETT_TOL) {
        if (nOben < -0.99) auflage += flaeche[i];
      } else {
        ueberhang += flaeche[i];
      }
    }
    return {
      ...lage,
      ueberhang_mm2: runden(ueberhang),
      auflage_mm2: runden(auflage),
      hoehe_mm: runden(hoch - tief),
    };
  });
}

export interface Empfehlung {
  beste: Lage;
  /** Die Lage „wie gezeichnet“ ist bereits (so gut wie) die beste */
  bereitsBeste: boolean;
  lagen: Lage[];
  text: string;
}

/**
 * Wählt die beste Lage: wenig Überhang, dann große Auflage, dann geringe Höhe. Überhänge unter 2 mm² und Unterschiede unter
 * 3 % zählen als gleich; bei Gleichstand gewinnt die Lage wie gezeichnet.
 */
export function beste(lagen: Lage[]): Empfehlung {
  const gezeichnet = lagen.find((l) => l.id === "gezeichnet")!;
  const gleich = (a: number, b: number, abs: number) => Math.abs(a - b) <= Math.max(abs, 0.03 * Math.max(a, b));
  let gewinner = gezeichnet;
  for (const l of lagen) {
    if (l === gewinner) continue;
    if (!gleich(l.ueberhang_mm2, gewinner.ueberhang_mm2, 2)) {
      if (l.ueberhang_mm2 < gewinner.ueberhang_mm2) gewinner = l;
      continue;
    }
    if (!gleich(l.auflage_mm2, gewinner.auflage_mm2, 2)) {
      if (l.auflage_mm2 > gewinner.auflage_mm2) gewinner = l;
      continue;
    }
    if (l.hoehe_mm < gewinner.hoehe_mm - 0.5) gewinner = l;
  }
  const bereits = gewinner === gezeichnet;
  const kurz = (l: Lage) => `Überhang ${l.ueberhang_mm2} mm², Auflage ${l.auflage_mm2} mm², Höhe ${l.hoehe_mm} mm`;
  const text = bereits
    ? `Die Lage wie gezeichnet ist die beste (${kurz(gezeichnet)}).`
    : `Besser ${gewinner.name}: ${kurz(gewinner)}. Wie gezeichnet: ${kurz(gezeichnet)}.`;
  return { beste: gewinner, bereitsBeste: bereits, lagen, text };
}

export function empfehlung(netz: NetzDaten): Empfehlung {
  return beste(lagenBewerten(netz));
}
