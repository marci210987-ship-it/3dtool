import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

afterEach(cleanup);
import { Zeichnen } from "./zeichenblatt";
import { Eigenteil, neuesTeil } from "./zeichnen";

function Huelle({ start, extra = {} }: { start: Eigenteil[]; extra?: Partial<React.ComponentProps<typeof Zeichnen>> }) {
  const [teile, setTeile] = useState<Eigenteil[]>(start);
  return (
    <>
      <Zeichnen teile={teile} onChange={setTeile} fehler={[]} {...extra} />
      <output data-testid="anzahl">{teile.length}</output>
    </>
  );
}

describe("Zeichnen: Rückgängig und Wiederholen", () => {
  it("macht neue Teile und getippte Namen rückgängig und stellt sie wieder her", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[neuesTeil([])]} />);
    const zurueck = screen.getByTestId("rueckgaengig") as HTMLButtonElement;
    const vor = screen.getByTestId("wiederholen") as HTMLButtonElement;
    expect(zurueck.disabled).toBe(true);

    await benutzer.click(screen.getByTestId("teil-neu"));
    expect(screen.getByTestId("anzahl").textContent).toBe("2");
    expect(zurueck.disabled).toBe(false);

    // Mehrere Tastenanschläge in kurzer Zeit zählen als eine Änderung
    const name = screen.getByTestId("teil-name") as HTMLInputElement;
    await benutzer.clear(name);
    await benutzer.type(name, "Halter");
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Halter");

    await benutzer.click(zurueck);
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Eigenes Teil 2");
    expect(screen.getByTestId("anzahl").textContent).toBe("2");

    await benutzer.click(zurueck);
    expect(screen.getByTestId("anzahl").textContent).toBe("1");
    expect(zurueck.disabled).toBe(true);

    await benutzer.click(vor);
    expect(screen.getByTestId("anzahl").textContent).toBe("2");
    expect(vor.disabled).toBe(false);
    await benutzer.click(vor);
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Halter");
    expect(vor.disabled).toBe(true);
  });
});

describe("Zeichnen: Vorlagen und Ausrichten", () => {
  it("speichert eigene Vorlagen und setzt sie als neues Teil ein", async () => {
    const benutzer = userEvent.setup();
    const gespeichert: Array<[string, string]> = [];
    render(
      <Huelle
        start={[neuesTeil([])]}
        extra={{
          meineVorlagen: [{ id: "v-1", name: "Mein Winkel", teil: { name: "Mein Winkel", hoehe_mm: 7, formen: [{ typ: "rechteck", x: 0, y: 0, b: 20, t: 10, loch: false }] } }],
          onVorlageSpeichern: async (name, teil) => {
            gespeichert.push([name, teil.name]);
            return name === "kaputt" ? "Das Teil ist noch nicht gültig." : null;
          },
          onVorlageLoeschen: () => undefined,
        }}
      />,
    );
    const sichern = screen.getByTestId("vorlage-sichern") as HTMLButtonElement;
    expect(sichern.disabled).toBe(true);
    await benutzer.type(screen.getByTestId("vorlage-name"), "kaputt");
    await benutzer.click(sichern);
    expect(screen.getByTestId("vorlage-meldung").textContent).toBe("Das Teil ist noch nicht gültig.");
    await benutzer.clear(screen.getByTestId("vorlage-name"));
    await benutzer.type(screen.getByTestId("vorlage-name"), "Gut");
    await benutzer.click(screen.getByTestId("vorlage-sichern"));
    expect(screen.getByTestId("vorlage-meldung").textContent).toBe("„Gut“ gespeichert.");
    expect(gespeichert.map((g) => g[0])).toEqual(["kaputt", "Gut"]);

    await benutzer.selectOptions(screen.getByTestId("vorlage"), "v:v-1");
    expect(screen.getByTestId("anzahl").textContent).toBe("2");
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Mein Winkel");
    expect((screen.getByTestId("teil-hoehe") as HTMLInputElement).value).toBe("7");
  });

  it("richtet eine Form per Knopf an den übrigen Formen aus", async () => {
    const benutzer = userEvent.setup();
    const teil: Eigenteil = {
      ...neuesTeil([]),
      formen: [
        { typ: "rechteck", x: 0, y: 0, b: 60, t: 40, loch: false },
        { typ: "kreis", x: 5, y: 5, r: 4, loch: true },
      ],
    };
    render(<Huelle start={[teil]} />);
    await benutzer.click(screen.getAllByRole("button", { name: /Kreis/ }).find((b) => b.closest(".formliste"))!);
    const mitte = screen.getByTestId("ausrichten-mitte-x");
    expect((mitte as HTMLButtonElement).disabled).toBe(false);
    await benutzer.click(mitte);
    await benutzer.click(screen.getByTestId("ausrichten-mitte-y"));
    expect((screen.getByText("Mitte x").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("30");
    expect((screen.getByText("Mitte y").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("20");
    // Rückgängig nimmt die letzte Ausrichtung zurück
    await benutzer.click(screen.getByTestId("rueckgaengig"));
    await benutzer.click(screen.getAllByRole("button", { name: /Kreis/ }).find((b) => b.closest(".formliste"))!);
    expect((screen.getByText("Mitte y").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("5");
  });
});
