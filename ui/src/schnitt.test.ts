import { describe, expect, it } from "vitest";
import { bereichModell, fangen, messen, schnittEbene, schnittPosition, szeneZuModell } from "./schnitt";

// Hilfsfunktion: Abstand eines Szenenpunkts von der Ebene (≥ 0 bleibt stehen)
const abstand = (e: { normal: [number, number, number]; konstante: number }, p: [number, number, number]) => e.normal[0] * p[0] + e.normal[1] * p[1] + e.normal[2] * p[2] + e.konstante;

describe("Schnittebene", () => {
  it("z: bleibt unterhalb der Höhe stehen", () => {
    const e = schnittEbene("z", 5);
    expect(abstand(e, [0, 3, 0])).toBeGreaterThan(0); // Höhe 3 bleibt
    expect(abstand(e, [0, 7, 0])).toBeLessThan(0); // Höhe 7 wird abgeschnitten
  });
  it("x: bleibt links der Position stehen", () => {
    const e = schnittEbene("x", 20);
    expect(abstand(e, [10, 0, 0])).toBeGreaterThan(0);
    expect(abstand(e, [30, 0, 0])).toBeLessThan(0);
  });
  it("y: Modell-y ist Szenen-minus-z", () => {
    const e = schnittEbene("y", 15);
    // Modell-y 10 = Szene-z −10: bleibt; Modell-y 20 = Szene-z −20: weg
    expect(abstand(e, [0, 0, -10])).toBeGreaterThan(0);
    expect(abstand(e, [0, 0, -20])).toBeLessThan(0);
  });
  it("umkehren zeigt die andere Seite", () => {
    const e = schnittEbene("z", 5, true);
    expect(abstand(e, [0, 3, 0])).toBeLessThan(0);
    expect(abstand(e, [0, 7, 0])).toBeGreaterThan(0);
  });
});

describe("Bereich und Position", () => {
  it("Bereich je Achse aus der Szenen-Box", () => {
    expect(bereichModell([0, 0, -30], [40, 10, 0], "x")).toEqual([0, 40]);
    expect(bereichModell([0, 0, -30], [40, 10, 0], "z")).toEqual([0, 10]);
    expect(bereichModell([0, 0, -30], [40, 10, 0], "y")).toEqual([0, 30]);
  });
  it("Schieber begrenzt und rundet", () => {
    expect(schnittPosition([0, 10], 0.5)).toBe(5);
    expect(schnittPosition([0, 10], 2)).toBe(10);
    expect(schnittPosition([0, 10], -1)).toBe(0);
  });
});

describe("Messen", () => {
  it("Szenenpunkt zu Modell", () => {
    expect(szeneZuModell([5, 7, -3])).toEqual([5, 3, 7]);
    expect(szeneZuModell([55, 7, -3], 50)).toEqual([5, 3, 7]);
  });
  it("Abstand und Teilmaße", () => {
    expect(messen([0, 0, 0], [3, 4, 0])).toEqual({ abstand: 5, dx: 3, dy: 4, dz: 0, steigung: 0 });
    const m = messen([0, 0, 0], [10, 0, 10]);
    expect(m.abstand).toBe(14.14);
    expect(m.steigung).toBe(45);
  });
  it("Fangen an Eckpunkten", () => {
    const ecken: [number, number, number][] = [[0, 0, 0], [10, 0, 0]];
    expect(fangen([9.2, 0.5, 0], ecken)).toEqual({ punkt: [10, 0, 0], gefangen: true });
    expect(fangen([5, 5, 5], ecken)).toEqual({ punkt: [5, 5, 5], gefangen: false });
  });
});
