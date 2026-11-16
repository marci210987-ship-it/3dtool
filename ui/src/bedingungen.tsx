import { useState } from "react";
import type { Eigenteil, Form } from "./zeichnen";

export interface Bedingung { art: "mittig" | "abstand" | "gleich" | "parallel"; quelle: string; ziel: string; dx?: number; dy?: number }
const mitte = (f: Form): [number, number] => {
  if (f.typ === "kreis") return [f.x, f.y];
  if (f.typ === "rechteck") return [f.x + f.b / 2, f.y + f.t / 2];
  throw new Error("Bedingungen unterstützen Rechtecke und Kreise.");
};

/** Gerichteter, zyklenfreier Graph: zuerst Bezug, dann davon abhängige Formen berechnen. */
export function bedingungenAnwenden(teil: Eigenteil): Eigenteil {
  const regeln = teil.bedingungen || [];
  if (!regeln.length) return teil;
  const formen = teil.formen.map((f) => ({ ...f }));
  const ids = new Map<string, Form>();
  formen.forEach((f) => {
    if (f.fid) {
      if (ids.has(f.fid)) throw new Error("Formkennungen sind doppelt vorhanden.");
      ids.set(f.fid, f);
    }
  });
  const felder = new Set<string>();
  regeln.forEach((r) => {
    if (!ids.has(r.quelle) || !ids.has(r.ziel)) throw new Error("Bezugsform fehlt.");
    if (r.quelle === r.ziel) throw new Error("Eine Form kann nicht ihr eigener Bezug sein.");
    if (!["mittig", "abstand", "gleich", "parallel"].includes(r.art)) throw new Error("Unbekannte Bedingung.");
    const key = `${r.ziel}:${r.art === "mittig" || r.art === "abstand" ? "lage" : r.art}`;
    if (felder.has(key)) throw new Error("Für diese Eigenschaft besteht bereits eine Bedingung. Zuerst entfernen.");
    felder.add(key);
  });
  const fertig = new Set<string>(); const besucht = new Set<string>();
  function loese(id: string) {
    if (fertig.has(id)) return;
    if (besucht.has(id)) throw new Error("Kreisbezug: Diese Bedingungen hängen gegenseitig voneinander ab.");
    besucht.add(id);
    const ziel = ids.get(id)!;
    const regelnZiel = regeln.filter((r) => r.ziel === id);
    // Größe und Richtung vor der Lage; Zentrierung bleibt dadurch erhalten.
    regelnZiel.sort((a, b) => Number(["mittig", "abstand"].includes(a.art)) - Number(["mittig", "abstand"].includes(b.art)));
    for (const r of regelnZiel) {
      loese(r.quelle);
      const quelle = ids.get(r.quelle)!;
      mitte(quelle); mitte(ziel);
      if (r.art === "gleich") {
        if (quelle.typ === "kreis" && ziel.typ === "kreis") ziel.r = quelle.r;
        else if (quelle.typ === "rechteck" && ziel.typ === "rechteck") {
          ziel.b = quelle.b; ziel.t = quelle.t;
          if (ziel.radius) ziel.radius = Math.min(ziel.radius, ziel.b / 2, ziel.t / 2);
        } else throw new Error("Gleiche Größe benötigt zwei Kreise oder zwei Rechtecke.");
      } else if (r.art === "parallel") {
        if (quelle.typ !== "rechteck" || ziel.typ !== "rechteck") throw new Error("Parallel benötigt zwei Rechtecke.");
        ziel.winkel = quelle.winkel || 0;
      } else {
        const [x, y] = mitte(quelle);
        const dx = r.art === "abstand" ? r.dx : 0; const dy = r.art === "abstand" ? r.dy : 0;
        if (!Number.isFinite(dx) || !Number.isFinite(dy)) throw new Error("Abstände müssen endliche Zahlen sein.");
        if (ziel.typ === "kreis") { ziel.x = x + dx!; ziel.y = y + dy!; }
        else if (ziel.typ === "rechteck") { ziel.x = x + dx! - ziel.b / 2; ziel.y = y + dy! - ziel.t / 2; }
      }
    }
    besucht.delete(id); fertig.add(id);
  }
  ids.forEach((_, id) => loese(id));
  return { ...teil, formen };
}

/** Kopien erhalten neue Kennungen; beim Löschen einer Form entfallen deren Beziehungen. */
export function bedingungenBereinigen(teil: Eigenteil): Eigenteil {
  const belegt = new Set<string>();
  const formen = teil.formen.map((f) => {
    if (!f.fid) return f;
    const fid = belegt.has(f.fid) ? crypto.randomUUID() : f.fid;
    belegt.add(fid);
    return fid === f.fid ? f : { ...f, fid };
  });
  return { ...teil, formen, bedingungen: (teil.bedingungen || []).filter((r) => belegt.has(r.quelle) && belegt.has(r.ziel)) };
}

export function BedingungenPanel({ teil, onChange }: { teil: Eigenteil; onChange: (teil: Eigenteil) => void }) {
  const [quelle, setQuelle] = useState(0); const [ziel, setZiel] = useState(1);
  const [art, setArt] = useState<Bedingung["art"]>("mittig");
  const [dx, setDx] = useState("0"); const [dy, setDy] = useState("0"); const [fehler, setFehler] = useState("");
  const optionen = teil.formen.map((f, i) => [f, i] as const).filter(([f]) => f.typ === "rechteck" || f.typ === "kreis");
  return <fieldset className="bedingungen-panel" data-testid="bedingungen"><legend>Skizzenbedingungen</legend>
    <p className="leise">Die abhängige Form folgt der Bezugsform. Unterstützt Rechtecke und Kreise; Abstände gelten zwischen den Mittelpunkten entlang der Zeichenachsen.</p>
    <label>Bezugsform<select value={quelle} onChange={(e) => setQuelle(Number(e.target.value))}>{optionen.map(([f, i]) => <option key={i} value={i}>{i + 1}: {f.typ}{f.loch ? " (Loch)" : ""}</option>)}</select></label>
    <label>Abhängige Form<select value={ziel} onChange={(e) => setZiel(Number(e.target.value))}>{optionen.map(([f, i]) => <option key={i} value={i}>{i + 1}: {f.typ}{f.loch ? " (Loch)" : ""}</option>)}</select></label>
    <label>Beziehung<select value={art} onChange={(e) => setArt(e.target.value as Bedingung["art"])}><option value="mittig">Mittig</option><option value="abstand">Fester Abstand</option><option value="gleich">Gleiche Größe</option><option value="parallel">Parallel (Rechtecke)</option></select></label>
    {art === "abstand" && <><label>Abstand X (mm)<input value={dx} onChange={(e) => setDx(e.target.value)} /></label><label>Abstand Y (mm)<input value={dy} onChange={(e) => setDy(e.target.value)} /></label></>}
    <button type="button" disabled={optionen.length < 2} onClick={() => {
      try {
        const formen = teil.formen.map((f) => ({ ...f, fid: f.fid || crypto.randomUUID() }));
        if (!formen[quelle] || !formen[ziel]) throw new Error("Bitte zwei vorhandene Formen wählen.");
        const zahl = (s: string) => s.trim() ? Number(s.replace(",", ".")) : NaN;
        const r: Bedingung = { art, quelle: formen[quelle].fid, ziel: formen[ziel].fid, ...(art === "abstand" ? { dx: zahl(dx), dy: zahl(dy) } : {}) };
        onChange(bedingungenAnwenden({ ...teil, formen, bedingungen: [...(teil.bedingungen || []), r] })); setFehler("");
      } catch (e) { setFehler((e as Error).message); }
    }}>Bedingung hinzufügen</button>
    {(teil.bedingungen || []).map((r, i) => <p key={i}>Form {teil.formen.findIndex((f) => f.fid === r.ziel) + 1} → Form {teil.formen.findIndex((f) => f.fid === r.quelle) + 1}: {r.art}{r.art === "abstand" ? ` (${r.dx}, ${r.dy} mm)` : ""} <button type="button" onClick={() => onChange({ ...teil, bedingungen: teil.bedingungen!.filter((_, j) => i !== j) })}>Bedingung entfernen</button></p>)}
    {fehler && <p role="alert">{fehler}</p>}
  </fieldset>;
}
