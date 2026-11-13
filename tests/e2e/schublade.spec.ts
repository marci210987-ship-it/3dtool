import { expect, test } from "@playwright/test";
import path from "node:path";

const PROJEKT = "/tmp/cadstudio-e2e/kueche.cadstudio.json";
const BILDER = "/opt/cursor/artifacts";

test("Schublade anlegen, prüfen, speichern, neu öffnen, erzeugen", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Schubladen-Konfigurator")).toBeVisible();
  await expect(page.getByText("in Vorbereitung")).toHaveCount(3);
  await page.screenshot({ path: path.join(BILDER, "startseite.png"), fullPage: true });

  await page.getByTestId("neue-schublade").click();
  await page.getByTestId("name").fill("Kuechenschublade");
  await page.getByTestId("breite").fill("480");
  await page.getByTestId("tiefe").fill("420");
  await page.getByTestId("hoehe-schublade").fill("80");
  await page.getByTestId("spiel").fill("1");
  await page.getByTestId("verbinder").fill("0.2");
  await page.getByTestId("raster-berechnen").click();

  await expect(page.getByText("11 × 9 Felder")).toBeVisible();
  await expect(page.getByText("P1")).toBeVisible();
  await expect(page.getByText("P4")).toBeVisible();
  await expect(page.getByText("passt aufs Druckbett").first()).toBeVisible();

  await page.getByRole("button", { name: "Boxen platzieren" }).click();
  await page.getByTestId("katalog-klein").click();
  await page.getByTestId("katalog-mittel").click();
  await page.getByTestId("katalog-besteckfach").click();
  await page.getByTestId("katalog-gross").click();
  await expect(page.getByTestId("box-B1")).toBeVisible();
  await expect(page.getByTestId("box-B4")).toBeVisible();
  await expect(page.getByTestId("ueberlappung")).toHaveCount(0);

  await page.getByTestId("box-B1").click();
  await page.getByTestId("hinten").click();
  await page.getByTestId("box-B4").click();
  await page.getByTestId("drehen").click();
  await page.getByTestId("links").click();
  await page.getByTestId("links").click();
  await expect(page.getByTestId("ueberlappung")).toBeVisible();
  await page.screenshot({ path: path.join(BILDER, "editor-ueberlappung.png"), fullPage: true });

  await page.getByRole("button", { name: "4. Drucken" }).click();
  await expect(page.getByTestId("erzeugen")).toBeDisabled();
  await expect(page.getByTestId("export-gesperrt")).toBeVisible();

  await page.getByRole("button", { name: "3. Boxen" }).click();
  await page.getByTestId("box-B4").click();
  await page.getByTestId("rechts").click();
  await page.getByTestId("rechts").click();
  await expect(page.getByTestId("ueberlappung")).toHaveCount(0);
  await page.getByTestId("hoehe").fill("4");
  await expect(page.getByTestId("vorschau-art")).toContainText("Vereinfachte Vorschau");

  await page.getByRole("button", { name: "4. Drucken" }).click();
  await expect(page.getByTestId("erzeugen")).toBeEnabled();
  await page.getByTestId("speicherpfad").fill(PROJEKT);
  await page.getByTestId("speichern").click();
  await expect(page.getByTestId("meldung")).toContainText("Gespeichert");

  await page.reload();
  await page.getByRole("button", { name: /Kuechenschublade/ }).click();
  await expect(page.getByTestId("breite")).toHaveValue("480");
  await expect(page.getByTestId("tiefe")).toHaveValue("420");
  await page.getByRole("button", { name: "3. Boxen" }).click();
  await expect(page.getByTestId("box-B1")).toBeVisible();
  await expect(page.getByTestId("box-B4")).toBeVisible();
  await page.getByTestId("box-B4").click();
  await expect(page.getByTestId("hoehe")).toHaveValue("4");

  await page.getByRole("button", { name: "4. Drucken" }).click();
  await page.getByTestId("erzeugen").click();
  await expect(page.getByTestId("export-erfolg")).toBeVisible({ timeout: 120000 });
  await expect(page.getByTestId("vorschau-art").last()).toContainText("STL");
  await page.screenshot({ path: path.join(BILDER, "export-erfolg.png"), fullPage: true });
});
