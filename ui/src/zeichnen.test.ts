import { describe, expect, it } from "vitest";
import { abstandsvorschlag, masseSetzen, masswertText, aussenmass, fangpunkteVon, ausrichten, formMitte, gitter, kopieren, kreismuster, laesstSichDrehen, reihe, spiegeln, bezugsrahmen, einrasten, fangpunkte, formBox, formHoehen, formOberkante, gesamthoehe, hoehenanteil, massangaben, VORLAGEN, zahlText, kreisAus, neuesTeil, polygonAus, rechteckAus, rechteckMm, runden, teilVonServer, verschieben, verschiebenMitFang, type Form } from "./zeichnen";

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
    expect(m.map((x) => x.text)).toContain("z 5 · h 20");
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

  it("rechnet Keil und Optionen in Höhen und Maße ein", () => {
    const keil = { typ: "rechteck" as const, x: 0, y: 0, b: 40, t: 30, loch: false, keil_mm: 10 };
    expect(formOberkante(keil, 5)).toBe(15);
    expect(formOberkante({ ...keil, keil_mm: -3 }, 5)).toBe(5);
    expect(gesamthoehe({ hoehe_mm: 5, formen: [keil] })).toBe(15);
    const m = massangaben({ ...keil, schraege_mm: 0, kante_art: "fase", kante_mm: 1 } as never, 4);
    expect(m.map((x) => x.text).join("|")).toContain("Keil 10");
    expect(m.map((x) => x.text).join("|")).toContain("Fase 1");
    const loch = massangaben({ typ: "kreis", x: 0, y: 0, r: 2, loch: true, schraege_mm: 1.5 }, 4);
    expect(loch.map((x) => x.text)).toContain("Schräge 1,5");
  });

  it("rastet Punkte an Fluchtlinien anderer Formen ein", () => {
    const platte: Form = { typ: "rechteck", x: 0, y: 0, b: 60, t: 40, loch: false };
    const punkte = fangpunkte([platte]);
    expect(punkte).toContainEqual([30, 20]);
    expect(punkte).toContainEqual([60, 40]);
    const r = einrasten([29.2, 15], punkte, 2);
    expect(r.punkt).toEqual([30, 15]);
    expect(r.fangX).toBe(30);
    expect(r.fangY).toBeUndefined();
    expect(einrasten([29.2, 20.5], punkte, 2).punkt).toEqual([30, 20]);
    expect(einrasten([45, 10], punkte, 1).fangX).toBeUndefined();
    expect(fangpunkte([platte], 0)).toEqual([]);
  });

  it("rastet beim Verschieben mit Kanten und Mitten ein", () => {
    const platte: Form = { typ: "rechteck", x: 0, y: 0, b: 60, t: 40, loch: false };
    const loch: Form = { typ: "kreis", x: 10, y: 10, r: 4, loch: true };
    // Loch um (19.2, 9.1) schieben: Mitte x 29.2 -> 30 (Mitte der Platte), Mitte y 19.1 -> 20
    const r = verschiebenMitFang(loch, 19.2, 9.1, [platte], 1.5);
    expect(r.dx).toBeCloseTo(20);
    expect(r.dy).toBeCloseTo(10);
    expect(r.fangX).toBe(30);
    expect(r.fangY).toBe(20);
    // weit weg: keine Korrektur
    const f = verschiebenMitFang(loch, 100, 100, [platte], 1.5);
    expect(f).toEqual({ dx: 100, dy: 100, fangX: undefined, fangY: undefined });
  });

  it("richtet Formen am Bezugsrahmen aus", () => {
    const formen: Form[] = [
      { typ: "rechteck", x: 0, y: 0, b: 60, t: 40, loch: false },
      { typ: "rechteck", x: 5, y: 7, b: 10, t: 10, loch: false },
      { typ: "kreis", x: 3, y: 3, r: 2, loch: true },
    ];
    const rahmen = bezugsrahmen(formen, 1);
    expect(rahmen).toEqual([0, 0, 60, 40]);
    expect(formBox(ausrichten(formen[1], "mitte-x", rahmen))).toEqual([25, 7, 35, 17]);
    expect(formBox(ausrichten(formen[1], "mitte-y", rahmen))).toEqual([5, 15, 15, 25]);
    expect(formBox(ausrichten(formen[1], "rechts", rahmen))).toEqual([50, 7, 60, 17]);
    expect(formBox(ausrichten(formen[1], "oben", rahmen))).toEqual([5, 30, 15, 40]);
    expect(formBox(ausrichten(formen[1], "links", rahmen))[0]).toBe(0);
    expect(formBox(ausrichten(formen[1], "unten", rahmen))[1]).toBe(0);
    // Loch wird an der Platte zentriert; Löcher zählen nicht zum Rahmen
    expect(bezugsrahmen(formen, 2)).toEqual([0, 0, 60, 40]);
    expect(bezugsrahmen([formen[2]], 5)).toBeNull();
    expect(ausrichten(formen[2], "mitte-x", null)).toBe(formen[2]);
  });

  it("erzeugt Reihen und Gitter ohne das Original", () => {
    const loch: Form = { typ: "kreis", x: 5, y: 5, r: 2, loch: true };
    const r = reihe(loch, 4, 10, 0);
    expect(r.map((f) => (f as { x: number }).x)).toEqual([15, 25, 35]);
    expect(reihe(loch, 1, 10, 0)).toEqual([]);
    const g = gitter(loch, 3, 2, 10, 8);
    expect(g).toHaveLength(5);
    expect(g.map((f) => [(f as { x: number }).x, (f as { y: number }).y])).toEqual([[15, 5], [25, 5], [5, 13], [15, 13], [25, 13]]);
    expect(gitter(loch, 1, 1, 10, 8)).toEqual([]);
    expect(kopieren(loch, 3, -2)).toMatchObject({ x: 8, y: 3 });
  });

  it("erzeugt Kreismuster für Kreise und Vielecke, nicht für Rechtecke", () => {
    const loch: Form = { typ: "kreis", x: 20, y: 10, r: 2, loch: true };
    const kopien = kreismuster(loch, [10, 10], 4, 360);
    expect(kopien).toHaveLength(3);
    expect(kopien.map((f) => [(f as { x: number }).x, (f as { y: number }).y])).toEqual([[10, 20], [0, 10], [10, 0]]);
    // Bogen: 3 Formen über 90 Grad -> 45 und 90 Grad
    const bogen = kreismuster(loch, [10, 10], 3, 90);
    expect(bogen.map((f) => [(f as { x: number }).x, (f as { y: number }).y])).toEqual([[17.071, 17.071], [10, 20]]);
    const dreieck: Form = { typ: "polygon", punkte: [[20, 10], [24, 10], [20, 14]], loch: false };
    const p = kreismuster(dreieck, [10, 10], 2, 360)[0] as { punkte: number[][] };
    expect(p.punkte).toEqual([[0, 10], [-4, 10], [0, 6]]);
    expect(kreismuster({ typ: "rechteck", x: 0, y: 0, b: 5, t: 5, loch: false, keil_mm: 2 }, [0, 0], 4)).toEqual([]);
    expect(laesstSichDrehen({ typ: "rechteck", x: 0, y: 0, b: 5, t: 5, loch: false, keil_mm: 2 })).toBe(false);
    expect(laesstSichDrehen({ typ: "rechteck", x: 0, y: 0, b: 5, t: 5, loch: false })).toBe(true);
    expect(kreismuster(loch, [10, 10], 1)).toEqual([]);
  });

  it("spiegelt Formen an Achsen und dreht den Keil um", () => {
    const rechteck: Form = { typ: "rechteck", x: 10, y: 5, b: 20, t: 10, loch: false };
    expect(spiegeln(rechteck, "x", 30, 5)).toMatchObject({ x: 30, y: 5, b: 20 });
    expect(spiegeln(rechteck, "x", 20, 5)).toMatchObject({ x: 10 });
    expect(spiegeln(rechteck, "y", 20, 5)).toMatchObject({ x: 10, y: 25, t: 10 });
    expect(spiegeln({ typ: "kreis", x: 4, y: 6, r: 2, loch: true }, "x", 10, 5)).toMatchObject({ x: 16, y: 6 });
    const dreieck: Form = { typ: "polygon", punkte: [[0, 0], [10, 0], [0, 6]], loch: false };
    expect(spiegeln(dreieck, "x", 5, 5)).toMatchObject({ punkte: [[10, 0], [0, 0], [10, 6]] });
    const keil: Form = { typ: "rechteck", x: 0, y: 0, b: 20, t: 10, loch: false, keil_mm: 6, h_mm: 4 };
    const k = spiegeln(keil, "y", 5, 4) as { y: number; h_mm: number; keil_mm: number };
    expect(k).toMatchObject({ y: 0, h_mm: 10, keil_mm: -6 });
    // doppelt gespiegelt = Ausgangsform
    expect(spiegeln(k as unknown as Form, "y", 5, 4)).toMatchObject({ y: 0, h_mm: 4, keil_mm: 6 });
    expect(abstandsvorschlag(rechteck)).toEqual({ x: 25, y: 15 });
    expect(formMitte(rechteck)).toEqual([20, 10]);
  });

  it("rechnet gedrehte Rechtecke: Bounding-Box, Fangpunkte, Kreismuster, Spiegeln", () => {
    const quadrat: Form = { typ: "rechteck", x: 0, y: 0, b: 10, t: 10, loch: false, winkel: 45 };
    const [x0, y0, x1, y1] = formBox(quadrat);
    expect(x1 - x0).toBeCloseTo(14.142, 2);
    expect((x0 + x1) / 2).toBeCloseTo(5, 3);
    expect((y0 + y1) / 2).toBeCloseTo(5, 3);
    expect(formBox({ ...quadrat, winkel: 180 })).toEqual([0, 0, 10, 10]);
    expect(formBox({ typ: "rechteck", x: 0, y: 0, b: 40, t: 20, loch: false, winkel: 90 })).toEqual([10, -10, 30, 30]);
    // Eckpunkte des gedrehten Rechtecks gehören zu den Fangpunkten
    const ecken = fangpunkteVon(quadrat);
    expect(ecken.some(([x, y]) => Math.abs(x - 5) < 1e-6 && Math.abs(y - (5 + 5 * Math.SQRT2)) < 1e-3)).toBe(true);
    // Kreismuster: Rechteck wandert auf den Kreis und dreht mit
    const platte: Form = { typ: "rechteck", x: 18, y: -2, b: 4, t: 4, loch: true };
    const kopien = kreismuster(platte, [0, 0], 4, 360);
    expect(kopien).toHaveLength(3);
    const k = kopien[0] as { x: number; y: number; winkel: number };
    expect(k.x + 2).toBeCloseTo(0, 3);
    expect(k.y + 2).toBeCloseTo(20, 3);
    expect(k.winkel).toBe(90);
    expect((kopien[1] as { winkel: number }).winkel).toBe(180);
    // Spiegeln: Mitte wird gespiegelt, Winkel wechselt das Vorzeichen
    const schraeg: Form = { typ: "rechteck", x: 0, y: 0, b: 10, t: 4, loch: false, winkel: 30 };
    const g = spiegeln(schraeg, "x", 20, 5) as { x: number; y: number; winkel: number };
    expect(g.x + 5).toBeCloseTo(35, 3);
    expect(g.y).toBe(0);
    expect(g.winkel).toBe(-30);
    expect((spiegeln(g as unknown as Form, "x", 20, 5) as { winkel: number }).winkel).toBe(30);
    expect(massangaben(schraeg, 3)[0].text).toBe("10 × 4 ∠ 30°");
  });

  it("ändert Maße per Eingabe und lehnt ungültige Werte ab", () => {
    const rechteck: Form = { typ: "rechteck", x: 5, y: 5, b: 40, t: 20, loch: false, radius: 9 };
    expect(masseSetzen(rechteck, "b", "55,5")).toMatchObject({ x: 5, y: 5, b: 55.5, t: 20, radius: 9 });
    // Radius schrumpft mit der kürzeren Seite mit
    expect(masseSetzen(rechteck, "t", "10")).toMatchObject({ t: 10, radius: 5 });
    expect(masseSetzen({ ...rechteck, radius: undefined }, "t", "10")).not.toHaveProperty("radius", 5);
    const kreis: Form = { typ: "kreis", x: 10, y: 10, r: 3, loch: true };
    expect(masseSetzen(kreis, "d", "8")).toMatchObject({ x: 10, y: 10, r: 4 });
    expect(masseSetzen(kreis, "d", "")).toBeNull();
    expect(masseSetzen(kreis, "d", "abc")).toBeNull();
    expect(masseSetzen(kreis, "d", "0,2")).toBeNull();
    expect(masseSetzen(kreis, "b", "5")).toBeNull();
    expect(masswertText(rechteck, "b")).toBe("40");
    expect(masswertText(kreis, "d")).toBe("6");
    expect(masswertText({ ...rechteck, b: 12.5 }, "b")).toBe("12,5");
    // nur Rechteck und Kreis haben änderbare Maße
    expect(massangaben(rechteck, 4).map((m) => m.feld)).toEqual(["b", "t"]);
    expect(massangaben(kreis, 4).map((m) => m.feld)).toEqual(["d"]);
    expect(massangaben({ typ: "polygon", punkte: [[0, 0], [5, 0], [0, 5]], loch: false }, 4)[0].feld).toBeUndefined();
  });
});
