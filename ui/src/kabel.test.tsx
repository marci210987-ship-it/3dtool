import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { KabelArt, KabelAnsicht, profilKopieren } from "./kabel";

afterEach(() => cleanup());

const katalog: KabelArt[] = [
  {
    id: "kanal",
    name: "Kabelkanal",
    text: "Gerades Stück.",
    druck: "Öffnung nach oben auf das Bett legen.",
    standard: { innenbreite_mm: 20, wand_mm: 1.6, laenge_mm: 120, deckel: "nein" },
    felder: [
      { key: "innenbreite_mm", label: "Innenbreite", einheit: "mm", gruppe: "profil" },
      { key: "wand_mm", label: "Wandstärke", einheit: "mm", gruppe: "profil" },
      { key: "laenge_mm", label: "Nutzlänge", einheit: "mm" },
      { key: "deckel", label: "Deckel", auswahl: [{ wert: "nein", text: "Ohne Deckel" }, { wert: "ja", text: "Mit Deckel" }] },
    ],
  },
];

const teil = { id: "K1", art: "kanal", name: "Kabelkanal", parameter: { innenbreite_mm: 20, wand_mm: 1.6, laenge_mm: 120, deckel: "nein" } };

function ansicht(extra: Partial<Parameters<typeof KabelAnsicht>[0]> = {}) {
  return render(
    <KabelAnsicht
      katalog={katalog}
      teile={[teil]}
      aktivId="K1"
      fehler={[]}
      soll={[130.2, 26.8, 15.4]}
      stuecke={1}
      onWaehlen={() => undefined}
      onNeu={() => undefined}
      onEntfernen={() => undefined}
      onParameter={() => undefined}
      onAngleichen={() => undefined}
      onErzeugen={() => undefined}
      ergebnis={null}
      rechnet={false}
      jobText=""
      speicherpfad=""
      onSpeicherpfad={() => undefined}
      onSpeichern={() => undefined}
      {...extra}
    />,
  );
}

describe("Kabelmanagement", () => {
  it("zeigt Druckhinweis, Skizze und Außenmaß", () => {
    ansicht();
    expect(screen.getByText(/Öffnung nach oben/)).toBeTruthy();
    expect(screen.getByTestId("kabel-mass").textContent).toMatch(/mm/);
    expect(screen.getByTestId("kabel-skizze")).toBeTruthy();
    expect(screen.getByTestId("vorschau-art").textContent).toMatch(/Vereinfachte Vorschau/);
  });

  it("sperrt das Berechnen bei einer deutschen Fehlermeldung", () => {
    ansicht({ fehler: ["Kabelkanal: Wandstärke 0.4 liegt außerhalb von 1.2 bis 3.2 mm."] });
    expect(screen.getByTestId("kabel-fehler").textContent).toMatch(/außerhalb/);
    expect((screen.getByTestId("kabel-erzeugen") as HTMLButtonElement).disabled).toBe(true);
  });

  it("meldet ein abweichendes Profil und zeigt die Dateien nach dem Export", () => {
    ansicht({
      fehler: ["Kabelkanal und Kabelkanal K2: Die Teile passen nicht zusammen. Innenbreite ist 20 mm und 40 mm."],
      ergebnis: { ok: true, teile: [{ dateien: [{ id: "K1", stl: "/tmp/K1.stl", fcstd: "/tmp/K1.FCStd", ok: true }] }] },
    });
    expect(screen.getByTestId("kabel-passung").textContent).toMatch(/passen nicht/);
    expect(screen.getByTestId("kabel-dateien").textContent).toMatch(/STL/);
    expect(screen.getByTestId("kabel-dateien").textContent).toMatch(/FCStd/);
  });

  it("überträgt das Profil auf die anderen Teile", () => {
    const kopie = profilKopieren(
      [teil, { id: "K2", art: "ecke", name: "Ecke", parameter: { innenbreite_mm: 40, wand_mm: 1.2, laenge_mm: 50 } }],
      "K1",
    );
    expect(kopie[1].parameter.innenbreite_mm).toBe(20);
    expect(kopie[1].parameter.wand_mm).toBe(1.6);
    expect(kopie[0].parameter.innenbreite_mm).toBe(20);
  });
});
