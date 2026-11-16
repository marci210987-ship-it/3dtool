import { expect, type Locator, type Page, test } from "@playwright/test";

const MIT_FREECAD = Boolean(process.env.FREECADCMD);

/** Rechnet Millimeter im Zeichenblatt in Bildschirmkoordinaten um (das Blatt ist quadratisch eingepasst). */
async function blattKoordinaten(blatt: Locator) {
  // Das Blatt ragt im Standardfenster über den unteren Rand: erst vollständig ins Bild scrollen
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

async function eigeneTeileOeffnen(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await expect(page.getByTestId("zeichnen")).toBeVisible();
}

// Die Abläufe wechseln bewusst das Projekt und bestätigen den Schutz ungespeicherter Änderungen.
test.beforeEach(async ({ page }) => { page.on("dialog", (dialog) => dialog.accept()); });

test("Zeichnen: Rechteck und Loch ziehen, Maß per Eingabe ändern, Rückgängig", async ({ page }) => {
  await eigeneTeileOeffnen(page);
  const blatt = page.getByTestId("zeichenblatt");

  // Rechteck 60 × 40 mm (Raster 1 mm, Einrasten rastet am Ursprung nicht, weil noch keine Form existiert)
  let mm = await blattKoordinaten(blatt);
  await ziehen(page, mm(10, 10), mm(70, 50));
  await expect(page.getByTestId("teil-mass")).toContainText("Außenmaß 60 × 40 × 10 mm");

  // Kreisloch in der Mitte: rastet an der Plattenmitte (40 / 30) ein
  await page.getByTestId("loch-modus").check();
  await page.getByTestId("werkzeug-kreis").click();
  mm = await blattKoordinaten(blatt); // die Seite kann sich nach dem ersten Ziehen verschoben haben
  await ziehen(page, mm(41, 31), mm(45, 31));
  await expect(page.locator(".formliste li")).toHaveCount(2);
  await page.locator(".formliste li button", { hasText: "Kreis" }).first().click();
  await expect(page.getByLabel("Mitte x", { exact: false }).first()).toHaveValue("40");
  await expect(page.getByLabel("Mitte y", { exact: false }).first()).toHaveValue("30");

  // Maß der Platte per Eingabe ändern
  await page.getByTestId("masse-b").click();
  const eingabe = page.getByTestId("masse-eingabe");
  await expect(eingabe).toBeFocused();
  await eingabe.fill("80");
  await eingabe.press("Enter");
  await expect(page.getByTestId("teil-mass")).toContainText("Außenmaß 80 × 40 × 10 mm");

  // Rückgängig nimmt die Änderung zurück
  await page.getByTestId("rueckgaengig").click();
  await expect(page.getByTestId("teil-mass")).toContainText("Außenmaß 60 × 40 × 10 mm");
});

test("Zeichnen: Vorlage, eigene Vorlage speichern und wiederfinden, SVG-Import", async ({ page }) => {
  await eigeneTeileOeffnen(page);
  await page.getByTestId("vorlage").selectOption("stufe");
  await expect(page.getByTestId("teil-mass")).toContainText("Außenmaß 60 × 40 × 12 mm");

  const name = "E2E Stufenblock " + Date.now();
  await page.getByTestId("vorlage-name").fill(name);
  await page.getByTestId("vorlage-sichern").click();
  await expect(page.getByTestId("vorlage-meldung")).toContainText("gespeichert");

  // Nach dem Neuladen liegt die Vorlage noch im Programmordner
  await page.reload();
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await expect(page.getByTestId("vorlage").locator("option", { hasText: name })).toHaveCount(1);
  await page.getByTestId("vorlage").selectOption({ label: name });
  await expect(page.getByTestId("teil-name")).toHaveValue(name);

  // aufräumen
  await page.locator(".meine-vorlagen summary").click();
  await page.locator('[data-testid^="vorlage-loeschen-"]').first().click();
  await expect(page.getByTestId("vorlage").locator("option", { hasText: name })).toHaveCount(0);

  // SVG-Import: Rechteck mit Radius, Kreisloch, Langloch aus Bögen
  const svg =
    '<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="50mm" viewBox="0 0 90 50">' +
    '<rect x="0" y="0" width="90" height="50" rx="6"/><circle cx="12" cy="25" r="3.5"/>' +
    '<path d="M 35 20 H 65 A 5 5 0 0 1 65 30 H 35 A 5 5 0 0 1 35 20 Z"/></svg>';
  await page.getByTestId("import-datei").setInputFiles({ name: "Deckel.svg", mimeType: "image/svg+xml", buffer: Buffer.from(svg) });
  await expect(page.getByTestId("import-vorschau")).toContainText("3 Formen, davon 2 Löcher, 90 × 50 mm");
  await page.getByTestId("import-hoehe").fill("6");
  await page.getByTestId("import-einfuegen").click();
  await expect(page.getByTestId("teil-name")).toHaveValue("Deckel");
  await expect(page.getByTestId("teil-mass")).toContainText("Außenmaß 90 × 50 × 6 mm");
});

test("Zeichnen: Muster und Ausrichten", async ({ page }) => {
  await eigeneTeileOeffnen(page);
  await page.getByTestId("vorlage").selectOption("platte");
  await page.locator(".teileliste li button", { hasText: "Platte mit Bohrungen" }).click();
  // erste Bohrung wählen, ein Gitter von 3 Spalten daraus erzeugen
  await page.locator(".formliste li button", { hasText: "Kreis" }).first().click();
  await page.locator(".muster summary").click();
  const vorher = await page.locator(".formliste li").count();
  await page.getByTestId("muster-gitter").click();
  await expect(page.locator(".formliste li")).toHaveCount(vorher + 2);
  // Ausrichten: Mitte der Platte
  await page.getByTestId("ausrichten-mitte-x").click();
  await expect(page.getByTestId("muster-meldung")).toContainText("Formen");
});

test("Schublade: Wunschliste platzieren und Füllstil", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("neue-schublade").click();
  await page.getByTestId("breite").fill("480");
  await page.getByTestId("tiefe").fill("420");
  await page.getByTestId("raster-berechnen").click();
  await page.getByRole("button", { name: "Boxen platzieren" }).click();

  await page.locator('[data-testid="wunschliste"] summary').click();
  await page.getByTestId("wunsch-kabel").fill("1");
  await page.getByTestId("wunsch-besteckfach").fill("2");
  await page.getByTestId("wunsch-klein").fill("3");
  await page.getByTestId("wunsch-rest").uncheck();
  await page.getByTestId("wuensche-platzieren").click();
  await expect(page.getByTestId("meldung")).toContainText("6 Boxen ergänzt");
  await expect(page.locator(".box")).toHaveCount(6);
  await expect(page.getByTestId("ueberlappung")).toHaveCount(0);

  // Rest füllen mit einheitlicher Größe
  await page.getByTestId("fuellstil").selectOption("einheitlich");
  await page.getByTestId("auto-fuellen").click();
  await expect(page.getByTestId("meldung")).toContainText("Boxen ergänzt");
  expect(await page.locator(".box").count()).toBeGreaterThan(6);
  await expect(page.getByTestId("ueberlappung")).toHaveCount(0);

  await page.getByRole("button", { name: "5. Drucken" }).click();
  await expect(page.getByTestId("erzeugen")).toBeEnabled();
});

test("Export eigener Teile mit FreeCAD", async ({ page }) => {
  test.skip(!MIT_FREECAD, "FREECADCMD nicht gesetzt");
  await eigeneTeileOeffnen(page);
  await page.getByTestId("vorlage").selectOption("senkung");
  await page.getByRole("button", { name: "5. Drucken" }).click();
  await page.getByTestId("erzeugen").click();
  await expect(page.getByTestId("export-erfolg")).toBeVisible({ timeout: 120000 });
});

async function aussenmass(page: Page): Promise<number[]> {
  const text = (await page.getByTestId("teil-mass").textContent()) ?? "";
  const m = text.match(/Außenmaß ([\d.]+) × ([\d.]+)/);
  return m ? [Number(m[1]), Number(m[2])] : [0, 0];
}

test("Zeichnen: Vieleck-Punkte ziehen, einfügen und löschen", async ({ page }) => {
  await eigeneTeileOeffnen(page);
  const blatt = page.getByTestId("zeichenblatt");
  let mm = await blattKoordinaten(blatt);

  // Dreieck (10/10, 70/10, 10/50) per Klick, Enter schließt
  await page.getByTestId("werkzeug-polygon").click();
  mm = await blattKoordinaten(blatt); // die Hilfezeile ändert mit dem Werkzeug ihre Höhe
  for (const [x, y] of [[10, 10], [70, 10], [10, 50]]) await page.mouse.click(mm(x, y).x, mm(x, y).y);
  await page.keyboard.press("Enter");
  await expect(page.locator(".formliste li")).toHaveCount(1);
  await expect.poll(() => aussenmass(page)).toEqual([expect.closeTo(60, -1), expect.closeTo(40, -1)]);

  // Wählen und Punkt 2 nach (90/10) ziehen: Breite 80
  await page.getByTestId("werkzeug-wahl").click();
  mm = await blattKoordinaten(blatt);
  await page.mouse.click(mm(20, 20).x, mm(20, 20).y);
  await expect(page.getByTestId("punkt-griffe")).toBeVisible();
  mm = await blattKoordinaten(blatt);
  const mitte = async (id: string) => {
    const b = (await page.getByTestId(id).boundingBox())!;
    return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
  };
  const px = mm(20, 0).x - mm(0, 0).x; // Pixel für 20 mm
  const p1 = await mitte("punkt-griff-1");
  await ziehen(page, p1, { x: p1.x + px, y: p1.y });
  await expect.poll(async () => (await aussenmass(page))[0]).toBeGreaterThan(78);
  await expect.poll(async () => (await aussenmass(page))[0]).toBeLessThan(82);

  // Punkt auf der Kante einfügen (Kante 0, Mitte 50/10) und nach unten ziehen: Tiefe wächst
  const k0 = await mitte("kante-griff-0");
  await ziehen(page, k0, { x: k0.x, y: k0.y + px / 2 });
  await expect(page.getByText("4 Punkte")).toBeVisible();
  await expect.poll(async () => (await aussenmass(page))[1]).toBeGreaterThan(48);

  // Punkt über die Eingabe verschieben, dann löschen
  await expect(page.getByTestId("punkt-x")).toBeVisible();
  await page.getByTestId("punkt-loeschen").click();
  await expect(page.getByText("3 Punkte")).toBeVisible();
  await expect(page.getByTestId("punkt-loeschen")).toHaveCount(0);
});
