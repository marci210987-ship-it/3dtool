import { expect, test } from "@playwright/test";
import path from "node:path";

const BILDER = path.join("test-results", "design");

test.use({ viewport: { width: 1440, height: 900 } });

test("Oberfläche in den sechs Bereichen", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "CAD Studio" })).toBeVisible();
  await expect(page.locator(".wortmarke")).toBeVisible();
  await page.screenshot({ path: path.join(BILDER, "startseite.png") });

  await page.getByTestId("neue-schublade").click();
  await page.getByTestId("breite").fill("480");
  await page.getByTestId("tiefe").fill("420");
  await page.getByTestId("raster-berechnen").click();
  await expect(page.getByText("11 × 9 Felder")).toBeVisible();
  await page.getByRole("button", { name: "Boxen platzieren" }).click();
  await page.getByTestId("katalog-klein").click();
  await page.getByTestId("katalog-mittel").click();
  await page.getByTestId("katalog-gross").click();
  await expect(page.getByTestId("box-B3")).toContainText("Große Box");
  await expect(page.getByTestId("box-B3")).toContainText("2×3");
  await page.screenshot({ path: path.join(BILDER, "schublade-boxen.png") });

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await expect(page.getByTestId("zeichnen")).toBeVisible();
  await page.screenshot({ path: path.join(BILDER, "eigene-teile.png") });

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Ersatzteile/ }).click();
  await expect(page.getByTestId("ersatz-kabelclip")).toBeVisible();
  await page.screenshot({ path: path.join(BILDER, "ersatzteile.png") });

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Kabelmanagement/ }).click();
  await expect(page.getByTestId("kabel-kanal")).toBeVisible();
  await page.screenshot({ path: path.join(BILDER, "kabelmanagement.png") });

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Elektronikgehäuse/ }).click();
  await expect(page.getByTestId("gehaeuse-mass")).toContainText("mm");
  await page.screenshot({ path: path.join(BILDER, "elektronikgehaeuse.png") });
});
