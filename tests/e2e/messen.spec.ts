import { expect, test } from "@playwright/test";
import { BoxGeometry } from "three";

// Definiertes Dreiecksnetz: prüft WebGL, Trefferermittlung und Scrollen auch ohne
// lokale FreeCAD-Installation. Der bestehende FreeCAD-Test prüft zusätzlich den Exportpfad.
test("3D-Messpunkte treffen nach dem Scrollen zu den Werkzeugen das Modell", async ({ page }) => {
  const fehler: string[] = [];
  page.on("pageerror", (e) => fehler.push(e.message));
  const geo = new BoxGeometry(60, 40, 25);
  geo.translate(40, 30, 12.5);
  const netz = {
    teil: "E1", name: "Messplatte", punkte: Array.from(geo.attributes.position.array),
    dreiecke: Array.from(geo.index!.array), bbox_mm: [10, 10, 0, 70, 50, 25], volumen_mm3: 60000,
  };
  geo.dispose();
  await page.route("**/api", async (route) => {
    if (route.request().postDataJSON().cmd !== "vorschau") return route.continue();
    await route.fulfill({ json: { ok: true, result: { ok: true, netze: [netz], hinweise: [], teile_gesamt: 1, teile_gezeigt: 1 } } });
  });
  await page.goto("/");
  await expect(page).toHaveTitle("CAD Studio");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await page.getByTestId("vorlage").selectOption("platte");
  await expect(page.getByTestId("ansicht3d-info")).toContainText("60 × 40 × 25 mm");
  await page.getByTestId("ausrichtung").locator("summary").click();
  await page.getByTestId("schnitt-achse").selectOption("z");
  await expect(page.getByTestId("schnitt-mm")).toContainText("12.5 mm");
  await page.getByTestId("schnitt-umkehren").click();
  await page.getByTestId("schnitt-achse").selectOption("aus");
  await page.getByTestId("messen-an").check();

  const canvas = page.getByTestId("ansicht3d-buehne").locator("canvas");
  // Erzwingt die ursprüngliche Situation: Die Werkzeuge bleiben sichtbar, während
  // die Bühnenmitte außerhalb des Fensters liegt. Locator-Klicks müssen zurückscrollen.
  await page.getByTestId("messen-info").evaluate((el) => el.scrollIntoView({ block: "start" }));
  const vorher = (await canvas.boundingBox())!;
  expect(vorher.y + vorher.height / 2).toBeLessThan(0);
  await canvas.click({ position: { x: vorher.width / 2 - 15, y: vorher.height / 2 } });
  await expect(page.getByTestId("messen-info")).toContainText("Punkt 1");
  await canvas.click({ position: { x: vorher.width / 2 + 15, y: vorher.height / 2 } });
  await expect(page.getByTestId("messen-info")).toContainText("Abstand");
  await expect(page.getByTestId("messen-info")).not.toContainText("NaN");
  await page.getByTestId("messen-loeschen").click();
  await expect(page.getByTestId("messen-info")).toContainText("Zwei Punkte");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(fehler).toEqual([]);
});
