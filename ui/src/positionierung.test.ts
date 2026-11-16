import { describe, expect, it } from "vitest";
import { anKante, bauteilRahmen, gleichmaessigVerteilen, konzentrischerKreis, mittelpunktUebernehmen, mitFormIds, positionenAufloesen, positionLoesen, zentrieren } from "./positionierung";
import { einrasten, fangpunkteVon, formBox, formMitte, masseSetzen, verschieben, type Form } from "./zeichnen";

const start = (): Form[] => [
  { typ: "rechteck", x: 30, y: 20, b: 80, t: 40, loch: false },
  { typ: "kreis", x: 38, y: 29, r: 3, loch: true },
];
const patch = (formen: Form[], index: number, werte: object) => formen.map((f, i) => i === index ? { ...f, ...werte } as Form : f);

describe("Parametrische Positionierung", () => {
  it("zentriert mit versetztem Ursprung, getrennt je Achse und ohne Mutation", () => {
    const f = start();
    const x = zentrieren(f, 1, ["x"]);
    expect(formMitte(x[1])).toEqual([70, 29]);
    const xy = zentrieren(x, 1, ["y"]);
    expect(formMitte(xy[1])).toEqual([70, 40]);
    expect(formMitte(f[1])).toEqual([38, 29]);
  });
  it("bleibt bei Breite, Tiefe, Translation und nach JSON-Roundtrip mittig", () => {
    let f = zentrieren(start(), 1);
    f = positionenAufloesen(patch(f, 0, { b: 100, t: 60, x: -20, y: -10 }));
    expect(formMitte(f[1])).toEqual([30, 20]);
    const geladen = JSON.parse(JSON.stringify(f)) as Form[];
    expect(formMitte(positionenAufloesen(patch(geladen, 0, { b: 120 }))[1])).toEqual([40, 20]);
  });
  it("hält die Mitte gebundener Rechtecke bei deren eigener Größenänderung", () => {
    const f = zentrieren([...start(), { typ: "rechteck", x: 0, y: 0, b: 10, t: 10, loch: true }], 2);
    const neu = positionenAufloesen(patch(f, 2, { b: 20, t: 16 }));
    expect(formMitte(neu[2])).toEqual([70, 40]);
  });
  it("löst manuell nur die geänderte Achse", () => {
    let f = zentrieren(start(), 1);
    f[1] = positionLoesen(verschieben(f[1], 5, 0), ["x"]);
    f = positionenAufloesen(patch(f, 0, { b: 120, t: 80 }));
    expect(formMitte(f[1])).toEqual([75, 60]);
    expect(f[1].position?.x).toBeUndefined();
  });
  it.each(["links", "rechts", "unten", "oben"] as const)("setzt echten Randabstand %s und hält ihn nach Durchmesseränderung", seite => {
    let f = anKante(start(), 1, seite, 5);
    f[1] = masseSetzen(f[1], "d", "10")!;
    f = positionenAufloesen(f);
    const b = formBox(f[1]);
    const abstaende = { links: b[0] - 30, rechts: 110 - b[2], unten: b[1] - 20, oben: 60 - b[3] };
    expect(abstaende[seite]).toBe(5);
  });
  it("berechnet Außenrahmen mehrerer versetzter Materialformen ohne Löcher", () => {
    const f: Form[] = [...start(), { typ: "rechteck", x: -30, y: -10, b: 20, t: 15, loch: false }];
    expect(bauteilRahmen(f, 1)).toEqual([-30, -10, 110, 60]);
    expect(formMitte(zentrieren(f, 1)[1])).toEqual([40, 25]);
  });
  it.each([true, false])("erstellt konzentrisch (Loch=%s), folgt auch durch eine Kette", loch => {
    let f = zentrieren(start(), 1);
    f = konzentrischerKreis(f, 1, 14, loch);
    f = konzentrischerKreis(f, 2, 18, false);
    f = positionenAufloesen(patch(f, 0, { b: 120, t: 80 }));
    expect(f.slice(1).map(formMitte)).toEqual([[90, 60], [90, 60], [90, 60]]);
    expect(f[2]).toMatchObject({ r: 7, loch });
    expect(bauteilRahmen(f, 1)).toEqual([30, 20, 150, 100]);
  });
  it("folgt einem manuell verschobenen Bezugskreis", () => {
    let f = konzentrischerKreis(start(), 1, 12, false);
    f[1] = verschieben(f[1], -8, 10);
    f = positionenAufloesen(f);
    expect(formMitte(f[2])).toEqual([30, 39]);
  });
  it("löst gelöschte Quellen, verwechselt neue Formen nicht mit gelöschten IDs", () => {
    const f = konzentrischerKreis(start(), 1, 12, false);
    const neu = positionenAufloesen([f[0], f[2], { typ: "kreis", x: 5, y: 5, r: 1, loch: true }]);
    expect(formMitte(neu[1])).toEqual([38, 29]);
    expect(neu[1].position).toBeUndefined();
    expect(neu[2].form_id).not.toBe(f[1].form_id);
  });
  it("vergibt unabhängige IDs und löst Bindungen an Kopien", () => {
    const f = zentrieren(start(), 1);
    const neu = mitFormIds([...f, verschieben(f[1], 10, 0)]);
    expect(new Set(neu.map(f => f.form_id)).size).toBe(3);
    expect(neu[2].position).toBeUndefined();
  });
  it("verhindert Kreisbezüge beim Mittelpunkt-Übernehmen", () => {
    const f = konzentrischerKreis(start(), 1, 10, true);
    expect(mittelpunktUebernehmen(f, 1, 2)).toBe(f);
    expect(mittelpunktUebernehmen(f, 1, 1)).toBe(f);
  });
  it("verarbeitet beschädigte Kreisbezüge ohne Rekursion oder Positionssprung", () => {
    const f = mitFormIds(start());
    f[0].position = { x: { quelle: f[1].form_id!, lage: "mitte" } };
    f[1].position = { x: { quelle: f[0].form_id!, lage: "mitte" } };
    expect(positionenAufloesen(f).map(formMitte)).toEqual(f.map(formMitte));
  });
  it("übernimmt den Mittelpunkt einer beliebigen Form", () => {
    expect(formMitte(mittelpunktUebernehmen(start(), 1, 0)[1])).toEqual([70, 40]);
  });
  it("verteilt unsortierte Mehrfachauswahl gleichmäßig und hält Endpunkte fest", () => {
    const f: Form[] = [0, 8, 40, 90].map(x => ({ typ: "kreis", x, y: 5, r: 1, loch: true }));
    const neu = gleichmaessigVerteilen(f, [3, 1, 0, 2, 1], "x");
    expect(neu.map(formMitte)).toEqual([[0, 5], [30, 5], [60, 5], [90, 5]]);
    expect(gleichmaessigVerteilen(f, [0, 1], "x")).toBe(f);
  });
  it("prüft ungültige Maße, fehlenden Bauteilrahmen und Formenlimit", () => {
    const f = start();
    for (const d of [NaN, Infinity, 0, -1, 0.1]) expect(konzentrischerKreis(f, 1, d, true)).toBe(f);
    expect(konzentrischerKreis(f, 0, 10, true)).toBe(f);
    expect(anKante(f, 1, "links", -1)).toBe(f);
    expect(zentrieren([f[1]], 0)).toEqual([f[1]]);
    const voll = Array.from({ length: 200 }, () => f[1]);
    expect(konzentrischerKreis(voll, 0, 10, true)).toBe(voll);
  });
  it("erkennt echte Kreis-, Polygon- und gedrehte Kantenmittelpunkte", () => {
    expect(fangpunkteVon(start()[1])).toHaveLength(5);
    const p: Form = { typ: "polygon", punkte: [[10, 10], [30, 20], [10, 30]], loch: false };
    expect(fangpunkteVon(p)).toContainEqual([20, 15]);
    const r: Form = { typ: "rechteck", x: 0, y: 0, b: 20, t: 10, winkel: 90, loch: false };
    expect(fangpunkteVon(r)).toContainEqual([15, 5]);
    expect(einrasten([19.7, 15.2], fangpunkteVon(p), 1).punkt).toEqual([20, 15]);
  });
});

it("verteilt vertikal und lässt die x-Bindung bestehen", () => {
  let f: Form[] = [...start(), { typ: "kreis", x: 50, y: 35, r: 2, loch: true }, { typ: "kreis", x: 50, y: 59, r: 2, loch: true }];
  f = zentrieren(f, 2, ["x"]);
  const neu = gleichmaessigVerteilen(f, [1, 2, 3], "y");
  expect(formMitte(neu[2])).toEqual([70, 44]);
  expect(neu[2].position?.x?.quelle).toBe("teil");
});
