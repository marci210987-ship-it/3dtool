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
    // das leere Startteil wird ersetzt, nicht ergänzt
    expect(screen.getByTestId("anzahl").textContent).toBe("1");
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

describe("Zeichnen: Muster und Spiegeln", () => {
  const teilMitLoch = (): Eigenteil => ({
    ...neuesTeil([]),
    formen: [
      { typ: "rechteck", x: 0, y: 0, b: 100, t: 60, loch: false },
      { typ: "kreis", x: 20, y: 30, r: 3, loch: true },
    ],
  });
  const formAnzahl = () => document.querySelectorAll(".formliste li").length;
  const waehle = async (benutzer: ReturnType<typeof userEvent.setup>, name: RegExp) =>
    benutzer.click(screen.getAllByRole("button", { name }).find((b) => b.closest(".formliste"))!);

  it("erzeugt ein Gitter aus einer gewählten Form und macht es rückgängig", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[teilMitLoch()]} />);
    await waehle(benutzer, /Kreis/);
    expect(formAnzahl()).toBe(2);
    await benutzer.clear(screen.getByTestId("muster-zeilen"));
    await benutzer.type(screen.getByTestId("muster-zeilen"), "2");
    await benutzer.click(screen.getByTestId("muster-gitter")); // 3 Spalten x 2 Zeilen = 5 Kopien
    expect(formAnzahl()).toBe(7);
    expect(screen.getByTestId("muster-meldung").textContent).toContain("5 Formen");
    await benutzer.click(screen.getByTestId("rueckgaengig"));
    expect(formAnzahl()).toBe(2);
  });

  it("erzeugt ein Kreismuster um die Mitte der Platte", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[teilMitLoch()]} />);
    await waehle(benutzer, /Kreis/);
    // Mitte ist die Plattenmitte (50 / 30), Anzahl 6 -> 5 Kopien
    expect((screen.getByTestId("kreis-mitte-x") as HTMLInputElement).value).toBe("50");
    expect((screen.getByTestId("kreis-mitte-y") as HTMLInputElement).value).toBe("30");
    await benutzer.click(screen.getByTestId("muster-kreis"));
    expect(formAnzahl()).toBe(7);
  });

  it("spiegelt als Kopie oder ersetzt das Original und meldet das Formenlimit", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[teilMitLoch()]} />);
    await waehle(benutzer, /Kreis/);
    await benutzer.click(screen.getByTestId("spiegeln-x")); // Kopie an x = 50 -> 80
    expect(formAnzahl()).toBe(3);
    expect((screen.getByText("Mitte x").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("80");
    await benutzer.click(screen.getByTestId("spiegeln-ersetzen"));
    await benutzer.click(screen.getByTestId("spiegeln-x")); // ersetzt die Kopie: 80 -> 20
    expect(formAnzahl()).toBe(3);
    expect((screen.getByText("Mitte x").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("20");
    // Limit: 50 x 50 Gitter wäre 2499 Kopien
    await benutzer.clear(screen.getByTestId("muster-spalten"));
    await benutzer.type(screen.getByTestId("muster-spalten"), "50");
    await benutzer.clear(screen.getByTestId("muster-zeilen"));
    await benutzer.type(screen.getByTestId("muster-zeilen"), "50");
    await benutzer.click(screen.getByTestId("muster-gitter"));
    expect(screen.getByTestId("muster-meldung").textContent).toContain("Zu viele Formen");
    expect(formAnzahl()).toBe(3);
  });

  it("bietet das Kreismuster auch für Rechtecke an, ausgenommen mit Keil", async () => {
    const benutzer = userEvent.setup();
    const { unmount } = render(<Huelle start={[teilMitLoch()]} />);
    await waehle(benutzer, /Rechteck/);
    expect(screen.queryByTestId("muster-kreis")).not.toBeNull();
    // Kreismuster mit der Platte als Rechteck: Kopien drehen mit
    await benutzer.click(screen.getByTestId("muster-kreis"));
    expect(formAnzahl()).toBe(7);
    unmount();

    const keilTeil: Eigenteil = { ...neuesTeil([]), formen: [{ typ: "rechteck", x: 0, y: 0, b: 40, t: 20, loch: false, keil_mm: 5 }] };
    render(<Huelle start={[keilTeil]} />);
    await waehle(benutzer, /Rechteck/);
    expect(screen.queryByTestId("muster-kreis")).toBeNull();
    expect(screen.getByText(/Ein Rechteck mit Keil lässt sich nicht drehen/)).toBeTruthy();
  });

  it("dreht ein Rechteck per Feld und per Knopf", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[teilMitLoch()]} />);
    await waehle(benutzer, /Rechteck/);
    await benutzer.click(screen.getByTestId("winkel-plus90"));
    expect((screen.getByTestId("form-winkel") as HTMLInputElement).value).toBe("90");
    await benutzer.click(screen.getByTestId("winkel-plus90"));
    await benutzer.click(screen.getByTestId("winkel-plus90"));
    await benutzer.click(screen.getByTestId("winkel-plus90"));
    expect((screen.getByTestId("form-winkel") as HTMLInputElement).value).toBe(""); // 360 = keine Drehung
    await benutzer.type(screen.getByTestId("form-winkel"), "30");
    expect((screen.getByTestId("form-winkel") as HTMLInputElement).value).toBe("30");
    expect(screen.getByTestId("teil-mass").textContent).toContain("Außenmaß");
  });
});

describe("Zeichnen: Maße per Eingabe ändern", () => {
  it("ändert Breite, Tiefe und Durchmesser durch Klick auf das Maß", async () => {
    const benutzer = userEvent.setup();
    const teil: Eigenteil = {
      ...neuesTeil([]),
      formen: [
        { typ: "rechteck", x: 0, y: 0, b: 100, t: 60, loch: false },
        { typ: "kreis", x: 20, y: 30, r: 3, loch: true },
      ],
    };
    render(<Huelle start={[teil]} />);
    // Maß der Platte ändern
    await benutzer.click(screen.getByTestId("masse-b"));
    const eingabe = screen.getByTestId("masse-eingabe") as HTMLInputElement;
    expect(eingabe.value).toBe("100");
    await benutzer.clear(eingabe);
    await benutzer.type(eingabe, "120,5{Enter}");
    expect(screen.queryByTestId("masse-eingabe")).toBeNull();
    expect((screen.getByText("Breite").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("120.5");
    // ungültige Eingabe: Feld bleibt offen, Wert ändert sich nicht
    await benutzer.click(screen.getByTestId("masse-t"));
    await benutzer.clear(screen.getByTestId("masse-eingabe"));
    await benutzer.type(screen.getByTestId("masse-eingabe"), "abc{Enter}");
    expect(screen.queryByTestId("masse-eingabe")).not.toBeNull();
    await benutzer.keyboard("{Escape}");
    expect(screen.queryByTestId("masse-eingabe")).toBeNull();
    expect((screen.getByText("Tiefe").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("60");
    // Durchmesser des Lochs
    await benutzer.click(screen.getAllByRole("button", { name: /Kreis/ }).find((b) => b.closest(".formliste"))!);
    await benutzer.click(screen.getByTestId("masse-d"));
    const d = screen.getByTestId("masse-eingabe") as HTMLInputElement;
    expect(d.value).toBe("6");
    await benutzer.clear(d);
    await benutzer.type(d, "10{Enter}");
    expect((screen.getByText("Radius").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("5");
    // Rückgängig nimmt die Änderung zurück
    await benutzer.click(screen.getByTestId("rueckgaengig"));
    await benutzer.click(screen.getAllByRole("button", { name: /Kreis/ }).find((b) => b.closest(".formliste"))!);
    expect((screen.getByText("Radius").closest("label")!.querySelector("input") as HTMLInputElement).value).toBe("3");
  });
});

describe("Zeichnen: Umriss importieren", () => {
  const svgText =
    '<svg xmlns="http://www.w3.org/2000/svg" width="80mm" height="50mm" viewBox="0 0 80 50"><rect x="0" y="0" width="80" height="50" rx="4"/><circle cx="40" cy="25" r="6"/></svg>';

  it("liest eine SVG-Datei, zeigt Größe und Hinweise und fügt sie als neues Teil ein", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[neuesTeil([])]} />);
    const datei = new File([svgText], "Gehaeuse Deckel.svg", { type: "image/svg+xml" });
    await benutzer.upload(screen.getByTestId("import-datei"), datei);
    const vorschau = await screen.findByTestId("import-vorschau");
    expect(vorschau.textContent).toContain("2 Formen, davon 1 Löcher, 80 × 50 mm");
    expect((screen.getByTestId("import-massstab") as HTMLInputElement).value).toBe("1");
    // Maßstab ändern: doppelte Größe
    await benutzer.clear(screen.getByTestId("import-massstab"));
    await benutzer.type(screen.getByTestId("import-massstab"), "2");
    expect(screen.getByTestId("import-vorschau").textContent).toContain("160 × 100 mm");
    await benutzer.clear(screen.getByTestId("import-hoehe"));
    await benutzer.type(screen.getByTestId("import-hoehe"), "8");
    await benutzer.click(screen.getByTestId("import-einfuegen"));
    expect(screen.getByTestId("anzahl").textContent).toBe("1");
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Gehaeuse Deckel");
    expect((screen.getByTestId("teil-hoehe") as HTMLInputElement).value).toBe("8");
    expect(document.querySelectorAll(".formliste li")).toHaveLength(2);
    expect(screen.queryByTestId("import-vorschau")).toBeNull();
  });

  it("sperrt das Einfügen bei ungültigem Maßstab oder fehlender Außenform und meldet ungültige Dateien", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[neuesTeil([])]} />);
    await benutzer.upload(screen.getByTestId("import-datei"), new File([svgText], "a.svg", { type: "image/svg+xml" }));
    await screen.findByTestId("import-vorschau");
    await benutzer.clear(screen.getByTestId("import-massstab"));
    await benutzer.type(screen.getByTestId("import-massstab"), "0");
    expect((screen.getByTestId("import-einfuegen") as HTMLButtonElement).disabled).toBe(true);
    await benutzer.clear(screen.getByTestId("import-massstab"));
    await benutzer.type(screen.getByTestId("import-massstab"), "1");
    expect((screen.getByTestId("import-einfuegen") as HTMLButtonElement).disabled).toBe(false);
    await benutzer.clear(screen.getByTestId("import-hoehe"));
    await benutzer.type(screen.getByTestId("import-hoehe"), "300");
    expect((screen.getByTestId("import-einfuegen") as HTMLButtonElement).disabled).toBe(true);
    // keine SVG
    await benutzer.upload(screen.getByTestId("import-datei"), new File(["Hallo"], "kaputt.svg", { type: "image/svg+xml" }));
    const hinweise = await screen.findByTestId("import-hinweise");
    expect(hinweise.textContent).toContain("keine gültige SVG");
    expect((screen.getByTestId("import-einfuegen") as HTMLButtonElement).disabled).toBe(true);
  });

  it("erkennt DXF an der Endung und liest einen Umriss", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[neuesTeil([])]} />);
    const dxf = "0\nSECTION\n2\nENTITIES\n0\nLWPOLYLINE\n90\n4\n70\n1\n10\n0\n20\n0\n10\n30\n20\n0\n10\n30\n20\n20\n10\n0\n20\n20\n0\nENDSEC\n0\nEOF\n";
    await benutzer.upload(screen.getByTestId("import-datei"), new File([dxf], "platte.dxf"));
    const vorschau = await screen.findByTestId("import-vorschau");
    expect(vorschau.textContent).toContain("1 Formen, davon 0 Löcher, 30 × 20 mm");
  });
});

describe("Zeichnen: Vorlagen ersetzen nur leere Teile", () => {
  it("ergänzt ein neues Teil, wenn das aktive Teil schon Formen hat", async () => {
    const benutzer = userEvent.setup();
    const belegt: Eigenteil = { ...neuesTeil([]), formen: [{ typ: "rechteck", x: 0, y: 0, b: 10, t: 10, loch: false }] };
    render(<Huelle start={[belegt]} />);
    await benutzer.selectOptions(screen.getByTestId("vorlage"), "platte");
    expect(screen.getByTestId("anzahl").textContent).toBe("2");
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Platte mit Bohrungen");
    // jetzt ist das aktive Teil belegt: eine zweite Vorlage ergänzt wieder
    await benutzer.selectOptions(screen.getByTestId("vorlage"), "stufe");
    expect(screen.getByTestId("anzahl").textContent).toBe("3");
  });

  it("ersetzt das leere Startteil durch eine mitgelieferte Vorlage und behält die Id", async () => {
    const benutzer = userEvent.setup();
    render(<Huelle start={[neuesTeil([])]} />);
    await benutzer.selectOptions(screen.getByTestId("vorlage"), "winkel");
    expect(screen.getByTestId("anzahl").textContent).toBe("1");
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Winkelhalter");
    expect(document.querySelectorAll(".teileliste li button")[0].textContent).toContain("E1");
    // Rückgängig stellt das leere Teil wieder her
    await benutzer.click(screen.getByTestId("rueckgaengig"));
    expect((screen.getByTestId("teil-name") as HTMLInputElement).value).toBe("Eigenes Teil 1");
  });
});
