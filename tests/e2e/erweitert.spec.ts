import { expect, type Locator, type Page, test } from "@playwright/test";

const MIT_FREECAD = Boolean(process.env.FREECADCMD);

async function blattKoordinaten(blatt: Locator) {
  await blatt.evaluate((el) => el.scrollIntoView({ block: "center" }));
  const box = await blatt.boundingBox();
  const viewBox = (await blatt.getAttribute("viewBox"))!.split(" ").map(Number);
  if (!box) throw new Error("Zeichenblatt nicht sichtbar");
  const seite = Math.min(box.width, box.height);
  const links = box.x + (box.width - seite) / 2;
  const oben = box.y + (box.height - seite) / 2;
  const mass = seite / viewBox[2];
  return (xMm: number, yMm: number) => ({ x: links + xMm * mass, y: oben + seite - yMm * mass });
}

async function ziehen(page: Page, von: { x: number; y: number }, nach: { x: number; y: number }) {
  await page.mouse.move(von.x, von.y);
  await page.mouse.down();
  await page.mouse.move((von.x + nach.x) / 2, (von.y + nach.y) / 2, { steps: 3 });
  await page.mouse.move(nach.x, nach.y, { steps: 3 });
  await page.mouse.up();
}

async function oeffnen(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await expect(page.getByTestId("zeichnen")).toBeVisible();
}

async function platte(page: Page) {
  const blatt = page.getByTestId("zeichenblatt");
  const mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(10, 10), mm(70, 50));
  await expect(page.locator(".formliste li")).toHaveCount(1);
}

test("Langloch, Text und Senkung zeichnen", async ({ page }) => {
  await oeffnen(page);
  await platte(page);
  const blatt = page.getByTestId("zeichenblatt");

  // Langloch als Loch
  await page.getByTestId("loch-modus").check();
  await page.getByTestId("werkzeug-langloch").click();
  await page.getByTestId("langloch-breite").fill("6");
  let mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(20, 30), mm(40, 30));
  await expect(page.locator(".formliste li button", { hasText: "Langloch" })).toBeVisible();

  // Rundes Loch mit Senkung
  await page.getByTestId("werkzeug-kreis").click();
  mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(55, 30), mm(57, 30));
  await page.getByTestId("loch-modus").uncheck();
  await page.locator(".formliste li button", { hasText: "Kreis" }).first().click();
  await page.getByTestId("senk-art").selectOption("senkung");
  await expect(page.getByTestId("senk-ring")).toBeVisible();
  await expect(page.getByTestId("senk-tiefe-info")).toContainText("mm");
  await page.getByTestId("senk-art").selectOption("sechskant");
  await expect(page.getByTestId("senk-t")).toBeVisible();
  await expect(page.getByTestId("senk-ring")).toBeVisible();

  // Text erhaben
  await page.getByTestId("werkzeug-text").click();
  await page.getByTestId("text-neu").fill("M3");
  await page.getByTestId("text-neu-hoehe").fill("5");
  mm = await blattKoordinaten(blatt);
  await page.mouse.click(mm(12, 42).x, mm(12, 42).y);
  await expect(page.locator(".formliste li button", { hasText: "Text „M3“" })).toBeVisible();
  await expect(page.getByTestId("text-panel")).toBeVisible();
  await page.getByTestId("text-inhalt").fill("A1");
  await expect(page.locator(".formliste li button", { hasText: "Text „A1“" })).toBeVisible();
});

test("Gruppe wählen, gemeinsam verschieben, kopieren und spiegeln", async ({ page }) => {
  await oeffnen(page);
  const blatt = page.getByTestId("zeichenblatt");
  let mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(10, 10), mm(30, 30));
  mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(50, 10), mm(70, 30));
  await expect(page.locator(".formliste li")).toHaveCount(2);

  await page.getByTestId("werkzeug-wahl").click();
  await page.getByTestId("form-0").click({ position: { x: 10, y: 10 } });
  await page.getByTestId("form-1").click({ position: { x: 10, y: 10 }, modifiers: ["Shift"] });
  await expect(page.getByTestId("gruppe-panel")).toContainText("2 Formen");
  await expect(page.getByTestId("gruppe-markierung")).toBeVisible();

  const vorher = await page.getByTestId("teil-mass").textContent();
  await page.getByTestId("gruppe-kopieren").click();
  await expect(page.locator(".formliste li")).toHaveCount(4);
  await expect(page.getByTestId("teil-mass")).not.toHaveText(vorher ?? "");

  await page.getByTestId("gruppe-spiegel-x").click();
  await expect(page.locator(".formliste li")).toHaveCount(4);
  await page.getByTestId("gruppe-loeschen").click();
  await expect(page.locator(".formliste li")).toHaveCount(2);
});

test("Seitenloch und Drehteil bedienen", async ({ page }) => {
  await oeffnen(page);
  await platte(page);
  await page.getByTestId("seitenloch-neu").click();
  await expect(page.getByTestId("seitenloch-0")).toBeVisible();
  await page.getByTestId("sl-art-0").selectOption("schlitz");
  await expect(page.getByTestId("sl-b-0")).toBeVisible();
  await page.getByTestId("sl-loeschen-0").click();
  await expect(page.getByTestId("seitenloch-0")).toHaveCount(0);

  await page.getByTestId("profil-knopf").click();
  await expect(page.getByTestId("profil-umriss")).toBeVisible();
  await expect(page.getByTestId("profil-r-0")).toBeVisible();
  await page.getByTestId("profil-entfernen").click();
  await expect(page.getByTestId("profil-umriss")).toHaveCount(0);
});

test("Export: Drehteil mit Text, Senkung und Seitenloch", async ({ page }) => {
  test.skip(!MIT_FREECAD, "FREECADCMD nicht gesetzt");
  await oeffnen(page);
  await page.getByTestId("profil-knopf").click();
  await page.getByTestId("seitenloch-neu").click();
  await page.getByTestId("sl-z-0").fill("5");
  await page.getByRole("button", { name: "5. Drucken" }).click();
  await page.getByTestId("erzeugen").click();
  await expect(page.getByTestId("export-erfolg")).toBeVisible({ timeout: 120000 });
});

test("3D-Ansicht zeigt die echte Geometrie beim Zeichnen", async ({ page }) => {
  test.skip(!MIT_FREECAD, "FREECADCMD nicht gesetzt");
  await oeffnen(page);
  await platte(page);
  const info = page.getByTestId("ansicht3d-info");
  await expect(info).toContainText("60 × 40 × 10 mm", { timeout: 60000 });
  // Eine Änderung rechnet neu: Teilhöhe 25
  await page.getByLabel("Standardhöhe (mm)").fill("25");
  await expect(info).toContainText("× 25 mm", { timeout: 60000 });
  await expect(page.getByTestId("ansicht3d-buehne").locator("canvas")).toBeVisible();
  // Ungültige Eingabe: die Meldung steht statt eines Körpers
  await page.getByLabel("Standardhöhe (mm)").fill("0");
  await expect(page.getByTestId("ansicht3d-fehler")).toBeVisible({ timeout: 60000 });
});

test("Wunschliste: Seite links und rechts", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("neue-schublade").click();
  await page.getByTestId("breite").fill("480");
  await page.getByTestId("tiefe").fill("420");
  await page.getByTestId("raster-berechnen").click();
  await page.getByRole("button", { name: "Boxen platzieren" }).click();
  await page.locator('[data-testid="wunschliste"] summary').click();
  await page.getByTestId("wunsch-besteckfach").fill("1");
  await page.getByTestId("wunsch-kabel").fill("1");
  await page.getByTestId("wunsch-seite-besteckfach").selectOption("rechts");
  await page.getByTestId("wunsch-seite-kabel").selectOption("links");
  await page.getByTestId("wunsch-rest").uncheck();
  await page.getByTestId("wuensche-platzieren").click();
  await expect(page.getByTestId("meldung")).toContainText("2 Boxen ergänzt");
  const boxen = page.locator(".box");
  await expect(boxen).toHaveCount(2);
  const lagen = await boxen.evaluateAll((els) => els.map((e) => ({ text: e.textContent ?? "", x: e.getBoundingClientRect().x })));
  const kabel = lagen.find((l) => l.text.includes("Kabel"))!;
  const fach = lagen.find((l) => l.text.includes("Besteck"))!;
  expect(kabel.x).toBeLessThan(fach.x);
});
