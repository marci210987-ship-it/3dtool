import { expect, test } from "@playwright/test";

test("Positionierung: zentrieren, Größe ändern, konzentrisch, Randabstand und mobiles Layout", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await page.getByTestId("vorlage").selectOption("platte");
  const kreise = page.locator(".formliste li button", { hasText: "Kreis" });
  await kreise.first().click();
  await page.getByTestId("zentrieren").click();
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("30");
  await page.locator(".formliste li button", { hasText: "Rechteck" }).first().click();
  await page.getByLabel("Links x", { exact: true }).fill("20");
  await page.getByLabel("Unten y", { exact: true }).fill("10");
  await page.getByLabel("Breite", { exact: true }).fill("80");
  await kreise.first().click();
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("60");
  await expect(page.getByLabel("Mitte y", { exact: true })).toHaveValue("30");
  await page.getByTestId("form-durchmesser").fill("6");
  await page.getByTestId("konzentrisch-d").fill("14");
  await page.getByTestId("konzentrisch-art").selectOption("hinzufuegen");
  await page.getByTestId("konzentrisch-erstellen").click();
  await kreise.last().click();
  await expect(page.getByTestId("form-durchmesser")).toHaveValue("14");
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("60");
  await kreise.first().click();
  await page.getByTestId("kantenabstand").fill("5");
  await page.getByTestId("ausrichten-rechts").click();
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("92");
  await kreise.last().click();
  await expect(page.getByLabel("Mitte x", { exact: true })).toHaveValue("92");
  await page.getByTestId("fang-an").uncheck();
  await expect(page.getByTestId("fanglinien")).toHaveCount(0);
  for (const width of [390, 768, 1400]) {
    await page.setViewportSize({ width, height: 900 });
    const layout = await page.evaluate(() => ({ passt: document.documentElement.scrollWidth <= window.innerWidth + 1,
      ueberlauf: [...document.querySelectorAll("body *")].filter(el => el.getBoundingClientRect().right > window.innerWidth + 1).slice(0, 8).map(el => `${el.tagName}.${el.className}`) }));
    expect(layout, JSON.stringify({ width, ...layout })).toMatchObject({ passt: true });
  }
});

test("Fangpunkt wird beim Zeichnen sichtbar und lässt sich abschalten", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Eigene Teile zeichnen/ }).click();
  await page.getByTestId("vorlage").selectOption("platte");
  await page.getByTestId("werkzeug-kreis").click();
  const blatt = page.getByTestId("zeichenblatt");
  await blatt.scrollIntoViewIfNeeded();
  const punkt = await blatt.evaluate(el => {
    const svg = el as SVGSVGElement;
    const p = svg.createSVGPoint(); p.x = 30; p.y = svg.viewBox.baseVal.height - 20;
    const q = p.matrixTransform(svg.getScreenCTM()!);
    return { x: q.x, y: q.y };
  });
  await page.mouse.move(punkt.x + 1, punkt.y + 1);
  await expect(page.getByTestId("fangpunkt-aktiv")).toBeVisible();
  await page.getByTestId("fang-an").uncheck();
  await expect(page.getByTestId("fangpunkt-aktiv")).toHaveCount(0);
});
