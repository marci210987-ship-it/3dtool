import { useId, useMemo, useRef, useState } from "react";
import {
  aussenmass,
  Eigenteil,
  Form,
  kreisAus,
  neuesTeil,
  polygonAus,
  Punkt,
  rechteckAus,
  rechteckMm,
  runden,
  verschieben,
} from "./zeichnen";

type Werkzeug = "wahl" | "rechteck" | "kreis" | "polygon";

interface Entwurf {
  typ: "rechteck" | "kreis";
  a: Punkt;
  b: Punkt;
}

interface Ziehen {
  index: number;
  start: Punkt;
  original: Form;
}

const WERKZEUGE: Array<{ id: Werkzeug; titel: string; hilfe: string }> = [
  { id: "wahl", titel: "Auswählen / Verschieben", hilfe: "Form anklicken, ziehen zum Verschieben. Entf löscht." },
  { id: "rechteck", titel: "Rechteck", hilfe: "Mit gedrückter Maustaste von Ecke zu Ecke ziehen." },
  { id: "kreis", titel: "Kreis", hilfe: "Vom Mittelpunkt nach außen ziehen." },
  { id: "polygon", titel: "Vieleck", hilfe: "Punkte anklicken. Klick auf den ersten Punkt, Enter oder „Fertig“ schließt die Form." },
];

const RASTER_AUSWAHL = [0.1, 0.5, 1, 5, 10];

export interface Lageplan {
  breite: number;
  tiefe: number;
  platten: Array<{ links_mm: number; vorne_mm: number; breite_mm: number; tiefe_mm: number }>;
  boxen: Array<{ id: string; links_mm: number; vorne_mm: number; breite_mm: number; tiefe_mm: number }>;
}

export function Zeichnen({
  teile,
  onChange: onChangeProp,
  fehler,
  lageplan = null,
}: {
  teile: Eigenteil[];
  onChange: (teile: Eigenteil[]) => void;
  fehler: string[];
  lageplan?: Lageplan | null;
}) {
  const maskenId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const svgRef = useRef<SVGSVGElement>(null);
  const [aktivId, setAktivId] = useState<string>(teile[0]?.id ?? "");
  const [werkzeug, setWerkzeug] = useState<Werkzeug>("rechteck");
  const [loch, setLoch] = useState(false);
  const [raster, setRaster] = useState(1);
  const [entwurf, setEntwurf] = useState<Entwurf | null>(null);
  const [polyPunkte, setPolyPunkte] = useState<Punkt[]>([]);
  const [zeiger, setZeiger] = useState<Punkt | null>(null);
  const [auswahl, setAuswahl] = useState<number | null>(null);
  const [ziehen, setZiehen] = useState<Ziehen | null>(null);

  const teil = teile.find((t) => t.id === aktivId) ?? teile[0] ?? null;

  // Verlauf für Rückgängig/Wiederholen: ganze Teilelisten als Schnappschüsse.
  const vergangen = useRef<Eigenteil[][]>([]);
  const zukunft = useRef<Eigenteil[][]>([]);
  const letzteEingabe = useRef(0);

  function merke() {
    vergangen.current.push(teile);
    if (vergangen.current.length > 100) vergangen.current.shift();
    zukunft.current = [];
  }

  function onChange(neu: Eigenteil[], art: "einmal" | "zug" | "tippen" = "einmal") {
    if (art === "einmal") {
      merke();
    } else if (art === "tippen") {
      const jetzt = Date.now();
      if (jetzt - letzteEingabe.current > 800) merke();
      letzteEingabe.current = jetzt;
    }
    onChangeProp(neu);
  }

  function rueckgaengig() {
    const vor = vergangen.current.pop();
    if (!vor) return;
    zukunft.current.push(teile);
    onChangeProp(vor);
    setAuswahl(null);
    abbrechen();
  }

  function wiederholen() {
    const nach = zukunft.current.pop();
    if (!nach) return;
    vergangen.current.push(teile);
    onChangeProp(nach);
    setAuswahl(null);
    abbrechen();
  }

  const ausdehnung = useMemo(() => {
    let mx = 0;
    let my = 0;
    for (const f of teil?.formen ?? []) {
      if (f.typ === "rechteck") {
        mx = Math.max(mx, f.x + f.b);
        my = Math.max(my, f.y + f.t);
      } else if (f.typ === "kreis") {
        mx = Math.max(mx, f.x + f.r);
        my = Math.max(my, f.y + f.r);
      } else {
        for (const [x, y] of f.punkte) {
          mx = Math.max(mx, x);
          my = Math.max(my, y);
        }
      }
    }
    const rund = (v: number) => Math.max(120, Math.ceil((v + 20) / 10) * 10);
    return { w: rund(mx), h: rund(my) };
  }, [teil]);
  const W = ausdehnung.w;
  const H = ausdehnung.h;

  function aendereTeil(fn: (t: Eigenteil) => Eigenteil, art: "einmal" | "zug" | "tippen" = "einmal") {
    if (!teil) return;
    onChange(teile.map((t) => (t.id === teil.id ? fn(t) : t)), art);
  }

  function formen(neu: Form[], art: "einmal" | "zug" | "tippen" = "einmal") {
    aendereTeil((t) => ({ ...t, formen: neu }), art);
  }

  function welt(e: { clientX: number; clientY: number }): Punkt {
    const svg = svgRef.current;
    if (!svg) return [0, 0];
    const m = svg.getScreenCTM();
    if (!m) return [0, 0];
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const p = pt.matrixTransform(m.inverse());
    return [Math.max(0, runden(p.x, raster)), Math.max(0, runden(H - p.y, raster))];
  }

  function polygonFertig() {
    if (!teil) return;
    const form = polygonAus(polyPunkte, loch);
    setPolyPunkte([]);
    if (form) {
      formen([...teil.formen, form]);
      setAuswahl(teil.formen.length);
    }
  }

  function abbrechen() {
    setEntwurf(null);
    setPolyPunkte([]);
    setZiehen(null);
  }

  function runter(e: React.PointerEvent<SVGSVGElement>) {
    if (!teil) return;
    const p = welt(e);
    if (werkzeug === "rechteck" || werkzeug === "kreis") {
      svgRef.current?.setPointerCapture(e.pointerId);
      setEntwurf({ typ: werkzeug, a: p, b: p });
    } else if (werkzeug === "polygon") {
      const erster = polyPunkte[0];
      if (erster && polyPunkte.length >= 3 && Math.hypot(p[0] - erster[0], p[1] - erster[1]) <= Math.max(raster, 2)) {
        polygonFertig();
      } else {
        setPolyPunkte([...polyPunkte, p]);
      }
    } else {
      setAuswahl(null);
    }
  }

  function bewegt(e: React.PointerEvent<SVGSVGElement>) {
    const p = welt(e);
    setZeiger(p);
    if (entwurf) setEntwurf({ ...entwurf, b: p });
    if (ziehen && teil) {
      const neu = verschieben(ziehen.original, p[0] - ziehen.start[0], p[1] - ziehen.start[1]);
      formen(teil.formen.map((f, i) => (i === ziehen.index ? neu : f)), "zug");
    }
  }

  function hoch(e: React.PointerEvent<SVGSVGElement>) {
    if (ziehen) setZiehen(null);
    if (!entwurf || !teil) return;
    const form = entwurf.typ === "rechteck" ? rechteckAus(entwurf.a, welt(e), loch) : kreisAus(entwurf.a, welt(e), loch);
    setEntwurf(null);
    if (form) {
      formen([...teil.formen, form]);
      setAuswahl(teil.formen.length);
    }
  }

  function formGedrueckt(e: React.PointerEvent, index: number) {
    if (werkzeug !== "wahl" || !teil) return;
    e.stopPropagation();
    merke();
    svgRef.current?.setPointerCapture(e.pointerId);
    setAuswahl(index);
    setZiehen({ index, start: welt(e), original: teil.formen[index] });
  }

  function taste(e: React.KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) wiederholen();
      else rueckgaengig();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
      e.preventDefault();
      wiederholen();
      return;
    }
    if (e.key === "Escape") abbrechen();
    else if (e.key === "Enter" && werkzeug === "polygon") polygonFertig();
    else if ((e.key === "Delete" || e.key === "Backspace") && auswahl !== null && teil) {
      formen(teil.formen.filter((_, i) => i !== auswahl));
      setAuswahl(null);
    }
  }

  function setzeFeld(index: number, patch: Record<string, number | boolean>) {
    if (!teil) return;
    formen(teil.formen.map((f, i) => (i === index ? ({ ...f, ...patch } as Form) : f)), "tippen");
  }

  const maß = teil ? aussenmass(teil.formen) : null;
  const gewaehlt = teil && auswahl !== null ? teil.formen[auswahl] : null;
  const material = (teil?.formen ?? []).map((f, i) => ({ f, i })).filter((x) => !x.f.loch);
  const loecher = (teil?.formen ?? []).map((f, i) => ({ f, i })).filter((x) => x.f.loch);

  return (
    <div className="zeichnen" data-testid="zeichnen">
      <aside className="teileliste">
        <h2>Teile</h2>
        <ul>
          {teile.map((t) => (
            <li key={t.id}>
              <button type="button" className={t.id === teil?.id ? "aktiv" : ""} onClick={() => { setAktivId(t.id); setAuswahl(null); abbrechen(); }}>
                {t.id} · {t.name}
              </button>
            </li>
          ))}
        </ul>
        <div className="knopfzeile">
          <button
            type="button"
            data-testid="teil-neu"
            onClick={() => {
              const neu = neuesTeil(teile);
              onChange([...teile, neu]);
              setAktivId(neu.id);
              setAuswahl(null);
              abbrechen();
            }}
          >
            Neues Teil
          </button>
          {teil && (
            <button
              type="button"
              onClick={() => {
                const kopie = { ...neuesTeil(teile), name: `${teil.name} (Kopie)`, hoehe_mm: teil.hoehe_mm, boden_mm: teil.boden_mm, anzahl: teil.anzahl, formen: teil.formen.map((f) => ({ ...f })) as Form[] };
                onChange([...teile, kopie]);
                setAktivId(kopie.id);
              }}
            >
              Duplizieren
            </button>
          )}
          {teil && (
            <button
              type="button"
              onClick={() => {
                const rest = teile.filter((t) => t.id !== teil.id);
                onChange(rest);
                setAktivId(rest[0]?.id ?? "");
                setAuswahl(null);
              }}
            >
              Löschen
            </button>
          )}
        </div>
      </aside>

      {!teil && <p className="leise">Noch kein Teil. „Neues Teil“ anlegen und zeichnen.</p>}

      {teil && (
        <>
          <div className="zeichenflaeche">
            <div className="werkzeuge" role="toolbar" aria-label="Zeichenwerkzeuge">
              {WERKZEUGE.map((w) => (
                <button key={w.id} type="button" className={werkzeug === w.id ? "aktiv" : ""} data-testid={`werkzeug-${w.id}`} title={w.hilfe} onClick={() => { setWerkzeug(w.id); abbrechen(); }}>
                  {w.titel}
                </button>
              ))}
              <button type="button" data-testid="rueckgaengig" disabled={vergangen.current.length === 0} onClick={rueckgaengig} title="Strg+Z">
                Rückgängig
              </button>
              <button type="button" data-testid="wiederholen" disabled={zukunft.current.length === 0} onClick={wiederholen} title="Strg+Y">
                Wiederholen
              </button>
              <label className="check">
                <input type="checkbox" data-testid="loch-modus" checked={loch} onChange={(e) => setLoch(e.target.checked)} />
                Neue Form ist ein Loch
              </label>
              <label className="check">
                Raster
                <select value={raster} onChange={(e) => setRaster(Number(e.target.value))}>
                  {RASTER_AUSWAHL.map((r) => (
                    <option key={r} value={r}>{r} mm</option>
                  ))}
                </select>
              </label>
              {werkzeug === "polygon" && polyPunkte.length >= 3 && (
                <button type="button" onClick={polygonFertig}>Fertig</button>
              )}
            </div>
            <p className="leise">{WERKZEUGE.find((w) => w.id === werkzeug)?.hilfe}</p>
            <svg
              ref={svgRef}
              data-testid="zeichenblatt"
              viewBox={`0 0 ${W} ${H}`}
              tabIndex={0}
              onPointerDown={runter}
              onPointerMove={bewegt}
              onPointerUp={hoch}
              onKeyDown={taste}
              style={{ touchAction: "none", width: "100%", maxHeight: 560, background: "#fff", border: "1px solid #e4ddd0", borderRadius: 12 }}
            >
              <defs>
                <mask id={`m${maskenId}`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
                  <rect x={0} y={0} width={W} height={H} fill="#fff" />
                  <g fill="#000">{loecher.map(({ f, i }) => (<g key={i}>{formElement(f)}</g>))}</g>
                </mask>
              </defs>
              {Array.from({ length: Math.floor(W / 10) + 1 }, (_, i) => (
                <line key={`v${i}`} x1={i * 10} y1={0} x2={i * 10} y2={H} stroke={i % 5 === 0 ? "#cfc7b6" : "#eee8dc"} strokeWidth={i % 5 === 0 ? 0.4 : 0.25} />
              ))}
              {Array.from({ length: Math.floor(H / 10) + 1 }, (_, i) => (
                <line key={`h${i}`} x1={0} y1={H - i * 10} x2={W} y2={H - i * 10} stroke={i % 5 === 0 ? "#cfc7b6" : "#eee8dc"} strokeWidth={i % 5 === 0 ? 0.4 : 0.25} />
              ))}
              <g transform={`translate(0 ${H}) scale(1 -1)`}>
                <g mask={`url(#m${maskenId})`} fill="#9fd0cb" stroke="#0f6e6e" strokeWidth={0.5}>
                  {material.map(({ f, i }) => (
                    <g key={i} onPointerDown={(e) => formGedrueckt(e, i)} style={{ cursor: werkzeug === "wahl" ? "move" : "crosshair" }} data-testid={`form-${i}`}>
                      {formElement(f)}
                    </g>
                  ))}
                </g>
                <g fill="rgba(231,163,168,0.25)" stroke="#b3434b" strokeWidth={0.5} strokeDasharray="2 1.5">
                  {loecher.map(({ f, i }) => (
                    <g key={i} onPointerDown={(e) => formGedrueckt(e, i)} style={{ cursor: werkzeug === "wahl" ? "move" : "crosshair" }} data-testid={`form-${i}`}>
                      {formElement(f)}
                    </g>
                  ))}
                </g>
                {gewaehlt && (
                  <g fill="none" stroke="#1c1915" strokeWidth={0.9} pointerEvents="none">
                    {formElement(gewaehlt)}
                  </g>
                )}
                {entwurf && (
                  <g fill="none" stroke="#1c1915" strokeDasharray="2 1" strokeWidth={0.6} pointerEvents="none">
                    {entwurf.typ === "rechteck"
                      ? (() => { const f = rechteckAus(entwurf.a, entwurf.b, loch); return f ? formElement(f) : null; })()
                      : (() => { const f = kreisAus(entwurf.a, entwurf.b, loch); return f ? formElement(f) : null; })()}
                  </g>
                )}
                {polyPunkte.length > 0 && (
                  <g fill="none" stroke="#1c1915" strokeWidth={0.6} pointerEvents="none">
                    <polyline points={[...polyPunkte, ...(zeiger ? [zeiger] : [])].map((p) => p.join(",")).join(" ")} />
                    {polyPunkte.map((p, i) => (<circle key={i} cx={p[0]} cy={p[1]} r={1.2} fill="#1c1915" />))}
                  </g>
                )}
              </g>
            </svg>
            <p className="leise" data-testid="zeigerinfo">
              {zeiger ? `Zeiger: ${zeiger[0]} / ${zeiger[1]} mm` : "Ursprung links unten, Maße in Millimeter."}
              {entwurf?.typ === "rechteck" && ` · ${Math.abs(entwurf.b[0] - entwurf.a[0]).toFixed(1)} × ${Math.abs(entwurf.b[1] - entwurf.a[1]).toFixed(1)} mm`}
              {entwurf?.typ === "kreis" && ` · Ø ${(2 * Math.hypot(entwurf.b[0] - entwurf.a[0], entwurf.b[1] - entwurf.a[1])).toFixed(1)} mm`}
            </p>
          </div>

          <div className="eigenschaften">
            <h2>Eigenschaften</h2>
            <label>
              Name
              <input data-testid="teil-name" value={teil.name} onChange={(e) => aendereTeil((t) => ({ ...t, name: e.target.value }), "tippen")} />
            </label>
            <Zahlfeld label="Höhe (mm)" wert={teil.hoehe_mm} testid="teil-hoehe" onChange={(v) => aendereTeil((t) => ({ ...t, hoehe_mm: v }), "tippen")} />
            <Zahlfeld label="Boden unter Löchern (mm, 0 = durchgehend)" wert={teil.boden_mm} testid="teil-boden" onChange={(v) => aendereTeil((t) => ({ ...t, boden_mm: v }), "tippen")} />
            <Zahlfeld label="Anzahl" wert={teil.anzahl} onChange={(v) => aendereTeil((t) => ({ ...t, anzahl: Math.max(1, Math.round(v)) }), "tippen")} />
            <label>
              Obere Kante
              <select
                data-testid="kante-art"
                value={teil.kante_oben_art}
                onChange={(e) => aendereTeil((t) => ({ ...t, kante_oben_art: e.target.value as Eigenteil["kante_oben_art"], kante_oben_mm: e.target.value === "keine" ? 0 : t.kante_oben_mm || 1 }))}
              >
                <option value="keine">scharfkantig</option>
                <option value="fase">Fase</option>
                <option value="rund">Rundung</option>
              </select>
            </label>
            {teil.kante_oben_art !== "keine" && (
              <Zahlfeld label="Größe obere Kante (mm)" wert={teil.kante_oben_mm} testid="kante-mm" onChange={(v) => aendereTeil((t) => ({ ...t, kante_oben_mm: Math.max(0, v) }), "tippen")} />
            )}
            <Zahlfeld label="Fase unten (mm, gegen Elefantenfuß)" wert={teil.kante_unten_mm} testid="kante-unten" onChange={(v) => aendereTeil((t) => ({ ...t, kante_unten_mm: Math.max(0, v) }), "tippen")} />
            <p className="leise" data-testid="teil-mass">
              {maß ? `Außenmaß ${maß.breite} × ${maß.tiefe} × ${teil.hoehe_mm} mm` : "Noch keine Form, die Material hinzufügt."}
              {maß && (maß.breite > 256 || maß.tiefe > 256 || teil.hoehe_mm > 256) && " · passt nicht aufs Druckbett (256 mm)"}
            </p>

            {lageplan && maß && (
              <div data-testid="lageplan-bereich">
                <h2>In der Schublade</h2>
                <label className="check">
                  <input
                    type="checkbox"
                    data-testid="platziert"
                    checked={teil.platziert}
                    onChange={(e) => aendereTeil((t) => ({ ...t, platziert: e.target.checked }))}
                  />
                  In die Schublade stellen
                </label>
                {teil.platziert && (
                  <>
                    <Zahlfeld label="Position von links (mm)" wert={teil.x_mm} testid="teil-x" onChange={(v) => aendereTeil((t) => ({ ...t, x_mm: v }), "tippen")} />
                    <Zahlfeld label="Position von vorn (mm)" wert={teil.y_mm} testid="teil-y" onChange={(v) => aendereTeil((t) => ({ ...t, y_mm: v }), "tippen")} />
                    <button type="button" data-testid="teil-drehen" onClick={() => aendereTeil((t) => ({ ...t, drehung: (t.drehung + 90) % 180 }))}>
                      Um 90° drehen
                    </button>
                    <LageplanAnsicht plan={lageplan} teile={teile} aktivId={teil.id} onStart={merke} onMove={(x, y) => aendereTeil((t) => ({ ...t, x_mm: x, y_mm: y }), "zug")} />
                  </>
                )}
                <p className="hinweis">Das Teil steht auf der Platte. Es darf keine Box und kein anderes Teil überlappen.</p>
              </div>
            )}

            <h2>Formen</h2>
            {teil.formen.length === 0 && <p className="leise">Noch keine Formen.</p>}
            <ol className="formliste">
              {teil.formen.map((f, i) => (
                <li key={i} className={i === auswahl ? "aktiv" : ""}>
                  <button type="button" onClick={() => { setAuswahl(i); setWerkzeug("wahl"); }}>
                    {f.typ === "rechteck" ? "Rechteck" : f.typ === "kreis" ? "Kreis" : "Vieleck"} {f.loch ? "(Loch)" : ""}
                  </button>
                  <button type="button" aria-label={`Form ${i + 1} löschen`} onClick={() => { formen(teil.formen.filter((_, j) => j !== i)); setAuswahl(null); }}>
                    ×
                  </button>
                </li>
              ))}
            </ol>
            {gewaehlt && auswahl !== null && (
              <div className="formular">
                <label className="check">
                  <input type="checkbox" checked={gewaehlt.loch} onChange={(e) => setzeFeld(auswahl, { loch: e.target.checked })} />
                  Loch (schneidet Material weg)
                </label>
                {gewaehlt.typ === "rechteck" && (
                  <>
                    <Zahlfeld label="Links x" wert={gewaehlt.x} onChange={(v) => setzeFeld(auswahl, { x: v })} />
                    <Zahlfeld label="Unten y" wert={gewaehlt.y} onChange={(v) => setzeFeld(auswahl, { y: v })} />
                    <Zahlfeld label="Breite" wert={gewaehlt.b} onChange={(v) => setzeFeld(auswahl, { b: v })} />
                    <Zahlfeld label="Tiefe" wert={gewaehlt.t} onChange={(v) => setzeFeld(auswahl, { t: v })} />
                    <Zahlfeld label="Eckenradius (mm, 0 = eckig)" wert={gewaehlt.radius ?? 0} testid="form-radius" onChange={(v) => setzeFeld(auswahl, { radius: Math.max(0, v) })} />
                  </>
                )}
                {gewaehlt.typ === "kreis" && (
                  <>
                    <Zahlfeld label="Mitte x" wert={gewaehlt.x} onChange={(v) => setzeFeld(auswahl, { x: v })} />
                    <Zahlfeld label="Mitte y" wert={gewaehlt.y} onChange={(v) => setzeFeld(auswahl, { y: v })} />
                    <Zahlfeld label="Radius" wert={gewaehlt.r} onChange={(v) => setzeFeld(auswahl, { r: v })} />
                  </>
                )}
                {gewaehlt.typ === "polygon" && <p className="leise">{gewaehlt.punkte.length} Punkte. Zum Verschieben ziehen.</p>}
              </div>
            )}
            {fehler.length > 0 && (
              <div className="alarm" role="alert" data-testid="zeichnen-fehler">
                {fehler.map((f) => (<p key={f}>{f}</p>))}
              </div>
            )}
            <p className="hinweis">Das Teil wird als Grundkörper aus diesen Formen erzeugt (Draufsicht, gerade Extrusion). Rundungen gibt es für Rechteck-Ecken und für die obere Kante, eine Fase auch unten; Schrägen und Rundungen an Löchern gibt es nicht.</p>
          </div>
        </>
      )}
    </div>
  );
}

function formElement(f: Form) {
  if (f.typ === "rechteck") return <rect x={f.x} y={f.y} width={f.b} height={f.t} rx={f.radius || 0} ry={f.radius || 0} />;
  if (f.typ === "kreis") return <circle cx={f.x} cy={f.y} r={f.r} />;
  return <polygon points={f.punkte.map((p) => p.join(",")).join(" ")} />;
}

function Zahlfeld({ label, wert, onChange, testid }: { label: string; wert: number; onChange: (v: number) => void; testid?: string }) {
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

function LageplanAnsicht({
  plan,
  teile,
  aktivId,
  onStart,
  onMove,
}: {
  plan: Lageplan;
  teile: Eigenteil[];
  aktivId: string;
  onStart: () => void;
  onMove: (x: number, y: number) => void;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const [zug, setZug] = useState<{ dx: number; dy: number } | null>(null);
  const aktiv = teile.find((t) => t.id === aktivId);

  function punkt(e: React.PointerEvent): [number, number] {
    const svg = ref.current;
    const m = svg?.getScreenCTM();
    if (!svg || !m) return [0, 0];
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const p = pt.matrixTransform(m.inverse());
    return [p.x, p.y];
  }

  return (
    <svg
      ref={ref}
      data-testid="lageplan"
      viewBox={`0 0 ${plan.breite} ${plan.tiefe}`}
      style={{ touchAction: "none", width: "100%", background: "#fff", border: "1px solid #e4ddd0", borderRadius: 12 }}
      onPointerMove={(e) => {
        if (!zug) return;
        const [px, py] = punkt(e);
        onMove(Math.max(0, Math.round(px - zug.dx)), Math.max(0, Math.round(py - zug.dy)));
      }}
      onPointerUp={() => setZug(null)}
    >
      <rect x={0} y={0} width={plan.breite} height={plan.tiefe} fill="#fff" stroke="#1c1915" strokeWidth={1.2} />
      {plan.platten.map((p, i) => (
        <rect key={i} x={p.links_mm} y={p.vorne_mm} width={p.breite_mm} height={p.tiefe_mm} fill="none" stroke="#0f6e6e" strokeWidth={0.8} />
      ))}
      {plan.boxen.map((b) => (
        <rect key={b.id} x={b.links_mm} y={b.vorne_mm} width={b.breite_mm} height={b.tiefe_mm} fill="#f3d2a4" fillOpacity={0.85} stroke="#1c1915" strokeWidth={0.5} />
      ))}
      {teile.map((t) => {
        const r = t.platziert ? rechteckMm(t) : null;
        if (!r) return null;
        const istAktiv = t.id === aktivId;
        return (
          <g key={t.id}>
            <rect
              x={r.x}
              y={r.y}
              width={r.b}
              height={r.t}
              fill={istAktiv ? "#9fd0cb" : "#d9d2c3"}
              stroke="#1c1915"
              strokeWidth={istAktiv ? 1.2 : 0.5}
              style={{ cursor: istAktiv ? "move" : "default" }}
              data-testid={istAktiv ? "lageplan-teil" : undefined}
              onPointerDown={(e) => {
                if (!istAktiv || !aktiv) return;
                onStart();
                e.currentTarget.ownerSVGElement?.setPointerCapture(e.pointerId);
                const [px, py] = punkt(e);
                setZug({ dx: px - aktiv.x_mm, dy: py - aktiv.y_mm });
              }}
            />
            <text x={r.x + 2} y={r.y + 8} fontSize={7} fill="#1c1915" pointerEvents="none">{t.id}</text>
          </g>
        );
      })}
    </svg>
  );
}
