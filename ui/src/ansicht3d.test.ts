import { describe, expect, it } from "vitest";
import { versaetze } from "./ansicht3d";

describe("3D-Ansicht", () => {
  it("legt mehrere Körper nebeneinander", () => {
    const netze = [{ bbox_mm: [0, 0, 0, 40, 30, 10] }, { bbox_mm: [5, 0, 0, 25, 30, 4] }, { bbox_mm: [0, 0, 0, 10, 10, 10] }];
    expect(versaetze(netze, 10)).toEqual([0, 50 - 5, 50 + 20 + 10]);
  });
  it("ein einzelner Körper bleibt stehen", () => {
    expect(versaetze([{ bbox_mm: [3, 0, 0, 20, 5, 5] }])).toEqual([0]);
    expect(versaetze([])).toEqual([]);
  });
});
