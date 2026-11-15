/** Rechnung für Schnittebene und Messen in der 3D-Ansicht (Modell: x rechts, y nach hinten, z nach oben). */

export type Achse = "x" | "y" | "z";
export type Vek = [number, number, number];

/**
 * Schnittebene in Szenenkoordinaten (three.js: y nach oben, z zum Betrachter). Das Modell ist um −90° um x gedreht,
 * Modell-z liegt also auf Szenen-y und Modell-y auf Szenen-(−z). Die Ebene lässt Material mit Abstand ≥ 0 stehen:
 * ohne Umkehr bleibt alles bis zur Position (Modellkoordinate) stehen.
 */
export function schnittEbene(achse: Achse, pos: number, umkehren = false): { normal: Vek; konstante: number } {
  const vorzeichen = umkehren ? -1 : 1;
  if (achse === "x") return { normal: [-vorzeichen, 0, 0], konstante: vorzeichen * pos };
  if (achse === "z") return { normal: [0, -vorzeichen, 0], konstante: vorzeichen * pos };
  // Modell-y ist Szenen-(−z): bleibt y_modell <= pos, dann bleibt z_szene >= −pos
  return { normal: [0, 0, vorzeichen], konstante: vorzeichen * pos };
}

/** Bereich einer Modellachse (min, max) aus der Szenen-Box (min und max als Szenenkoordinaten). */
export function bereichModell(min: Vek, max: Vek, achse: Achse): [number, number] {
  if (achse === "x") return [min[0], max[0]];
  if (achse === "z") return [min[1], max[1]];
  return [-max[2] + 0, -min[2] + 0];
}

/** Position (mm, Modellkoordinate) aus dem Schieberwert 0 bis 1. */
export function schnittPosition(bereich: [number, number], anteil: number): number {
  const a = Math.max(0, Math.min(1, anteil));
  return Math.round((bereich[0] + (bereich[1] - bereich[0]) * a) * 100) / 100;
}

/** Szenenpunkt in Modellkoordinaten umrechnen (ohne Versatz des Teils). */
export function szeneZuModell(p: Vek, versatzX = 0): Vek {
  return [Math.round((p[0] - versatzX) * 1000) / 1000 + 0, Math.round(-p[2] * 1000) / 1000 + 0, Math.round(p[1] * 1000) / 1000 + 0];
}

export interface Messung {
  abstand: number;
  dx: number;
  dy: number;
  dz: number;
  /** Winkel zur Waagerechten in Grad */
  steigung: number;
}

export function messen(a: Vek, b: Vek): Messung {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const dz = b[2] - a[2];
  const waagerecht = Math.hypot(dx, dy);
  const r = (v: number) => Math.round(v * 100) / 100;
  return { abstand: r(Math.hypot(dx, dy, dz)), dx: r(dx), dy: r(dy), dz: r(dz), steigung: r((Math.atan2(dz, waagerecht) * 180) / Math.PI) };
}

/** Nächster Eckpunkt innerhalb der Fangweite (mm), sonst der Treffer selbst. */
export function fangen(treffer: Vek, ecken: Vek[], weite = 2): { punkt: Vek; gefangen: boolean } {
  let beste: Vek | null = null;
  let abstand = weite;
  for (const e of ecken) {
    const d = Math.hypot(e[0] - treffer[0], e[1] - treffer[1], e[2] - treffer[2]);
    if (d <= abstand) {
      abstand = d;
      beste = e;
    }
  }
  return beste ? { punkt: beste, gefangen: true } : { punkt: treffer, gefangen: false };
}
