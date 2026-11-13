import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Editor } from "./editor";
import { Box } from "./layout";

const plan = {
  einheiten_x: 11,
  einheiten_y: 9,
  ursprung_x_mm: 17,
  ursprung_y_mm: 21,
  raster_mm: 42,
  platten: [],
  verbinder_anzahl: 16,
  fehler: [],
  hinweise: [],
};

function Harness() {
  const [boxen, setBoxen] = useState<Box[]>([]);
  return <Editor breite={480} tiefe={420} plan={plan} boxen={boxen} onChange={setBoxen} />;
}

describe("Schubladenbild", () => {
  it("setzt vier Boxen, verschiebt, dreht und meldet eine Überlappung", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByTestId("katalog-klein"));
    await user.click(screen.getByTestId("katalog-mittel"));
    await user.click(screen.getByTestId("katalog-besteckfach"));
    await user.click(screen.getByTestId("katalog-gross"));
    expect(screen.getByTestId("box-B1")).toBeTruthy();
    expect(screen.getByTestId("box-B4")).toBeTruthy();
    expect(screen.queryByTestId("ueberlappung")).toBeNull();

    await user.click(screen.getByTestId("box-B4"));
    await user.click(screen.getByTestId("drehen"));
    await user.click(screen.getByTestId("links"));
    await user.click(screen.getByTestId("links"));
    expect(screen.getByTestId("ueberlappung").textContent).toMatch(/überlappen/i);

    const hoehe = screen.getByTestId("hoehe") as HTMLInputElement;
    fireEvent.change(hoehe, { target: { value: "4" } });
    expect(hoehe.value).toBe("4");
  });
});
