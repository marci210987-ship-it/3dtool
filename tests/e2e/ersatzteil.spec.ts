import { expect, test } from "@playwright/test";

test("Ersatzteil: Kabelclip wählen, ungültigen Durchmesser ablehnen", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("in Vorbereitung")).toHaveCount(2);
  await page.getByRole("button", { name: /Ersatzteile/ }).click();
  await expect(page.getByTestId("ersatz-kabelclip")).toBeVisible();
  await expect(page.getByTestId("feld-durchmesser_mm")).toHaveValue("6");
  await expect(page.getByTestId("vorschau-art")).toContainText("Vereinfachte Vorschau");
  await page.getByTestId("feld-durchmesser_mm").fill("0");
  await expect(page.getByTestId("ersatz-fehler")).toContainText("außerhalb");
  await expect(page.getByTestId("ersatz-erzeugen")).toBeDisabled();
  await page.getByTestId("feld-durchmesser_mm").fill("10");
  await expect(page.getByTestId("ersatz-fehler")).toHaveCount(0);
  await expect(page.getByTestId("ersatz-mass")).toContainText("mm");

  await page.getByRole("button", { name: "CAD Studio" }).click();
  await page.getByRole("button", { name: /Schubladen-Konfigurator/ }).click();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "schublade");
});
