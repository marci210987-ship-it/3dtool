import { expect, test } from "@playwright/test";

test("Kalibrierprojekt: Bedingungen, Wiederherstellung und Druckprofil", async ({ page }) => {
  const fehler: string[] = [];
  page.on("pageerror", (e) => fehler.push(e.message));
  page.on("dialog", (d) => d.accept());
  await page.goto("/");
  await expect(page).toHaveTitle(/CAD Studio/);
  await page.getByRole("button", { name: "Einstellungen", exact: true }).click();
  const panel = page.getByRole("region", { name: "Druckprofile und Kalibrierung" });
  await panel.getByLabel("Profilname", { exact: true }).fill("E2E Drucker 180");
  await panel.getByLabel("Bauraum X (mm)", { exact: true }).fill("180");
  await panel.getByRole("button", { name: "Druckprofil speichern", exact: true }).click();
  await expect(panel.getByRole("status")).toHaveText("Druckprofil gespeichert.");
  await panel.getByRole("button", { name: "Kalibrierprojekt mit fünf Spielmaßen erstellen" }).click();
  await expect(page.getByTestId("zeichnen")).toBeVisible();
  await expect(page.locator(".teileliste li")).toHaveCount(10);
  const bedingungen = page.getByTestId("bedingungen");
  await bedingungen.getByRole("button", { name: "Bedingung hinzufügen" }).click();
  await expect(bedingungen).toContainText("Form 2 → Form 1: mittig");
  // Eine Größenänderung der Platte verschiebt den Lochmittelpunkt automatisch.
  await page.locator(".formliste li button").first().click();
  await page.getByLabel("Breite", { exact: true }).fill("30");
  await page.locator(".formliste li").nth(1).getByRole("button").first().click();
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("15");
  await expect(page.getByRole("status").filter({ hasText: "Wiederherstellungskopie gesichert." })).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Wiederherstellen", exact: true }).click();
  await expect(page.getByTestId("zeichnen")).toBeVisible();
  await expect(page.locator(".teileliste li")).toHaveCount(10);
  await expect(page.getByTestId("bedingungen")).toContainText("mittig");
  await expect(page.locator("vite-error-overlay")).toHaveCount(0);
  expect(fehler).toEqual([]);
});

test("Exportauftrag bleibt sichtbar und lässt sich abbrechen", async ({ page }) => {
  // Der Transport und der UI-Zustandswechsel werden ohne vorhandene FreeCAD-Version geprüft.
  let cancelled = false;
  await page.route("**/api", async (route) => {
    const d = route.request().postDataJSON();
    if (d.cmd === "generate") return route.fulfill({ json: { ok: true, job: "abbruch-test" } });
    if (d.cmd === "cancel") { cancelled = true; return route.fulfill({ json: { ok: true } }); }
    return route.continue();
  });
  await page.route("**/api/job?*", (route) => route.fulfill({ json: { ok: true, status: cancelled ? "abgebrochen" : "laeuft", ergebnis: { ok: false, fehler: ["Export abgebrochen."] } } }));
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await page.getByTestId("vorlage").selectOption("platte");
  await page.getByRole("button", { name: "5. Drucken", exact: true }).click();
  await page.getByTestId("erzeugen").click();
  await page.getByRole("button", { name: "Export abbrechen", exact: true }).click();
  await expect(page.getByTestId("export-fehler")).toContainText("Export abgebrochen.");
  await expect(page.getByRole("button", { name: "Export abbrechen", exact: true })).toHaveCount(0);
  expect(cancelled).toBe(true);
});

test("Abgelehnter Projektwechsel erhält die ungespeicherte Zeichnung", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await page.getByTestId("vorlage").selectOption("platte");
  await page.getByTestId("teil-name").fill("Nicht verlieren");
  await page.getByRole("button", { name: "CAD Studio", exact: true }).click();
  page.once("dialog", (d) => d.dismiss());
  await page.getByTestId("neue-schublade").click();
  await expect(page.getByRole("heading", { name: "Was möchtest du bauen?" })).toBeVisible();
  await expect(page.locator(".app")).toHaveAttribute("data-modus", "zeichnen");
  await page.getByRole("button", { name: "Aktuelles Projekt fortsetzen", exact: true }).click();
  await expect(page.getByTestId("teil-name")).toHaveValue("Nicht verlieren");
});
