/** Parametrische Positionen; Koordinaten bleiben für Vorschau und Export vollständig aufgelöst. */
import { bereinigen, formBox, formMitte, MAX_FORMEN, MIN_MM, verschieben, type Form } from "./zeichnen";

export type Achse = "x" | "y";
export interface PositionsBezug { quelle: string; lage: "mitte" | "min" | "max"; abstand?: number }
export type Position = Partial<Record<Achse, PositionsBezug>>;
type Box = [number, number, number, number];

/** Kopien bekommen eigene IDs und keine unbeabsichtigt kopierten Bindungen. */
export function mitFormIds(formen: Form[]): Form[] {
  const reserviert = new Set([...formen.map(f => f.form_id).filter(Boolean), ...formen.flatMap(f => Object.values(f.position ?? {}).map(r => r.quelle))]);
  const gesehen = new Set<string>();
  let n = 1;
  return formen.map(f => {
    if (f.form_id && !gesehen.has(f.form_id)) { gesehen.add(f.form_id); return f; }
    while (reserviert.has(`f${n}`)) n++;
    const id = `f${n++}`;
    reserviert.add(id); gesehen.add(id);
    const { position: _position, ...rest } = f;
    return { ...rest, form_id: id } as Form;
  });
}

export function positionLoesen(form: Form, achsen: Achse[] = ["x", "y"]): Form {
  if (!form.position) return form;
  const position = { ...form.position };
  for (const a of achsen) delete position[a];
  return { ...form, position: Object.keys(position).length ? position : undefined };
}

/** Der Bauteilrahmen besteht aus freien Materialformen. Gebundene Aufsätze verändern ihren eigenen Bezug nicht. */
export function bauteilRahmen(formen: Form[], ausser: number): Box | null {
  const boxen = formen.filter((f, i) => i !== ausser && !f.loch && !f.position?.x && !f.position?.y).map(formBox);
  if (!boxen.length) return null;
  return [Math.min(...boxen.map(b => b[0])), Math.min(...boxen.map(b => b[1])), Math.max(...boxen.map(b => b[2])), Math.max(...boxen.map(b => b[3]))];
}

/** Auflösen je Achse, auch bei rückwärts angeordneten Ketten. Ungültige/zyklische Bezüge werden gelöst. */
export function positionenAufloesen(eingabe: Form[]): Form[] {
  const formen = mitFormIds(eingabe);
  const ids = new Map(formen.map((f, i) => [f.form_id!, i]));
  const status = new Map<string, number>();
  function achse(i: number, a: Achse): boolean {
    const key = `${i}-${a}`;
    if (status.get(key) === 1) return false;
    if (status.get(key) === 2) return true;
    status.set(key, 1);
    const regel = formen[i].position?.[a];
    if (regel) {
      let box: Box | null = null;
      if (regel.quelle === "teil") box = bauteilRahmen(formen, i);
      else {
        const j = ids.get(regel.quelle);
        if (j !== undefined && j !== i && achse(j, a)) box = formBox(formen[j]);
      }
      if (!box || !["mitte", "min", "max"].includes(regel.lage) || !Number.isFinite(regel.abstand ?? 0)) {
        formen[i] = positionLoesen(formen[i], [a]);
        status.set(key, 2);
        return false;
      }
      const k = a === "x" ? 0 : 1;
      const eigen = formBox(formen[i]);
      const ziel = regel.lage === "mitte" ? (box[k] + box[k + 2]) / 2
        : regel.lage === "min" ? box[k] + (regel.abstand ?? 0) + (eigen[k + 2] - eigen[k]) / 2
        : box[k + 2] - (regel.abstand ?? 0) - (eigen[k + 2] - eigen[k]) / 2;
      const delta = bereinigen(ziel - formMitte(formen[i])[k]);
      formen[i] = verschieben(formen[i], a === "x" ? delta : 0, a === "y" ? delta : 0);
    }
    status.set(key, 2);
    return true;
  }
  for (let i = 0; i < formen.length; i++) { achse(i, "x"); achse(i, "y"); }
  return formen;
}

export function positionBinden(formen: Form[], index: number, regeln: Position): Form[] {
  if (!formen[index]) return formen;
  const neu = mitFormIds(formen);
  neu[index] = { ...neu[index], position: { ...neu[index].position, ...regeln } };
  return positionenAufloesen(neu);
}

export function zentrieren(formen: Form[], index: number, achsen: Achse[] = ["x", "y"]): Form[] {
  if (!bauteilRahmen(formen, index)) return formen;
  const regeln: Position = {};
  for (const a of achsen) regeln[a] = { quelle: "teil", lage: "mitte" };
  return positionBinden(formen, index, regeln);
}

/** Abstand zwischen Formrand und achsparallelem Außenrahmen, nicht zwischen Lochmitte und Kante. */
export function anKante(formen: Form[], index: number, seite: "links" | "rechts" | "unten" | "oben", abstand = 0): Form[] {
  if (!Number.isFinite(abstand) || abstand < 0 || !bauteilRahmen(formen, index)) return formen;
  const a = seite === "links" || seite === "rechts" ? "x" : "y";
  const lage = seite === "links" || seite === "unten" ? "min" : "max";
  return positionBinden(formen, index, { [a]: { quelle: "teil", lage, abstand } });
}

/** Gemeinsamen Mittelpunkt übernehmen, ohne eine zyklische Abhängigkeit zuzulassen. */
export function mittelpunktUebernehmen(formen: Form[], index: number, quelle: number): Form[] {
  if (!formen[index] || !formen[quelle] || index === quelle) return formen;
  const neu = mitFormIds(formen);
  const zielId = neu[index].form_id!;
  function haengtAb(i: number, besucht = new Set<number>()): boolean {
    if (besucht.has(i)) return false;
    besucht.add(i);
    return Object.values(neu[i].position ?? {}).some(r => {
      if (r.quelle === zielId) return true;
      const j = neu.findIndex(f => f.form_id === r.quelle);
      return j >= 0 && haengtAb(j, besucht);
    });
  }
  if (haengtAb(quelle)) return formen;
  const regel: PositionsBezug = { quelle: neu[quelle].form_id!, lage: "mitte" };
  return positionBinden(neu, index, { x: regel, y: regel });
}

export function konzentrischerKreis(formen: Form[], quelle: number, durchmesser: number, loch: boolean): Form[] {
  if (formen[quelle]?.typ !== "kreis" || !Number.isFinite(durchmesser) || durchmesser < MIN_MM || formen.length >= MAX_FORMEN) return formen;
  const neu = mitFormIds(formen);
  const [x, y] = formMitte(neu[quelle]);
  neu.push({ typ: "kreis", x, y, r: bereinigen(durchmesser / 2), loch });
  return mittelpunktUebernehmen(neu, neu.length - 1, quelle);
}

/** Gleichmäßige Mittelpunktabstände; die beiden äußeren Formen bleiben stehen. */
export function gleichmaessigVerteilen(formen: Form[], auswahl: number[], a: Achse): Form[] {
  const k = a === "x" ? 0 : 1;
  const ids = [...new Set(auswahl)].filter(i => formen[i]).sort((i, j) => formMitte(formen[i])[k] - formMitte(formen[j])[k] || i - j);
  if (ids.length < 3) return formen;
  const start = formMitte(formen[ids[0]])[k];
  const schritt = (formMitte(formen[ids.at(-1)!])[k] - start) / (ids.length - 1);
  const neu = [...formen];
  ids.forEach((i, n) => {
    const delta = start + n * schritt - formMitte(formen[i])[k];
    neu[i] = positionLoesen(verschieben(formen[i], a === "x" ? delta : 0, a === "y" ? delta : 0), [a]);
  });
  return positionenAufloesen(neu);
}
