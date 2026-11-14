import { expect, test } from "@playwright/test";

test("Elektronikgehäuse: Wand ablehnen und zurück zur Schublade", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("in Vorbereitung")).toHaveCount(0);
  await page.getByRole("button", { name: /Elektronikgehäuse/ }).click();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "gehaeuse");
  await expect(page.getByTestId("feld-innen_b_mm")).toBeVisible();
  await expect(page.getByTestId("gehaeuse-mass")).toContainText("mm");
  await expect(page.getByTestId("vorschau-art")).toContainText("Vereinfachte Vorschau");

  await page.getByTestId("feld-wand_mm").fill("0.4");
  await expect(page.getByTestId("gehaeuse-fehler")).toContainText("außerhalb");
  await expect(page.getByTestId("gehaeuse-erzeugen")).toBeDisabled();
  await page.getByTestId("feld-wand_mm").fill("1.6");
  await expect(page.getByTestId("gehaeuse-fehler")).toHaveCount(0);

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Neue Schublade/ }).click();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "schublade");
});
