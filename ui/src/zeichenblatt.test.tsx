import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Zeichnen } from "./zeichenblatt";
import { Eigenteil, neuesTeil } from "./zeichnen";

function Huelle({ start }: { start: Eigenteil[] }) {
  const [teile, setTeile] = useState<Eigenteil[]>(start);
  return (
    <>
      <Zeichnen teile={teile} onChange={setTeile} fehler={[]} />
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
