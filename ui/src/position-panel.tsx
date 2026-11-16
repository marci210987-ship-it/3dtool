import { useEffect, useState } from "react";
import { formBox, MIN_MM, type Form } from "./zeichnen";
import { anKante, bauteilRahmen, konzentrischerKreis, mittelpunktUebernehmen, positionLoesen, zentrieren } from "./positionierung";

export function PositionPanel({ formen, index, onChange }: { formen: Form[]; index: number; onChange: (formen: Form[]) => void }) {
  const form = formen[index];
  const [durchmesser, setDurchmesser] = useState("10");
  const [entfernen, setEntfernen] = useState(true);
  const [abstand, setAbstand] = useState("0");
  const [quelle, setQuelle] = useState("");
  const [meldung, setMeldung] = useState("");
  const rahmen = bauteilRahmen(formen, index);
  const zahl = (text: string) => text.trim() ? Number(text.replace(",", ".")) : NaN;
  const d = zahl(durchmesser), rand = zahl(abstand);
  const b = formBox(form);
  function uebernehmen() {
    const neu = mittelpunktUebernehmen(formen, index, Number(quelle));
    if (neu === formen) setMeldung("Dieser Bezug würde einen Kreisbezug erzeugen. Bitte eine andere Form wählen.");
    else { setMeldung(""); onChange(neu); }
  }
  return <section className="position-panel" aria-label="Positionierung">
    <strong>Positionieren</strong>
    <div className="knopfzeile">
      <button type="button" data-testid="zentrieren" disabled={!rahmen} onClick={() => onChange(zentrieren(formen, index))}>Auf Bauteilmitte setzen</button>
      <button type="button" data-testid="ausrichten-mitte-x" disabled={!rahmen} onClick={() => onChange(zentrieren(formen, index, ["x"]))}>Horizontal zentrieren</button>
      <button type="button" data-testid="ausrichten-mitte-y" disabled={!rahmen} onClick={() => onChange(zentrieren(formen, index, ["y"]))}>Vertikal zentrieren</button>
    </div>
    {form.position && <><p className="leise" data-testid="positionsbindung">Position gebunden: {form.position.x ? "horizontal" : ""}{form.position.x && form.position.y ? " und " : ""}{form.position.y ? "vertikal" : ""}. Größenänderungen werden übernommen.</p>
      <button type="button" onClick={() => onChange(formen.map((f, i) => i === index ? positionLoesen(f) : f))}>Positionsbindung lösen</button></>}
    <p className="leise">Manuelles Verschieben löst die Bindung auf der geänderten Achse.</p>
    <label>Abstand zur Bauteilkante (mm)<input data-testid="kantenabstand" inputMode="decimal" value={abstand} onChange={e => setAbstand(e.target.value)} /></label>
    <div className="knopfzeile" aria-label="An Kante ausrichten">
      {(["links", "rechts", "unten", "oben"] as const).map(seite => <button key={seite} type="button" data-testid={`ausrichten-${seite}`} disabled={!rahmen || !Number.isFinite(rand) || rand < 0} onClick={() => onChange(anKante(formen, index, seite, rand))}>{seite[0].toUpperCase() + seite.slice(1)}</button>)}
    </div>
    {rahmen && <p className="leise">Randabstände: links {+(b[0] - rahmen[0]).toFixed(3)}, rechts {+(rahmen[2] - b[2]).toFixed(3)}, unten {+(b[1] - rahmen[1]).toFixed(3)}, oben {+(rahmen[3] - b[3]).toFixed(3)} mm. Bezug: achsparalleles Außenmaß freier Materialformen.</p>}
    <label>Bezug für Mittelpunkt<select data-testid="mittelpunkt-quelle" value={quelle} onChange={e => { setQuelle(e.target.value); setMeldung(""); }}><option value="">Form wählen</option>{formen.map((f, i) => i === index ? null : <option key={i} value={i}>Form {i + 1}: {f.typ}{f.loch ? " (Loch)" : ""}</option>)}</select></label>
    <button type="button" disabled={quelle === ""} onClick={uebernehmen}>Mittelpunkt übernehmen</button>
    {form.typ === "kreis" && <>
      <strong>Kreis um Mittelpunkt erstellen</strong>
      <label>Neuer Durchmesser (mm)<input data-testid="konzentrisch-d" inputMode="decimal" value={durchmesser} onChange={e => setDurchmesser(e.target.value)} /></label>
      <label>Material<select data-testid="konzentrisch-art" value={entfernen ? "entfernen" : "hinzufuegen"} onChange={e => setEntfernen(e.target.value === "entfernen")}><option value="entfernen">Material entfernen (Loch)</option><option value="hinzufuegen">Material hinzufügen</option></select></label>
      <button type="button" data-testid="konzentrisch-erstellen" disabled={!Number.isFinite(d) || d < MIN_MM || formen.length >= 200} onClick={() => onChange(konzentrischerKreis(formen, index, d, entfernen))}>Kreis erstellen</button>
      <p className="leise">Gemeinsamer Mittelpunkt bleibt gebunden. Material wird zuerst vereinigt, danach werden alle Löcher ausgeschnitten.</p>
    </>}
    {meldung && <p role="status">{meldung}</p>}
  </section>;
}

export function DurchmesserFeld({ wert, onChange }: { wert: number; onChange: (d: number) => void }) {
  const [text, setText] = useState(String(wert));
  useEffect(() => setText(String(wert)), [wert]);
  const d = text.trim() ? Number(text.replace(",", ".")) : NaN;
  const gueltig = Number.isFinite(d) && d >= MIN_MM;
  return <label>Durchmesser (mm)<input data-testid="form-durchmesser" inputMode="decimal" value={text} aria-invalid={!gueltig}
    onChange={e => { const neu = e.target.value; setText(neu); const zahl = neu.trim() ? Number(neu.replace(",", ".")) : NaN; if (Number.isFinite(zahl) && zahl >= MIN_MM && !neu.endsWith(".") && !neu.endsWith(",")) onChange(zahl); }}
    onBlur={() => setText(String(wert))} onKeyDown={e => { if (e.key === "Enter" && gueltig) { onChange(d); e.currentTarget.blur(); } if (e.key === "Escape") { setText(String(wert)); e.currentTarget.blur(); } }} /></label>;
}
