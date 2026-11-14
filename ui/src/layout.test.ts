import { describe, expect, it } from "vitest";
import { Box, boxBeschriftung, dupliziere, footprint, kollisionen, neueBox, ueberlappt, KATALOG } from "./layout";

function box(teil: Partial<Box> & Pick<Box, "id" | "x" | "y" | "ex" | "ey">): Box {
  return {
    name: teil.id,
    ez: 3,
    rotation: 0,
    fachX: 1,
    fachY: 1,
    stapellippe: true,
    deckel: false,
    herausnehmbar: false,
    kabelkerben: false,
    art: "raster",
    ...teil,
  };
}

describe("Editor-Layout", () => {
  it("dreht um 90 Grad und erkennt Überlappung", () => {
    const lang = box({ id: "B3", x: 5, y: 0, ex: 1, ey: 3, rotation: 90 });
    expect(footprint(lang)).toEqual([5, 0, 3, 1]);
    const a = box({ id: "B2", x: 0, y: 4, ex: 2, ey: 2 });
    const b = box({ id: "B4", x: 0, y: 4, ex: 2, ey: 3 });
    expect(ueberlappt(a, b)).toBe(true);
    expect(kollisionen([a, b])).toHaveLength(1);
    expect(ueberlappt(a, box({ id: "B1", x: 2, y: 4, ex: 2, ey: 2 }))).toBe(false);
  });

  it("legt vier verschiedene Boxen ohne Kollision", () => {
    let boxen: Box[] = [];
    for (const id of ["klein", "mittel", "besteckfach", "gross"]) {
      const vorlage = KATALOG.find((e) => e.id === id)!;
      const neu = neueBox(vorlage, boxen, 11, 9);
      expect(neu).not.toBeNull();
      boxen = [...boxen, neu!];
    }
    expect(kollisionen(boxen)).toEqual([]);
    expect(new Set(boxen.map((b) => `${b.ex}x${b.ey}`)).size).toBe(4);
    const gross = boxen.find((b) => b.ex === 2 && b.ey === 3)!;
    expect(boxBeschriftung(gross)).toBe("Große Box 2×3");
    expect(boxBeschriftung({ ...gross, name: "Große Box B-b74abcd", rotation: 90 })).toBe("Große Box 3×2");
  });

  it("dupliziert auf ein freies Nachbarfeld", () => {
    const original = box({ id: "B1", x: 0, y: 0, ex: 2, ey: 2 });
    const kopie = dupliziere(original, [original], 11, 9);
    expect(kopie.id).toBe("B2");
    expect(ueberlappt(original, kopie)).toBe(false);
  });
});
