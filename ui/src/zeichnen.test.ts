import { describe, expect, it } from "vitest";
import { aussenmass, formHoehen, gesamthoehe, hoehenanteil, massangaben, VORLAGEN, zahlText, kreisAus, neuesTeil, polygonAus, rechteckAus, rechteckMm, runden, teilVonServer, verschieben } from "./zeichnen";

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

  it("hat Standardwerte für Kanten und liest alte Dateien", () => {
    const teil = neuesTeil([]);
    expect([teil.kante_oben_art, teil.kante_oben_mm, teil.kante_unten_mm]).toEqual(["keine", 0, 0]);
    const alt = teilVonServer({ id: "E1", name: "Alt", formen: [] });
    expect([alt.kante_oben_art, alt.kante_oben_mm, alt.kante_unten_mm]).toEqual(["keine", 0, 0]);
    const neu = teilVonServer({ id: "E2", kante_oben_art: "rund", kante_oben_mm: 1.5, kante_unten_mm: 0.6 });
    expect([neu.kante_oben_art, neu.kante_oben_mm, neu.kante_unten_mm]).toEqual(["rund", 1.5, 0.6]);
    expect(teilVonServer({ id: "E3", kante_oben_art: "quatsch" }).kante_oben_art).toBe("keine");
  });

  it("liefert Maßangaben mit deutscher Zahlenschreibweise", () => {
    expect(zahlText(12)).toBe("12");
    expect(zahlText(12.54)).toBe("12,5");
    expect(zahlText(0.04)).toBe("0");
    const rechteck = massangaben({ typ: "rechteck", x: 10, y: 5, b: 40, t: 30, loch: false }, 4);
    expect(rechteck.map((m) => m.text)).toEqual(["40", "30"]);
    expect(rechteck[0]).toMatchObject({ x: 30, y: 39 });
    expect(rechteck[1]).toMatchObject({ x: 54, y: 20 });
    expect(massangaben({ typ: "kreis", x: 5, y: 5, r: 4.25, loch: true }, 4)[0].text).toBe("Ø 8,5");
    const dreieck = { typ: "polygon" as const, punkte: [[0, 0], [30, 0], [0, 40]] as [number, number][], loch: false };
    expect(massangaben(dreieck, 4)[0].text).toBe("30 × 40");
    expect(massangaben(dreieck, 4, true).map((m) => m.text)).toEqual(["30", "50", "40"]);
  });

  it("berechnet Höhen von Formen und die Gesamthöhe", () => {
    const teil = neuesTeil([]);
    teil.hoehe_mm = 5;
    teil.formen = [
      { typ: "rechteck", x: 0, y: 0, b: 60, t: 40, loch: false },
      { typ: "rechteck", x: 20, y: 10, b: 20, t: 20, loch: false, z_mm: 5, h_mm: 20 },
      { typ: "kreis", x: 10, y: 20, r: 4, loch: true, z_mm: 2, h_mm: 2 },
    ];
    expect(formHoehen(teil.formen[0], 5)).toEqual({ z: 0, h: 5 });
    expect(formHoehen({ typ: "rechteck", x: 0, y: 0, b: 1, t: 1, loch: false, z_mm: 3 }, 10)).toEqual({ z: 3, h: 7 });
    expect(gesamthoehe(teil)).toBe(25);
    expect(hoehenanteil(teil.formen[0], teil)).toBeCloseTo(0.2);
    expect(hoehenanteil(teil.formen[1], teil)).toBe(1);
    const nurLoch = { hoehe_mm: 8, formen: [{ typ: "kreis" as const, x: 0, y: 0, r: 2, loch: true }] };
    expect(gesamthoehe(nurLoch)).toBe(8);
  });

  it("zeigt Höhenangaben in den Maßen und hat brauchbare Vorlagen", () => {
    const m = massangaben({ typ: "rechteck", x: 0, y: 0, b: 10, t: 10, loch: false, z_mm: 5, h_mm: 20 }, 4);
    expect(m.map((x) => x.text)).toContain("z 5 h 20");
    expect(VORLAGEN.length).toBeGreaterThanOrEqual(4);
    for (const v of VORLAGEN) {
      const teil = { ...neuesTeil([]), ...v.erzeuge() };
      expect(teil.formen.length).toBeGreaterThan(0);
      expect(aussenmass(teil.formen)).not.toBeNull();
      expect(gesamthoehe(teil)).toBeGreaterThan(0);
      expect(gesamthoehe(teil)).toBeLessThanOrEqual(256);
    }
    expect(new Set(VORLAGEN.map((v) => v.id)).size).toBe(VORLAGEN.length);
  });
});
