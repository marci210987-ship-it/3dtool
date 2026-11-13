import { describe, expect, it } from "vitest";
import { leseDxf, leseSvg, pfadZuLinienzuegen, vereinfachen, zuFormen } from "./import";
import { formBox } from "./zeichnen";

const svg = (innen: string, kopf = 'width="100mm" height="60mm" viewBox="0 0 100 60"') =>
  `<svg xmlns="http://www.w3.org/2000/svg" ${kopf}>${innen}</svg>`;

describe("SVG-Import", () => {
  it("liest Rechteck mit Eckenradius und ein Kreisloch, y nach oben, Maßstab aus mm", () => {
    const erg = leseSvg(svg('<rect x="0" y="0" width="100" height="60" rx="5"/><circle cx="20" cy="30" r="4"/>'));
    expect(erg.einheitMm).toBeCloseTo(1);
    expect(erg.einheitBekannt).toBe(true);
    expect(erg.konturen).toHaveLength(2);
    const f = zuFormen(erg, erg.einheitMm);
    expect(f.breite).toBe(100);
    expect(f.tiefe).toBe(60);
    expect(f.formen[0]).toMatchObject({ typ: "rechteck", x: 0, y: 0, b: 100, t: 60, radius: 5, loch: false });
    expect(f.formen[1]).toMatchObject({ typ: "kreis", x: 20, y: 30, r: 4, loch: true });
    expect(f.anzahlLoecher).toBe(1);
  });

  it("dreht die y-Achse: Punkte oben im SVG liegen oben im Teil", () => {
    const erg = leseSvg(svg('<circle cx="10" cy="5" r="2"/><circle cx="10" cy="55" r="2"/><rect x="0" y="0" width="100" height="60"/>'));
    const f = zuFormen(erg, 1);
    const kreise = f.formen.filter((x) => x.typ === "kreis") as Array<{ y: number }>;
    expect(kreise.map((k) => k.y).sort((a, b) => a - b)).toEqual([5, 55]);
    // oben im SVG (cy=5) ist oben im Teil (y=55)
    expect(kreise[0].y).toBe(55);
  });

  it("rechnet den Maßstab aus Zoll, Zentimetern und fehlender Größe", () => {
    expect(leseSvg(svg("<rect width='10' height='10'/>", 'width="2in" height="2in" viewBox="0 0 100 100"')).einheitMm).toBeCloseTo(0.508, 4);
    expect(leseSvg(svg("<rect width='10' height='10'/>", 'width="10cm" height="10cm" viewBox="0 0 100 100"')).einheitMm).toBeCloseTo(1, 6);
    const ohne = leseSvg(svg("<rect width='10' height='10'/>", 'viewBox="0 0 100 100"'));
    expect(ohne.einheitBekannt).toBe(false);
    expect(ohne.hinweise.join(" ")).toContain("Annahme");
    // Maßstab frei wählbar
    expect(zuFormen(ohne, 2).breite).toBe(20);
    expect(zuFormen(ohne, 0).formen).toEqual([]);
  });

  it("macht aus einem Pfad mit innenliegender Kontur ein Loch (Gerade-Ungerade-Regel)", () => {
    const erg = leseSvg(svg('<path d="M0 0H40V30H0Z M10 10H30V20H10Z"/>'));
    expect(erg.konturen).toHaveLength(2);
    const f = zuFormen(erg, 1);
    const polygone = f.formen.filter((x) => x.typ === "polygon") as Array<{ loch: boolean; punkte: number[][] }>;
    expect(polygone.map((p) => p.loch).sort()).toEqual([false, true]);
    expect(polygone.every((p) => p.punkte.length === 4)).toBe(true);
    // Insel im Loch ist wieder Material
    const insel = leseSvg(svg('<path d="M0 0H60V60H0Z M10 10H50V50H10Z M20 20H40V40H20Z"/>'));
    expect(zuFormen(insel, 1).formen.map((x) => x.loch)).toEqual([false, true, false]);
  });

  it("zerlegt Bögen und Kurven in Linienzüge", () => {
    const kreis = pfadZuLinienzuegen("M 0 10 A 10 10 0 1 1 20 10 A 10 10 0 1 1 0 10 Z");
    expect(kreis).toHaveLength(1);
    expect(kreis[0].geschlossen).toBe(true);
    expect(kreis[0].punkte.length).toBeGreaterThan(30);
    const xs = kreis[0].punkte.map((p) => p[0]);
    const ys = kreis[0].punkte.map((p) => p[1]);
    expect(Math.max(...xs) - Math.min(...xs)).toBeCloseTo(20, 1);
    expect(Math.max(...ys) - Math.min(...ys)).toBeCloseTo(20, 1);
    // Mittelpunkt (10, 10): alle Punkte liegen 10 mm davon entfernt
    for (const [x, y] of kreis[0].punkte) expect(Math.hypot(x - 10, y - 10)).toBeCloseTo(10, 3);

    const kurve = pfadZuLinienzuegen("M0 0 C 0 20, 20 20, 20 0 Z");
    expect(kurve[0].punkte.length).toBeGreaterThan(10);
    const rel = pfadZuLinienzuegen("m 10 10 l 5 0 l 0 5 h -5 z");
    expect(rel[0].punkte).toEqual([[10, 10], [15, 10], [15, 15], [10, 15]]);
    const quad = pfadZuLinienzuegen("M0 0 Q 10 20 20 0 T 40 0 Z");
    expect(quad[0].punkte.length).toBeGreaterThan(20);
  });

  it("wendet Transformationen an und übernimmt Gruppen", () => {
    const erg = leseSvg(svg('<g transform="translate(10 5)"><rect x="0" y="0" width="20" height="10"/></g>'));
    const f = zuFormen(erg, 1);
    expect(f.formen[0]).toMatchObject({ typ: "rechteck", b: 20, t: 10 });
    const skal = leseSvg(svg('<g transform="scale(2)"><circle cx="5" cy="5" r="3"/></g>'));
    expect(zuFormen(skal, 1).formen[0]).toMatchObject({ typ: "kreis", r: 6 });
    // gedrehtes Rechteck wird zum Vieleck mit vier Ecken
    const gedreht = leseSvg(svg('<rect x="0" y="0" width="20" height="10" transform="rotate(30)"/>'));
    expect(gedreht.konturen[0].typ).toBe("polygon");
    // Ellipse wird zum Vieleck
    expect(leseSvg(svg('<ellipse cx="10" cy="10" rx="8" ry="4"/>')).konturen[0].typ).toBe("polygon");
  });

  it("meldet ungültige Dateien, ignorierten Text und versteckte Elemente", () => {
    expect(leseSvg("das ist kein svg").hinweise[0]).toContain("keine gültige SVG");
    expect(leseSvg("<svg xmlns='http://www.w3.org/2000/svg'><unclosed></svg>").konturen).toEqual([]);
    const text = leseSvg(svg('<text x="0" y="10">Hallo</text><rect width="10" height="10"/><rect width="5" height="5" display="none"/>'));
    expect(text.konturen).toHaveLength(1);
    expect(text.hinweise.join(" ")).toContain("Text");
    expect(leseSvg(svg("")).hinweise.join(" ")).toContain("keine Umrisse");
    const offen = leseSvg(svg('<path d="M0 0 L10 0 L10 10"/>'));
    expect(offen.hinweise.join(" ")).toContain("geschlossen");
    const polylinie = leseSvg(svg('<polyline points="0,0 10,0 10,10"/>'));
    expect(polylinie.konturen).toHaveLength(1);
  });

  it("vereinfacht Linienzüge und begrenzt die Punktzahl", () => {
    // 100 Punkte auf einer Geraden, dazu vier Ecken: bleiben vier
    const punkte: [number, number][] = [];
    for (let i = 0; i < 25; i++) punkte.push([i * 2, 0]);
    for (let i = 0; i < 25; i++) punkte.push([50, i * 2]);
    for (let i = 0; i < 25; i++) punkte.push([50 - i * 2, 50]);
    for (let i = 0; i < 25; i++) punkte.push([0, 50 - i * 2]);
    expect(vereinfachen(punkte, 0.05)).toHaveLength(4);
    expect(vereinfachen(punkte.slice(0, 3), 0.05)).toHaveLength(3);
    const viele = Array.from({ length: 5000 }, (_, i) => {
      const w = (2 * Math.PI * i) / 5000;
      return `${50 + 50 * Math.cos(w)},${50 + 50 * Math.sin(w)}`;
    }).join(" ");
    const f = zuFormen(leseSvg(svg(`<polygon points="${viele}"/>`)), 1);
    const p = f.formen[0] as { punkte: number[][] };
    expect(p.punkte.length).toBeLessThan(2001);
    expect(p.punkte.length).toBeGreaterThan(30);
  });

  it("begrenzt die Zahl der Formen und meldet reine Löcher", () => {
    const viele = Array.from({ length: 205 }, (_, i) => `<rect x="${i * 3}" y="0" width="2" height="2"/>`).join("");
    const f = zuFormen(leseSvg(svg(viele, 'width="700mm" height="10mm" viewBox="0 0 700 10"')), 1);
    expect(f.formen).toHaveLength(200);
    expect(f.hinweise.join(" ")).toContain("höchstens 200");
  });
});

describe("DXF-Import", () => {
  const dxf = (entitaeten: string, kopf = "") =>
    `0\nSECTION\n2\nHEADER\n${kopf}0\nENDSEC\n0\nSECTION\n2\nENTITIES\n${entitaeten}0\nENDSEC\n0\nEOF\n`;
  const lwp = (punkte: string, geschlossen = 1) => `0\nLWPOLYLINE\n90\n4\n70\n${geschlossen}\n${punkte}`;
  const pt = (x: number, y: number, bulge?: number) => `10\n${x}\n20\n${y}\n${bulge ? `42\n${bulge}\n` : ""}`;

  it("liest geschlossene Polylinie und Kreis; y bleibt oben; Einheit aus INSUNITS", () => {
    const text = dxf(lwp(pt(0, 0) + pt(40, 0) + pt(40, 30) + pt(0, 30)) + "0\nCIRCLE\n10\n20\n20\n15\n40\n5\n", "9\n$INSUNITS\n70\n4\n");
    const erg = leseDxf(text);
    expect(erg.einheitBekannt).toBe(true);
    expect(erg.einheitMm).toBe(1);
    const f = zuFormen(erg, 1);
    expect(f.breite).toBe(40);
    expect(f.tiefe).toBe(30);
    expect(f.formen[0]).toMatchObject({ typ: "polygon", loch: false });
    expect(f.formen[1]).toMatchObject({ typ: "kreis", x: 20, y: 15, r: 5, loch: true });
    expect(leseDxf(dxf("", "9\n$INSUNITS\n70\n1\n")).einheitMm).toBe(25.4);
    expect(leseDxf(dxf("")).einheitBekannt).toBe(false);
  });

  it("verkettet einzelne Linien und Bögen zu geschlossenen Konturen", () => {
    const linie = (a: number, b: number, c: number, d: number) => `0\nLINE\n10\n${a}\n20\n${b}\n11\n${c}\n21\n${d}\n`;
    // Quadrat aus vier Linien in gemischter Reihenfolge und Richtung
    const erg = leseDxf(dxf(linie(0, 0, 10, 0) + linie(10, 10, 10, 0) + linie(10, 10, 0, 10) + linie(0, 10, 0, 0) + linie(50, 50, 60, 60)));
    expect(erg.konturen).toHaveLength(1);
    expect(erg.hinweise.join(" ")).toContain("offene");
    const quadrat = erg.konturen[0] as { punkte: number[][] };
    expect(quadrat.punkte).toHaveLength(4);
    // Halbkreis aus ARC und eine Linie
    const bogenText = "0\nARC\n10\n0\n20\n0\n40\n10\n50\n0\n51\n180\n";
    const halb = leseDxf(dxf(bogenText + linie(-10, 0, 10, 0)));
    expect(halb.konturen).toHaveLength(1);
  });

  it("liest Bögen in Polylinien (Bulge) und alte POLYLINE-Entitäten", () => {
    // Halbkreis: Bulge 1 zwischen (0,0) und (10,0), dann zurück als gerade Linie
    const halbkreis = leseDxf(dxf(lwp(pt(0, 0, 1) + pt(10, 0))));
    const p = halbkreis.konturen[0] as { punkte: number[][] };
    expect(p.punkte.length).toBeGreaterThan(20);
    for (const [x, y] of p.punkte) expect(Math.hypot(x - 5, y)).toBeCloseTo(5, 2);
    expect(Math.min(...p.punkte.map((q) => q[1]))).toBeCloseTo(-5, 2); // positiver Bulge: Bogen rechts der Richtung (unter der Sehne)
    const alt = "0\nPOLYLINE\n70\n1\n0\nVERTEX\n10\n0\n20\n0\n0\nVERTEX\n10\n10\n20\n0\n0\nVERTEX\n10\n10\n20\n10\n0\nSEQEND\n";
    expect(leseDxf(dxf(alt)).konturen).toHaveLength(1);
  });

  it("meldet ungültige Dateien und nicht unterstützte Elemente", () => {
    expect(leseDxf("kein dxf").hinweise[0]).toContain("keine gültige");
    expect(leseDxf("0\nSECTION\n2\nENTITIES\n0\nENDSEC\n").konturen).toEqual([]);
    const gemischt = leseDxf(dxf(lwp(pt(0, 0) + pt(5, 0) + pt(5, 5)) + "0\nSPLINE\n0\nTEXT\n0\nINSERT\n"));
    expect(gemischt.hinweise.join(" ")).toContain("Nicht unterstützt");
    expect(gemischt.hinweise.join(" ")).toContain("Splines");
    expect(formBox({ typ: "kreis", x: 0, y: 0, r: 1, loch: false })).toEqual([-1, -1, 1, 1]);
  });
});
