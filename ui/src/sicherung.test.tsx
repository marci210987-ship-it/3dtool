import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { leseSicherung, useSicherung } from "./sicherung";
const leer = { format: "cadstudio.projekt", version: 1, name: "Leer", schublade: {}, boxen: [] };
beforeEach(() => { localStorage.clear(); vi.useFakeTimers(); });
afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });
describe("Projektwiederherstellung", () => {
  it("sichert Änderungen, hält laufende Eingaben beim Speichern aber schmutzig", () => {
    const { result, rerender } = renderHook(({ p }) => useSicherung(p, "test.json", true), { initialProps: { p: leer } });
    const neu = { ...leer, name: "Mein Teil" }; rerender({ p: neu });
    act(() => vi.advanceTimersByTime(1100));
    expect(leseSicherung()?.projekt.name).toBe("Mein Teil");
    act(() => result.current.gespeichert(leer));
    expect(result.current.schmutzig).toBe(true);
    expect(leseSicherung()).not.toBeNull();
    act(() => result.current.gespeichert(neu));
    expect(result.current.schmutzig).toBe(false);
    expect(leseSicherung()).toBeNull();
  });
  it("überschreibt keine noch nicht wiederhergestellte Sicherung", () => {
    localStorage.setItem("cadstudio.sicherung.v1", JSON.stringify({ version: 1, zeit: new Date().toISOString(), projekt: { ...leer, name: "Wichtig" }, pfad: "" }));
    const { result, rerender } = renderHook(({ p }) => useSicherung(p, "", true), { initialProps: { p: leer } });
    rerender({ p: { ...leer, name: "Anders" } });
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.rettung?.projekt.name).toBe("Wichtig");
    expect(leseSicherung()?.projekt.name).toBe("Wichtig");
  });
  it("meldet Speicherplatzfehler statt erfolgreichen Schutz zu behaupten", () => {
    const { result, rerender } = renderHook(({ p }) => useSicherung(p, "", true), { initialProps: { p: leer } });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
    rerender({ p: { ...leer, name: "Änderung" } });
    act(() => vi.advanceTimersByTime(1100));
    expect(result.current.hinweis).toMatch(/fehlgeschlagen/);
  });
});
