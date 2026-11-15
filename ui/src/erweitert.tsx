/** Panels für Senkungen, Schrauben, Text, Seitenlöcher und Drehprofil im Zeichenblatt. */

import { useState } from "react";

import { OptZahlfeld, Zahlfeld } from "./felder";
import {
  kopfFelder,
  lochDurchmesser,
  SCHRAUBEN_NAMEN,
  schraubdom,
  STANDARD,
  zweckText,
  type Einstellungen,
  type Kopf,
  type Schraube,
  type Zweck,
} from "./schrauben";
import {
  aussenBox,
  bereinigen,
  gesamthoehe,
  polygonSelbstschnitt,
  textMasse,
  traghoehe,
  type Eigenteil,
  type Form,
  type Punkt,
  type SenkArt,
  type Seite,
  type Seitenloch,
} from "./zeichnen";

type KreisForm = Extract<Form, { typ: "kreis" }>;
type TextForm = Extract<Form, { typ: "text" }>;

const SENK_ARTEN: Array<[SenkArt, string]> = [
  ["keine", "keine"],
  ["senkung", "Senkung (90°, für Senkkopfschrauben)"],
  ["gegenbohrung", "Gegenbohrung (Zylinderkopf)"],
  ["sechskant", "Sechskant-Tasche (Mutter)"],
];

/** Senkung, Gegenbohrung oder Sechskant-Tasche an einem runden Loch. */
export function SenkPanel({ form, onChange }: { form: KreisForm; onChange: (patch: Record<string, number | string | undefined>) => void }) {
  const art = form.senk_art ?? "keine";
  const d = form.r * 2;
  return (
    <div className="senk" data-testid="senk-panel">
      <label>
        Senkung am Loch
        <select
          data-testid="senk-art"
          value={art}
          onChange={(e) => {
            const neu = e.target.value as SenkArt;
            if (neu === "keine") return onChange({ senk_art: undefined, senk_d_mm: undefined, senk_t_mm: undefined, senk_seite: undefined });
            onChange({
              senk_art: neu,
              senk_d_mm: form.senk_d_mm ?? bereinigen(neu === "sechskant" ? d * 1.7 : d * 2),
              senk_t_mm: neu === "senkung" ? undefined : form.senk_t_mm ?? 3,
              senk_seite: form.senk_seite ?? "oben",
            });
          }}
        >
          {SENK_ARTEN.map(([wert, titel]) => (
            <option key={wert} value={wert}>{titel}</option>
          ))}
        </select>
      </label>
      {art !== "keine" && (
        <>
          <Zahlfeld
            label={art === "sechskant" ? "Schlüsselweite (mm)" : "Durchmesser der Senkung (mm)"}
            wert={form.senk_d_mm ?? 0}
            testid="senk-d"
            onChange={(v) => onChange({ senk_d_mm: v })}
          />
          {art === "senkung" ? (
            <p className="leise" data-testid="senk-tiefe-info">
              Tiefe ergibt sich aus 90°: {bereinigen(Math.max(0, ((form.senk_d_mm ?? d) - d) / 2))} mm
            </p>
          ) : (
            <Zahlfeld label="Tiefe (mm)" wert={form.senk_t_mm ?? 0} testid="senk-t" onChange={(v) => onChange({ senk_t_mm: v })} />
          )}
          <label>
            Seite
            <select data-testid="senk-seite" value={form.senk_seite ?? "oben"} onChange={(e) => onChange({ senk_seite: e.target.value })}>
              <option value="oben">oben (Oberseite des Teils)</option>
              <option value="unten">unten (auf dem Druckbett)</option>
            </select>
          </label>
        </>
      )}
    </div>
  );
}

/** Text: Inhalt und Schrifthöhe. Die Schrift ist eine 5×7-Pixelschrift (ein Pixel = Schrifthöhe / 7). */
export function TextPanel({ form, onChange }: { form: TextForm; onChange: (patch: Record<string, number | string | undefined>) => void }) {
  const { b, t } = textMasse(form.text, form.schrift_mm);
  return (
    <div data-testid="text-panel">
      <label>
        Text
        <input data-testid="text-inhalt" value={form.text} maxLength={40} onChange={(e) => onChange({ text: e.target.value })} />
      </label>
      <Zahlfeld label="Schrifthöhe (mm, mindestens 2,8)" wert={form.schrift_mm} testid="text-schrift" onChange={(v) => onChange({ schrift_mm: v })} />
      <Zahlfeld label="Links x" wert={form.x} onChange={(v) => onChange({ x: v })} />
      <Zahlfeld label="Unten y" wert={form.y} onChange={(v) => onChange({ y: v })} />
      <p className="leise">
        {b} × {t} mm. Großbuchstaben, Ziffern und . , : / + = ( ) ! ? % -; Ä Ö Ü ß werden zu AE OE UE SS. Pixel unter 0,4 mm druckt kein Drucker sauber.
      </p>
    </div>
  );
}

const SEITEN: Array<[Seite, string]> = [
  ["vorne", "vorne (y klein)"],
  ["hinten", "hinten (y groß)"],
  ["links", "links (x klein)"],
  ["rechts", "rechts (x groß)"],
];

/** Bohrungen und Schlitze von der Seite durch die Wand. */
export function SeitenlochPanel({ teil, onChange }: { teil: Eigenteil; onChange: (neu: Seitenloch[]) => void }) {
  const liste = teil.seitenloecher ?? [];
  const box = aussenBox(teil);
  const hoehe = gesamthoehe(teil);

  function hinzu() {
    const mitteX = box ? (box[0] + box[2]) / 2 : 10;
    onChange([...liste, { seite: "vorne", art: "rund", pos_mm: bereinigen(mitteX), z_mm: bereinigen(hoehe / 2), d_mm: 4, tiefe_mm: 0 }]);
  }

  function aendern(i: number, patch: Partial<Seitenloch>) {
    onChange(liste.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  return (
    <div data-testid="seitenloch-panel">
      <h2>Seitenlöcher</h2>
      <p className="leise">Bohrung oder Schlitz von der Seite durch die Wand. Position entlang der Wand, Höhe von der Unterseite, Tiefe 0 = ganz durch.</p>
      {liste.map((l, i) => (
        <fieldset key={i} className="seitenloch" data-testid={`seitenloch-${i}`}>
          <legend>Seitenloch {i + 1}</legend>
          <label>
            Wand
            <select
              data-testid={`sl-seite-${i}`}
              value={l.seite}
              onChange={(e) => {
                const seite = e.target.value as Seite;
                const quer = seite === "links" || seite === "rechts";
                const mitte = box ? (quer ? (box[1] + box[3]) / 2 : (box[0] + box[2]) / 2) : l.pos_mm;
                aendern(i, { seite, pos_mm: bereinigen(mitte) });
              }}
            >
              {SEITEN.map(([wert, titel]) => (
                <option key={wert} value={wert}>{titel}</option>
              ))}
            </select>
          </label>
          <label>
            Form
            <select
              data-testid={`sl-art-${i}`}
              value={l.art}
              onChange={(e) => aendern(i, e.target.value === "rund" ? { art: "rund", d_mm: l.d_mm ?? 4 } : { art: "schlitz", b_mm: l.b_mm ?? 8, h_mm: l.h_mm ?? 3 })}
            >
              <option value="rund">Bohrung</option>
              <option value="schlitz">Schlitz (Rechteck)</option>
            </select>
          </label>
          <Zahlfeld label={l.seite === "links" || l.seite === "rechts" ? "Position y (mm)" : "Position x (mm)"} wert={l.pos_mm} testid={`sl-pos-${i}`} onChange={(v) => aendern(i, { pos_mm: v })} />
          <Zahlfeld label="Höhe der Mitte (mm)" wert={l.z_mm} testid={`sl-z-${i}`} onChange={(v) => aendern(i, { z_mm: v })} />
          {l.art === "rund" ? (
            <Zahlfeld label="Durchmesser (mm)" wert={l.d_mm ?? 0} testid={`sl-d-${i}`} onChange={(v) => aendern(i, { d_mm: v })} />
          ) : (
            <>
              <Zahlfeld label="Breite entlang der Wand (mm)" wert={l.b_mm ?? 0} testid={`sl-b-${i}`} onChange={(v) => aendern(i, { b_mm: v })} />
              <Zahlfeld label="Höhe des Schlitzes (mm)" wert={l.h_mm ?? 0} testid={`sl-h-${i}`} onChange={(v) => aendern(i, { h_mm: v })} />
            </>
          )}
          <OptZahlfeld label="Tiefe (mm, leer = durch)" wert={l.tiefe_mm || undefined} testid={`sl-tiefe-${i}`} onChange={(v) => aendern(i, { tiefe_mm: v ?? 0 })} />
          <button type="button" data-testid={`sl-loeschen-${i}`} onClick={() => onChange(liste.filter((_, j) => j !== i))}>
            Entfernen
          </button>
        </fieldset>
      ))}
      <button type="button" data-testid="seitenloch-neu" onClick={hinzu} disabled={!box}>
        Seitenloch hinzufügen
      </button>
    </div>
  );
}

const PROFIL_VORLAGEN: Array<{ id: string; titel: string; punkte: Punkt[] }> = [
  { id: "knopf", titel: "Knopf", punkte: [[0, 0], [15, 0], [15, 12], [13, 14], [0, 14]] },
  { id: "huelse", titel: "Hülse", punkte: [[4, 0], [8, 0], [8, 15], [4, 15]] },
  { id: "rolle", titel: "Rolle mit Bund", punkte: [[0, 0], [12, 0], [12, 3], [8, 3], [8, 13], [12, 13], [12, 16], [0, 16]] },
  { id: "kegel", titel: "Kegelstumpf", punkte: [[0, 0], [14, 0], [6, 20], [0, 20]] },
];

/** Drehteil: Profil aus Punkten (Radius, Höhe), das um eine senkrechte Achse gedreht wird. */
export function ProfilPanel({ teil, onChange }: { teil: Eigenteil; onChange: (patch: Partial<Eigenteil>) => void }) {
  const profil = teil.profil ?? [];

  function setzen(punkte: Punkt[]) {
    const r = punkte.length ? Math.max(...punkte.map((p) => p[0])) : 0;
    onChange({ profil: punkte, dreh_x_mm: Math.max(teil.dreh_x_mm ?? 0, r), dreh_y_mm: Math.max(teil.dreh_y_mm ?? 0, r) });
  }

  if (profil.length === 0) {
    return (
      <div data-testid="profil-panel">
        <h2>Drehteil</h2>
        <p className="leise">Ein Profil um eine Achse drehen (Knopf, Hülse, Rolle). Formen und Löcher lassen sich zusätzlich zeichnen.</p>
        <div className="knopfzeile">
          {PROFIL_VORLAGEN.map((v) => (
            <button key={v.id} type="button" data-testid={`profil-${v.id}`} onClick={() => setzen(v.punkte.map((p) => [...p] as Punkt))}>
              {v.titel}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const rmax = Math.max(...profil.map((p) => p[0]), 1);
  const zmax = Math.max(...profil.map((p) => p[1]), 1);
  const massstab = 120 / Math.max(rmax * 2, zmax);
  const pt = (r: number, z: number) => `${(rmax + r) * massstab + 6},${(zmax - z) * massstab + 6}`;
  const spiegel = profil.map((p) => pt(-p[0], p[1])).join(" ");
  const original = profil.map((p) => pt(p[0], p[1])).join(" ");
  const schnitt = polygonSelbstschnitt(profil);

  return (
    <div data-testid="profil-panel">
      <h2>Drehteil</h2>
      <svg width={rmax * 2 * massstab + 12} height={zmax * massstab + 12} role="img" aria-label="Profilvorschau (Schnitt)" style={{ background: "#fff", border: "1px solid #e4ddd0", borderRadius: 8 }}>
        <polygon points={spiegel} fill="rgba(0,174,66,0.18)" stroke="#00AE42" strokeWidth={1} />
        <polygon points={original} fill="rgba(0,174,66,0.35)" stroke="#00AE42" strokeWidth={1.5} />
        <line x1={rmax * massstab + 6} y1={0} x2={rmax * massstab + 6} y2={zmax * massstab + 12} stroke="#999" strokeDasharray="3 3" />
      </svg>
      {schnitt && <p style={{ color: "#b3434b" }} data-testid="profil-selbstschnitt">Das Profil überschneidet sich selbst. Der Export lehnt es ab.</p>}
      <ol className="profilpunkte">
        {profil.map((p, i) => (
          <li key={i} style={{ display: "flex", gap: 6, alignItems: "end" }}>
            <Zahlfeld label={`${i + 1}  Radius`} wert={p[0]} testid={`profil-r-${i}`} onChange={(v) => setzen(profil.map((q, j) => (j === i ? ([Math.max(0, v), q[1]] as Punkt) : q)))} />
            <Zahlfeld label="Höhe" wert={p[1]} testid={`profil-z-${i}`} onChange={(v) => setzen(profil.map((q, j) => (j === i ? ([q[0], Math.max(0, v)] as Punkt) : q)))} />
            <button type="button" aria-label={`Profilpunkt ${i + 1} löschen`} disabled={profil.length <= 3} onClick={() => setzen(profil.filter((_, j) => j !== i))}>
              ×
            </button>
          </li>
        ))}
      </ol>
      <button
        type="button"
        data-testid="profil-punkt-neu"
        onClick={() => {
          const a = profil[profil.length - 1];
          const b = profil[0];
          setzen([...profil, [bereinigen((a[0] + b[0]) / 2), bereinigen((a[1] + b[1]) / 2)]]);
        }}
      >
        Punkt am Ende einfügen
      </button>
      <Zahlfeld label="Achse x (mm)" wert={teil.dreh_x_mm ?? 0} testid="dreh-x" onChange={(v) => onChange({ dreh_x_mm: v })} />
      <Zahlfeld label="Achse y (mm)" wert={teil.dreh_y_mm ?? 0} testid="dreh-y" onChange={(v) => onChange({ dreh_y_mm: v })} />
      <p className="leise">Punkte laufen um die Fläche, Radius 0 liegt auf der Achse. Achse so setzen, dass das Teil nicht über x = 0 und y = 0 hinausragt.</p>
      <button type="button" data-testid="profil-entfernen" onClick={() => onChange({ profil: [] })}>
        Drehprofil entfernen
      </button>
    </div>
  );
}

const ZWECKE: Array<[Zweck, string]> = [
  ["durchgang", "Durchgangsloch (Schraube frei)"],
  ["kern", "Kernloch (Gewinde schneiden)"],
  ["einsatz", "Gewindeeinsatz (einschmelzen)"],
];

/** Gemeinsame Auswahl für Schraubenloch und Dom: Größe, Zweck, Zuschlag. */
function SchraubenWahl({
  groesse,
  zweck,
  einst,
  onGroesse,
  onZweck,
  onEinst,
  testPrefix,
}: {
  groesse: Schraube;
  zweck: Zweck;
  einst: Einstellungen;
  onGroesse: (g: Schraube) => void;
  onZweck: (z: Zweck) => void;
  onEinst: (e: Einstellungen) => void;
  testPrefix: string;
}) {
  const d = lochDurchmesser(groesse, zweck, einst);
  return (
    <>
      <label>
        Schraube
        <select data-testid={`${testPrefix}-groesse`} value={groesse} onChange={(e) => onGroesse(e.target.value as Schraube)}>
          {SCHRAUBEN_NAMEN.map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </label>
      <label>
        Zweck
        <select data-testid={`${testPrefix}-zweck`} value={zweck} onChange={(e) => onZweck(e.target.value as Zweck)}>
          {ZWECKE.map(([wert, titel]) => (
            <option key={wert} value={wert}>{titel}</option>
          ))}
        </select>
      </label>
      {zweck !== "einsatz" ? (
        <Zahlfeld label="Zuschlag fürs Drucken (mm)" wert={einst.zuschlag} testid={`${testPrefix}-zuschlag`} onChange={(v) => onEinst({ ...einst, zuschlag: Math.max(0, v) })} />
      ) : (
        <Zahlfeld label="Abzug vom Einsatz-Außendurchmesser (mm)" wert={einst.einsatzAbzug} testid={`${testPrefix}-abzug`} onChange={(v) => onEinst({ ...einst, einsatzAbzug: Math.max(0, v) })} />
      )}
      <p className="leise" data-testid={`${testPrefix}-info`}>
        Lochdurchmesser {d} mm. {zweckText(zweck)} Nicht gedruckt geprüft.
      </p>
    </>
  );
}

/** Schraubenloch voreinstellen: setzt Durchmesser und bei Durchgangslöchern auf Wunsch Senk- oder Zylinderkopf. */
export function SchraubenPanel({ form, onChange }: { form: KreisForm; onChange: (patch: Record<string, number | string | undefined>) => void }) {
  const [groesse, setGroesse] = useState<Schraube>("M3");
  const [zweck, setZweck] = useState<Zweck>("durchgang");
  const [kopf, setKopf] = useState<Kopf>("ohne");
  const [einst, setEinst] = useState<Einstellungen>(STANDARD);
  return (
    <details className="schrauben" data-testid="schrauben-panel">
      <summary>Schraubenloch voreinstellen</summary>
      <SchraubenWahl groesse={groesse} zweck={zweck} einst={einst} onGroesse={setGroesse} onZweck={setZweck} onEinst={setEinst} testPrefix="schr" />
      {zweck === "durchgang" && (
        <label>
          Kopf
          <select data-testid="schr-kopf" value={kopf} onChange={(e) => setKopf(e.target.value as Kopf)}>
            <option value="ohne">ohne Versenkung</option>
            <option value="senk">Senkkopf (90°)</option>
            <option value="zylinder">Zylinderkopf (Gegenbohrung)</option>
          </select>
        </label>
      )}
      <button
        type="button"
        data-testid="schr-anwenden"
        onClick={() => {
          const patch: Record<string, number | string | undefined> = { r: Math.round((lochDurchmesser(groesse, zweck, einst) / 2) * 1000) / 1000 };
          if (zweck === "durchgang") {
            const k = kopfFelder(groesse, kopf, einst);
            Object.assign(patch, { senk_art: k.senk_art === "keine" ? undefined : k.senk_art, senk_d_mm: k.senk_d_mm, senk_t_mm: k.senk_t_mm, senk_seite: k.senk_seite });
          }
          onChange(patch);
        }}
      >
        Auf dieses Loch anwenden (jetzt Ø {Math.round(form.r * 2 * 100) / 100} mm)
      </button>
    </details>
  );
}

/** Schraubdom: Zylinder mit Schraubenloch auf der Platte. */
export function DomPanel({ teil, onAdd }: { teil: Eigenteil; onAdd: (formen: Form[]) => void }) {
  const box = aussenBox(teil);
  const [groesse, setGroesse] = useState<Schraube>("M3");
  const [zweck, setZweck] = useState<Zweck>("kern");
  const [einst, setEinst] = useState<Einstellungen>(STANDARD);
  const [x, setX] = useState<number | null>(null);
  const [y, setY] = useState<number | null>(null);
  const [hoehe, setHoehe] = useState(8);
  const [wand, setWand] = useState(1.6);
  const [tiefe, setTiefe] = useState<number | undefined>(undefined);
  const px = x ?? (box ? Math.round((box[0] + box[2]) / 2) : 10);
  const py = y ?? (box ? Math.round((box[1] + box[3]) / 2) : 10);
  const fuss = traghoehe(teil, [px, py]);
  return (
    <details className="dom" data-testid="dom-panel">
      <summary>Schraubdom hinzufügen</summary>
      <p className="leise">Ein Zylinder mit Schraubenloch, der auf der Platte steht. Fußhöhe ist die Oberseite der Form unter dem Dom.</p>
      <SchraubenWahl groesse={groesse} zweck={zweck} einst={einst} onGroesse={setGroesse} onZweck={setZweck} onEinst={setEinst} testPrefix="dom" />
      <Zahlfeld label="Mitte x (mm)" wert={px} testid="dom-x" onChange={setX} />
      <Zahlfeld label="Mitte y (mm)" wert={py} testid="dom-y" onChange={setY} />
      <Zahlfeld label="Höhe des Doms (mm)" wert={hoehe} testid="dom-hoehe" onChange={(v) => setHoehe(Math.max(1, v))} />
      <Zahlfeld label="Wand um das Loch (mm)" wert={wand} testid="dom-wand" onChange={(v) => setWand(Math.max(0.8, v))} />
      <OptZahlfeld label="Lochtiefe (mm, leer = ganze Domhöhe)" wert={tiefe} testid="dom-tiefe" onChange={setTiefe} />
      <p className="leise" data-testid="dom-masse">Fußhöhe {fuss} mm, Außendurchmesser {Math.round((lochDurchmesser(groesse, zweck, einst) + 2 * wand) * 100) / 100} mm.</p>
      <button type="button" data-testid="dom-hinzu" onClick={() => onAdd(schraubdom({ x: px, y: py, groesse, zweck, hoehe, fuss, wand, tiefe }, einst))}>
        Dom hinzufügen
      </button>
    </details>
  );
}
