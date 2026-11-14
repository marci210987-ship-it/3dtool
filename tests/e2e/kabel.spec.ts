import { expect, test } from "@playwright/test";

test("Kabelkanal: ungültige Wand, fremdes Profil, zurück zur Schublade", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("in Vorbereitung")).toHaveCount(1);
  await page.getByRole("button", { name: /Kabelmanagement/ }).click();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "kabel");
  await expect(page.getByTestId("kabel-kanal")).toBeVisible();
  await expect(page.getByTestId("kabel-mass")).toContainText("mm");
  await expect(page.getByTestId("vorschau-art")).toContainText("Vereinfachte Vorschau");

  await page.getByTestId("feld-wand_mm").fill("0.4");
  await expect(page.getByTestId("kabel-fehler")).toContainText("außerhalb");
  await expect(page.getByTestId("kabel-erzeugen")).toBeDisabled();
  await page.getByTestId("feld-wand_mm").fill("1.6");
  await expect(page.getByTestId("kabel-fehler")).toHaveCount(0);

  await page.getByTestId("kabel-ecke").click();
  await page.getByTestId("feld-innenbreite_mm").fill("40");
  await expect(page.getByTestId("kabel-passung")).toContainText("passen nicht");
  await expect(page.getByTestId("kabel-erzeugen")).toBeDisabled();
  await page.getByTestId("kabel-angleichen").click();
  await expect(page.getByTestId("kabel-passung")).toHaveCount(0);

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Neue Schublade/ }).click();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "schublade");
});
