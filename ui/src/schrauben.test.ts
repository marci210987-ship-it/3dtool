import { describe, expect, it } from "vitest";
import { kopfFelder, lochDurchmesser, schraubdom, SCHRAUBEN, STANDARD } from "./schrauben";

describe("Schraubenlöcher", () => {
  it("Durchgang und Kernloch mit Zuschlag", () => {
    expect(lochDurchmesser("M3", "durchgang")).toBe(3.5); // 3,4 + 0,1
    expect(lochDurchmesser("M3", "kern")).toBe(2.6); // 2,5 + 0,1
    expect(lochDurchmesser("M3", "durchgang", { ...STANDARD, zuschlag: 0.2 })).toBe(3.6);
    expect(lochDurchmesser("M5", "kern", { ...STANDARD, zuschlag: 0 })).toBe(4.2);
  });
  it("Einsatz: Außendurchmesser minus Abzug", () => {
    expect(lochDurchmesser("M3", "einsatz")).toBe(4.2); // 4,6 − 0,4
    expect(lochDurchmesser("M3", "einsatz", { ...STANDARD, einsatzAbzug: 0.6 })).toBe(4);
  });
  it("Tabelle ist in sich stimmig: wachsende Größen, Kern < Nenn < Durchgang", () => {
    const namen = Object.keys(SCHRAUBEN) as Array<keyof typeof SCHRAUBEN>;
    for (let i = 0; i < namen.length; i++) {
      const m = SCHRAUBEN[namen[i]];
      expect(m.kern).toBeLessThan(m.nenn);
      expect(m.durchgang).toBeGreaterThan(m.nenn);
      expect(m.einsatzAussen).toBeGreaterThan(m.nenn);
      if (i > 0) expect(m.nenn).toBeGreaterThan(SCHRAUBEN[namen[i - 1]].nenn);
    }
  });
  it("Kopf: Senkung und Gegenbohrung mit Spiel", () => {
    expect(kopfFelder("M3", "ohne")).toEqual({ senk_art: "keine" });
    expect(kopfFelder("M3", "senk")).toEqual({ senk_art: "senkung", senk_d_mm: 7, senk_seite: "oben" });
    expect(kopfFelder("M3", "zylinder")).toEqual({ senk_art: "gegenbohrung", senk_d_mm: 5.8, senk_t_mm: 3.3, senk_seite: "oben" });
  });
});

describe("Schraubdom", () => {
  it("Zylinder mit Loch, Loch ab Fußhöhe", () => {
    const [dom, loch] = schraubdom({ x: 10, y: 20, groesse: "M3", zweck: "kern", hoehe: 8, fuss: 3, wand: 1.6 });
    expect(dom).toMatchObject({ typ: "kreis", x: 10, y: 20, loch: false, z_mm: 3, h_mm: 8 });
    expect((dom as { r: number }).r).toBeCloseTo((2.6 + 3.2) / 2, 6);
    expect(loch).toMatchObject({ typ: "kreis", loch: true, z_mm: 3 });
    expect((loch as { r: number }).r).toBeCloseTo(1.3, 6);
  });
  it("Lochtiefe begrenzt den Beginn des Lochs", () => {
    const [, loch] = schraubdom({ x: 0, y: 0, groesse: "M3", zweck: "einsatz", hoehe: 10, fuss: 2, wand: 2, tiefe: 6 });
    expect((loch as { z_mm: number }).z_mm).toBe(6); // 2 + 10 − 6
    const [, tief] = schraubdom({ x: 0, y: 0, groesse: "M3", zweck: "einsatz", hoehe: 10, fuss: 2, wand: 2, tiefe: 99 });
    expect((tief as { z_mm: number }).z_mm).toBe(2); // nicht tiefer als der Dom
  });
});
