import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { GehaeuseAnsicht, GehaeuseDaten, gehaeuseZahlen } from "./gehaeuse";

afterEach(() => cleanup());

const daten: GehaeuseDaten = {
  innen_b_mm: 100,
  innen_t_mm: 72,
  innen_h_mm: 32,
  wand_mm: 1.6,
  boden_mm: 1.6,
  deckel_mm: 1.6,
  radius_mm: 2,
  spiel_mm: 0.2,
  deckel: "schraube",
  schraube: "m3",
  senkung: "nein",
  platine: "raspberry_pi_4",
  standoff_h_mm: 8,
  standoff_d_mm: 6,
  lueftung: "nein",
  laschen: "nein",
  oeffnungen: [{ seite: "vorne", form: "rechteck", pos_mm: 40, unten_mm: 12, breite_mm: 12, hoehe_mm: 6 }],
};

describe("Elektronikgehäuse", () => {
  it("zeigt die Drucklage und das Außenmaß", () => {
    render(
      <GehaeuseAnsicht
        daten={daten}
        vorlagen={{ raspberry_pi_4: { name: "Raspberry Pi 4", quelle: "Zeichnung der Raspberry Pi 4." } }}
        fehler={[]}
        soll={{ korpus: [103.2, 75.2, 33.6], deckel: [106.8, 78.8, 4.6] }}
        onAendern={() => undefined}
        onOeffnung={() => undefined}
        onOeffnungNeu={() => undefined}
        onOeffnungWeg={() => undefined}
        onErzeugen={() => undefined}
        ergebnis={null}
        rechnet={false}
        jobText=""
        speicherpfad=""
        onSpeicherpfad={() => undefined}
        onSpeichern={() => undefined}
      />,
    );
    expect(screen.getByText(/Öffnung nach oben/)).toBeTruthy();
    expect(screen.getByTestId("gehaeuse-mass").textContent).toMatch(/mm/);
    expect(screen.getByText(/Zeichnung der Raspberry Pi 4/)).toBeTruthy();
    expect(screen.getByTestId("vorschau-art").textContent).toMatch(/Vereinfachte Vorschau/);
  });

  it("sperrt das Berechnen und zeigt STL sowie FCStd", () => {
    render(
      <GehaeuseAnsicht
        daten={daten}
        vorlagen={{}}
        fehler={["Wandstärke 0.4 liegt außerhalb von 1.2 bis 4 mm."]}
        soll={null}
        onAendern={() => undefined}
        onOeffnung={() => undefined}
        onOeffnungNeu={() => undefined}
        onOeffnungWeg={() => undefined}
        onErzeugen={() => undefined}
        ergebnis={{ ok: true, teile: [{ dateien: [{ id: "G_korpus", stl: "/tmp/a.stl", fcstd: "/tmp/a.FCStd", ok: true }] }] }}
        rechnet={false}
        jobText=""
        speicherpfad=""
        onSpeicherpfad={() => undefined}
        onSpeichern={() => undefined}
      />,
    );
    expect(screen.getByTestId("gehaeuse-fehler").textContent).toMatch(/außerhalb/);
    expect((screen.getByTestId("gehaeuse-erzeugen") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("gehaeuse-dateien").textContent).toMatch(/STL/);
    expect(screen.getByTestId("gehaeuse-dateien").textContent).toMatch(/FCStd/);
  });

  it("rechnet Öffnungen in Zahlen um", () => {
    const zahlen = gehaeuseZahlen({ ...daten, wand_mm: "1.6", oeffnungen: [{ ...daten.oeffnungen[0], pos_mm: "40" }] });
    expect(zahlen.wand_mm).toBe(1.6);
    expect((zahlen.oeffnungen as Array<{ pos_mm: number }>)[0].pos_mm).toBe(40);
  });
});
