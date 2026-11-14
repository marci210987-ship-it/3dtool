/** Kleine Zahlfelder für die Zeichenoberfläche. */

export function Zahlfeld({ label, wert, onChange, testid }: { label: string; wert: number; onChange: (v: number) => void; testid?: string }) {
  return (
    <label>
      {label}
      <input
        data-testid={testid}
        inputMode="decimal"
        value={String(wert)}
        onChange={(e) => {
          const zahl = Number(e.target.value.replace(",", "."));
          if (Number.isFinite(zahl)) onChange(zahl);
        }}
      />
    </label>
  );
}

export function OptZahlfeld({ label, wert, onChange, testid }: { label: string; wert: number | undefined; onChange: (v: number | undefined) => void; testid?: string }) {
  return (
    <label>
      {label}
      <input
        data-testid={testid}
        inputMode="decimal"
        value={wert === undefined ? "" : String(wert)}
        onChange={(e) => {
          const text = e.target.value.trim().replace(",", ".");
          if (text === "") return onChange(undefined);
          const zahl = Number(text);
          if (Number.isFinite(zahl)) onChange(zahl);
        }}
      />
    </label>
  );
}
