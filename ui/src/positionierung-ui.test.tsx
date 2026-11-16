import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { Zeichnen } from "./zeichenblatt";
import { neuesTeil, type Eigenteil } from "./zeichnen";
vi.mock("./ansicht3d", () => ({ Ansicht3D: () => null }));
afterEach(cleanup);
function Huelle() {
  const [teile, setTeile] = useState<Eigenteil[]>([{ ...neuesTeil([]), formen: [
    { typ: "rechteck", x: 30, y: 20, b: 80, t: 40, loch: false },
    { typ: "kreis", x: 38, y: 29, r: 3, loch: true },
  ] }]);
  return <Zeichnen teile={teile} onChange={setTeile} fehler={[]} />;
}
it("zentriert, folgt Größenänderung, löst manuell eine Achse und unterstützt Rückgängig", async () => {
  const user = userEvent.setup(); render(<Huelle />);
  await user.click(screen.getByRole("button", { name: "Kreis (Loch)" }));
  await user.click(screen.getByTestId("zentrieren"));
  expect((screen.getByLabelText("Mitte x") as HTMLInputElement).value).toBe("70");
  await user.click(screen.getAllByRole("button", { name: "Rechteck" }).find(b => b.closest(".formliste"))!);
  fireEvent.change(screen.getByLabelText("Breite", { exact: true }), { target: { value: "100" } });
  await user.click(screen.getByRole("button", { name: "Kreis (Loch)" }));
  expect((screen.getByLabelText("Mitte x") as HTMLInputElement).value).toBe("80");
  fireEvent.change(screen.getByLabelText("Mitte x"), { target: { value: "65" } });
  await user.click(screen.getAllByRole("button", { name: "Rechteck" }).find(b => b.closest(".formliste"))!);
  fireEvent.change(screen.getByLabelText("Tiefe", { exact: true }), { target: { value: "60" } });
  await user.click(screen.getByRole("button", { name: "Kreis (Loch)" }));
  expect((screen.getByLabelText("Mitte x") as HTMLInputElement).value).toBe("65");
  expect((screen.getByLabelText("Mitte y") as HTMLInputElement).value).toBe("50");
  await user.click(screen.getByTestId("zentrieren"));
  await user.click(screen.getByTestId("rueckgaengig"));
  await user.click(screen.getByRole("button", { name: "Kreis (Loch)" }));
  expect((screen.getByLabelText("Mitte x") as HTMLInputElement).value).toBe("65");
});
it("erstellt einen konzentrischen Materialkreis und übernimmt den eingegebenen Durchmesser", async () => {
  const user = userEvent.setup(); render(<Huelle />);
  await user.click(screen.getByRole("button", { name: "Kreis (Loch)" }));
  await user.clear(screen.getByTestId("konzentrisch-d"));
  await user.type(screen.getByTestId("konzentrisch-d"), "12,5");
  await user.selectOptions(screen.getByTestId("konzentrisch-art"), "hinzufuegen");
  await user.click(screen.getByTestId("konzentrisch-erstellen"));
  await user.click(screen.getAllByRole("button", { name: "Kreis" }).find(b => b.closest(".formliste"))!);
  expect((screen.getByTestId("form-durchmesser") as HTMLInputElement).value).toBe("12.5");
  expect((screen.getByLabelText("Mitte x") as HTMLInputElement).value).toBe("38");
  expect(screen.getByTestId("positionsbindung").textContent).toContain("horizontal und vertikal");
});
