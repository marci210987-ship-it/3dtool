import { describe, expect, it } from "vitest";
import { empfehlung, lagenBewerten, type NetzDaten } from "./ausrichtung";

/** Quader als Netz mit nach außen zeigenden Normalen. */
function quader(x0: number, y0: number, z0: number, x1: number, y1: number, z1: number): NetzDaten {
  const p = [x0, y0, z0, x1, y0, z0, x1, y1, z0, x0, y1, z0, x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1];
  const d = [
    0, 2, 1, 0, 3, 2, // unten (Normale −z)
    4, 5, 6, 4, 6, 7, // oben
    0, 1, 5, 0, 5, 4, // vorne (−y)
    2, 3, 7, 2, 7, 6, // hinten (+y)
    0, 4, 7, 0, 7, 3, // links (−x)
    1, 2, 6, 1, 6, 5, // rechts (+x)
  ];
  return { punkte: p, dreiecke: d };
}

/** Vierseitige Pyramide: Grundfläche z = 0 mit Seite b, Spitze bei Höhe h (oder bei z = 0 mit Grundfläche oben, wenn gedreht). */
function pyramide(b: number, h: number, gedreht = false): NetzDaten {
  const z0 = gedreht ? h : 0;
  const zs = gedreht ? 0 : h;
  const m = b / 2;
  const p = [0, 0, z0, b, 0, z0, b, b, z0, 0, b, z0, m, m, zs];
  // Außenseite der Grundfläche zeigt von der Spitze weg
  const grund = gedreht ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
  const seiten = gedreht ? [0, 4, 1, 1, 4, 2, 2, 4, 3, 3, 4, 0] : [0, 1, 4, 1, 2, 4, 2, 3, 4, 3, 0, 4];
  return { punkte: p, dreiecke: [...grund, ...seiten] };
}

describe("Druckausrichtung", () => {
  it("Quader: keine Überhänge, Auflage je nach Seite, gezeichnet gewinnt bei Gleichstand", () => {
    const lagen = lagenBewerten(quader(0, 0, 0, 40, 30, 10));
    const l = Object.fromEntries(lagen.map((x) => [x.id, x]));
    expect(lagen.every((x) => x.ueberhang_mm2 === 0)).toBe(true);
    expect(l.gezeichnet.auflage_mm2).toBe(1200);
    expect(l.gezeichnet.hoehe_mm).toBe(10);
    expect(l.vorne.auflage_mm2).toBe(400); // 40 × 10
    expect(l.vorne.hoehe_mm).toBe(30);
    expect(empfehlung(quader(0, 0, 0, 40, 30, 10)).beste.id).toBe("gezeichnet");
  });

  it("flache Spitze nach oben ist gut, nach unten braucht Stützen", () => {
    const l = Object.fromEntries(lagenBewerten(pyramide(40, 8)).map((x) => [x.id, x]));
    expect(l.gezeichnet.ueberhang_mm2).toBe(0);
    expect(l.gezeichnet.auflage_mm2).toBe(1600);
    expect(l.gedreht.ueberhang_mm2).toBeGreaterThan(1000); // flache Seiten hängen fast waagerecht über
    expect(empfehlung(pyramide(40, 8)).bereitsBeste).toBe(true);
  });

  it("gezeichnet mit der flachen Spitze unten: die Empfehlung dreht das Teil um", () => {
    const e = empfehlung(pyramide(40, 8, true));
    expect(e.bereitsBeste).toBe(false);
    expect(e.beste.id).toBe("gedreht");
    expect(e.text).toContain("Besser");
    expect(e.beste.ueberhang_mm2).toBe(0);
  });

  it("steile Spitze (Wand weniger als 45° von der Senkrechten): in beiden Lagen kein Überhang", () => {
    const l = Object.fromEntries(lagenBewerten(pyramide(10, 20)).map((x) => [x.id, x]));
    expect(l.gezeichnet.ueberhang_mm2).toBe(0);
    expect(l.gedreht.ueberhang_mm2).toBe(0);
  });

  it("leeres Netz bricht nicht ab", () => {
    expect(() => empfehlung({ punkte: [], dreiecke: [] })).not.toThrow();
  });
});
