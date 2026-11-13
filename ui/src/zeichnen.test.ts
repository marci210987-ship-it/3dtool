import { describe, expect, it } from "vitest";
import { aussenmass, kreisAus, neuesTeil, polygonAus, rechteckAus, rechteckMm, runden, verschieben } from "./zeichnen";

describe("Zeichnen", () => {
  it("rastet auf das Raster ein", () => {
    expect(runden(12.4, 1)).toBe(12);
    expect(runden(12.6, 5)).toBe(15);
    expect(runden(3.3, 0)).toBe(3.3);
  });

  it("baut Formen aus zwei Punkten und verwirft zu kleine", () => {
    expect(rechteckAus([10, 5], [0, 25], false)).toEqual({ typ: "rechteck", x: 0, y: 5, b: 10, t: 20, loch: false });
    expect(rechteckAus([0, 0], [0.1, 20], false)).toBeNull();
    expect(kreisAus([5, 5], [8, 9], true)).toEqual({ typ: "kreis", x: 5, y: 5, r: 5, loch: true });
    expect(kreisAus([5, 5], [5, 5], false)).toBeNull();
    expect(polygonAus([[0, 0], [1, 1]], false)).toBeNull();
  });

  it("berechnet das Außenmaß nur aus Material, nicht aus Löchern", () => {
    const teil = neuesTeil([]);
    teil.formen = [
      { typ: "rechteck", x: 0, y: 0, b: 40, t: 30, loch: false },
      { typ: "kreis", x: 20, y: 15, r: 100, loch: true },
      { typ: "polygon", punkte: [[40, 0], [60, 0], [40, 30]], loch: false },
    ];
    expect(aussenmass(teil.formen)).toEqual({ breite: 60, tiefe: 30 });
    expect(aussenmass([{ typ: "kreis", x: 0, y: 0, r: 5, loch: true }])).toBeNull();
  });

  it("vergibt eindeutige Ids und verschiebt Formen", () => {
    const a = neuesTeil([]);
    const b = neuesTeil([a]);
    expect(a.id).toBe("E1");
    expect(b.id).toBe("E2");
    expect(verschieben({ typ: "rechteck", x: 1, y: 1, b: 2, t: 2, loch: false }, 4, -1)).toMatchObject({ x: 5, y: 0 });
    expect(verschieben({ typ: "polygon", punkte: [[0, 0], [2, 0], [0, 2]], loch: false }, 1, 1)).toMatchObject({
      punkte: [[1, 1], [3, 1], [1, 3]],
    });
  });

  it("berechnet die belegte Fläche in der Schublade mit Drehung", () => {
    const teil = neuesTeil([]);
    teil.formen = [{ typ: "rechteck", x: 5, y: 5, b: 40, t: 30, loch: false }];
    teil.x_mm = 12;
    teil.y_mm = 7;
    expect(rechteckMm(teil)).toEqual({ x: 12, y: 7, b: 40, t: 30 });
    teil.drehung = 90;
    expect(rechteckMm(teil)).toEqual({ x: 12, y: 7, b: 30, t: 40 });
    teil.formen = [];
    expect(rechteckMm(teil)).toBeNull();
  });
});
