import { describe, expect, it } from "vitest";
import { bedingungenAnwenden, bedingungenBereinigen } from "./bedingungen";
import { neuesTeil, teilVonServer, type Eigenteil, type Form } from "./zeichnen";
import { kalibrierteile, profilPruefen } from "./druckprofile";

function teil(): Eigenteil {
  return { ...neuesTeil([]), formen: [
    { fid: "a", typ: "rechteck", x: 0, y: 0, b: 40, t: 20, loch: false, winkel: 30 },
    { fid: "b", typ: "kreis", x: 2, y: 3, r: 2, loch: true },
    { fid: "c", typ: "kreis", x: 1, y: 1, r: 1, loch: true },
  ] };
}
describe("dauerhafte Skizzenbedingungen", () => {
  it("zentriert Löcher nach Größenänderung, lädt und löst Abhängigkeiten in beliebiger Reihenfolge", () => {
    let t = teil();
    t.bedingungen = [{ art: "abstand", quelle: "b", ziel: "c", dx: 10, dy: -2 }, { art: "mittig", quelle: "a", ziel: "b" }];
    t = bedingungenAnwenden(t);
    expect(t.formen[2]).toMatchObject({ x: 30, y: 8 });
    const f = t.formen[0]; if (f.typ === "rechteck") f.b = 60;
    t = bedingungenAnwenden(teilVonServer(JSON.parse(JSON.stringify(t))));
    expect(t.formen[1]).toMatchObject({ x: 30, y: 10 });
    expect(t.formen[2]).toMatchObject({ x: 40, y: 8 });
  });
  it("weist Kreisbezüge, widersprüchliche Lagebedingungen und ungültige Abstände zurück", () => {
    const t = teil();
    expect(() => bedingungenAnwenden({ ...t, bedingungen: [{ art: "mittig", quelle: "a", ziel: "b" }, { art: "mittig", quelle: "b", ziel: "a" }] })).toThrow(/Kreisbezug/);
    expect(() => bedingungenAnwenden({ ...t, bedingungen: [{ art: "mittig", quelle: "a", ziel: "b" }, { art: "abstand", quelle: "c", ziel: "b", dx: 1, dy: 2 }] })).toThrow(/bereits/);
    expect(() => bedingungenAnwenden({ ...t, bedingungen: [{ art: "abstand", quelle: "a", ziel: "b", dx: NaN, dy: 0 }] })).toThrow(/Zahlen/);
  });
  it("löst Größe und Parallelität vor der Zentrierung", () => {
    const t = teil();
    t.formen[1] = { fid: "b", typ: "rechteck", x: 50, y: 50, b: 5, t: 5, loch: false };
    t.bedingungen = [{ art: "mittig", quelle: "a", ziel: "b" }, { art: "gleich", quelle: "a", ziel: "b" }, { art: "parallel", quelle: "a", ziel: "b" }];
    expect(bedingungenAnwenden(t).formen[1]).toMatchObject({ x: 0, y: 0, b: 40, t: 20, winkel: 30 });
  });
  it("löst Beziehungen beim Löschen und gibt Kopien eigene Kennungen", () => {
    const t = teil(); t.bedingungen = [{ art: "mittig", quelle: "a", ziel: "b" }];
    t.formen = t.formen.filter((f) => f.fid !== "a");
    expect(bedingungenBereinigen(t).bedingungen).toEqual([]);
    t.formen.push({ ...t.formen[0] } as Form);
    expect(new Set(bedingungenBereinigen(t).formen.map((f) => f.fid)).size).toBe(3);
  });
});
describe("Druckprofile und Kalibrierung", () => {
  it("erstellt fünf Loch/Stift-Paare mit definiertem radialem Spiel", () => {
    const teile = kalibrierteile();
    expect(teile).toHaveLength(10);
    expect(new Set(teile.map((t) => t.id)).size).toBe(10);
    const loch = teile[0].formen[1]; const stift = teile[1].formen[0];
    if (loch.typ === "kreis" && stift.typ === "kreis") expect(loch.r - stift.r).toBeCloseTo(0.1);
  });
  it("verweigert ungültige Druckprofile", () => {
    const p = { id: "p", name: "Test", material: "PLA", bauraum_mm: [180, 200, 220], spiel_mm: 0.2, schubladenspiel_mm: 1, gedruckt: false };
    expect(profilPruefen(p)).toBeNull();
    expect(profilPruefen({ ...p, bauraum_mm: [NaN, 200, 220] })).toMatch(/Bauraum/);
    expect(profilPruefen({ ...p, spiel_mm: 0 })).toMatch(/Passungsspiel/);
  });
});
