import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => cleanup());
import { ErsatzArt, ErsatzteilAnsicht } from "./ersatzteile";

const katalog: ErsatzArt[] = [
  {
    id: "kabelclip",
    name: "Kabelclip",
    text: "Hält Kabel.",
    druck: "Flach drucken, Öffnung nach oben.",
    standard: { durchmesser_mm: 6, anzahl: 1, wand_mm: 1.2, befestigung: "schraube" },
    felder: [
      { key: "durchmesser_mm", label: "Kabeldurchmesser", min: 3, max: 25, einheit: "mm" },
      { key: "befestigung", label: "Befestigung", auswahl: [{ wert: "schraube", text: "Schraube" }, { wert: "kleben", text: "Kleben" }] },
    ],
  },
];

describe("Ersatzteil-Formular", () => {
  it("zeigt den Druckhinweis und meldet eine Maßänderung", async () => {
    const user = userEvent.setup();
    const onParameter = vi.fn();
    render(
      <ErsatzteilAnsicht
        katalog={katalog}
        teile={[{ id: "ET1", art: "kabelclip", name: "Kabelclip", parameter: { durchmesser_mm: 6, befestigung: "schraube" } }]}
        aktivId="ET1"
        fehler={[]}
        soll={[14, 26.4, 5.8]}
        onWaehlen={() => undefined}
        onNeu={() => undefined}
        onParameter={onParameter}
        onErzeugen={() => undefined}
        ergebnis={null}
        rechnet={false}
        jobText=""
        speicherpfad=""
        onSpeicherpfad={() => undefined}
        onSpeichern={() => undefined}
      />,
    );
    expect(screen.getByText(/Flach drucken/)).toBeTruthy();
    expect(screen.getByTestId("vorschau-art").textContent).toMatch(/Vereinfachte Vorschau/);
    await user.clear(screen.getByTestId("feld-durchmesser_mm"));
    await user.type(screen.getByTestId("feld-durchmesser_mm"), "8");
    expect(onParameter).toHaveBeenCalled();
  });

  it("zeigt eine deutsche Fehlermeldung und sperrt das Berechnen", () => {
    render(
      <ErsatzteilAnsicht
        katalog={katalog}
        teile={[{ id: "ET1", art: "kabelclip", name: "Kabelclip", parameter: { durchmesser_mm: 0, befestigung: "schraube" } }]}
        aktivId="ET1"
        fehler={["Kabeldurchmesser 0 liegt außerhalb von 3 bis 25 mm."]}
        soll={null}
        onWaehlen={() => undefined}
        onNeu={() => undefined}
        onParameter={() => undefined}
        onErzeugen={() => undefined}
        ergebnis={null}
        rechnet={false}
        jobText=""
        speicherpfad=""
        onSpeicherpfad={() => undefined}
        onSpeichern={() => undefined}
      />,
    );
    expect(screen.getByTestId("ersatz-fehler").textContent).toMatch(/außerhalb/);
    expect((screen.getByTestId("ersatz-erzeugen") as HTMLButtonElement).disabled).toBe(true);
  });

  it("zeigt STL und FCStd nach erfolgreichem Export", () => {
    render(
      <ErsatzteilAnsicht
        katalog={katalog}
        teile={[{ id: "ET1", art: "kabelclip", name: "Kabelclip", parameter: { durchmesser_mm: 6, befestigung: "schraube" } }]}
        aktivId="ET1"
        fehler={[]}
        soll={[14, 26.4, 5.8]}
        onWaehlen={() => undefined}
        onNeu={() => undefined}
        onParameter={() => undefined}
        onErzeugen={() => undefined}
        ergebnis={{
          ok: true,
          teile: [{ dateien: [{ id: "ET1", stl: "/tmp/ET1.stl", fcstd: "/tmp/ET1.FCStd", ok: true }] }],
        }}
        rechnet={false}
        jobText=""
        speicherpfad=""
        onSpeicherpfad={() => undefined}
        onSpeichern={() => undefined}
      />,
    );
    const dateien = screen.getByTestId("ersatz-dateien");
    expect(dateien.textContent).toMatch(/STL/);
    expect(dateien.textContent).toMatch(/FCStd/);
  });
});
