import { useId, useMemo, useRef, useState } from "react";
import { dateiText, type ImportErgebnis, leseDxf, leseSvg, zuFormen } from "./import";
import {
  aussenmass,
  ausrichten,
  type AusrichtModus,
  bezugsrahmen,
  einrasten,
  Eigenteil,
  abstandsvorschlag,
  fangpunkte,
  formMitte,
  gitter,
  kopieren,
  kreismuster,
  type MassFeld,
  masseSetzen,
  masswertText,
  laesstSichDrehen,
  MAX_FORMEN,
  reihe,
  spiegeln,
  type Form as FormTyp,
  gesamthoehe,
  hoehenanteil,
  Form,
  kreisAus,
  massangaben,
  neuesTeil,
  polygonAus,
  Punkt,
  rechteckAus,
  rechteckMm,
  runden,
  teilVonServer,
  VORLAGEN,
  neueTeilId,
  verschiebenMitFang,
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

export interface MeineVorlage {
  id: string;
  name: string;
  teil: Record<string, unknown>;
}

export function Zeichnen({
  teile,
  onChange: onChangeProp,
  fehler,
  lageplan = null,
  meineVorlagen = [],
  onVorlageSpeichern,
  onVorlageLoeschen,
}: {
  teile: Eigenteil[];
  onChange: (teile: Eigenteil[]) => void;
  fehler: string[];
  lageplan?: Lageplan | null;
  meineVorlagen?: MeineVorlage[];
  /** Gibt einen Fehlertext zurück oder null bei Erfolg. */
  onVorlageSpeichern?: (name: string, teil: Eigenteil) => Promise<string | null>;
  onVorlageLoeschen?: (id: string) => void;
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
  const [masseAn, setMasseAn] = useState(true);
  const [musterMeldung, setMusterMeldung] = useState("");
  const [vorlagenName, setVorlagenName] = useState("");
  const [vorlagenMeldung, setVorlagenMeldung] = useState("");
  const [masseEdit, setMasseEdit] = useState<{ index: number; feld: MassFeld; text: string; x: number; y: number } | null>(null);
  const [fangAn, setFangAn] = useState(true);
  const [fangLinien, setFangLinien] = useState<{ x?: number; y?: number }>({});

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

  /** Setzt ein Teil aus einer Vorlage oder Datei ein. Ein leeres aktives Teil wird ersetzt statt ergänzt. */
  function einsetzen(inhalt: Partial<Eigenteil>) {
    const leer = teil !== null && teil.formen.length === 0;
    const id = leer && teil ? teil.id : neueTeilId(teile);
    const eintrag = { ...neuesTeil(teile), ...inhalt, id } as Eigenteil;
    onChange(leer && teil ? teile.map((t) => (t.id === teil.id ? eintrag : t)) : [...teile, eintrag]);
    setAktivId(id);
    setAuswahl(null);
    abbrechen();
  }

  function aendereTeil(fn: (t: Eigenteil) => Eigenteil, art: "einmal" | "zug" | "tippen" = "einmal") {
    if (!teil) return;
    onChange(teile.map((t) => (t.id === teil.id ? fn(t) : t)), art);
  }

  function formen(neu: Form[], art: "einmal" | "zug" | "tippen" = "einmal") {
    aendereTeil((t) => ({ ...t, formen: neu }), art);
  }

  const fangSchwelle = Math.max(raster, W / 55);

  function welt(e: { clientX: number; clientY: number }, mitFang = true): Punkt {
    const svg = svgRef.current;
    if (!svg) return [0, 0];
    const m = svg.getScreenCTM?.();
    if (!m) return [0, 0];
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const p = pt.matrixTransform(m.inverse());
    const gerastet: Punkt = [Math.max(0, runden(p.x, raster)), Math.max(0, runden(H - p.y, raster))];
    if (!mitFang || !fangAn || !teil) return gerastet;
    const ziel = einrasten(gerastet, fangpunkte(teil.formen, ziehen ? ziehen.index : null), fangSchwelle);
    return ziel.punkt;
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
    const p = welt(e, !ziehen);
    setZeiger(p);
    if (entwurf) {
      setEntwurf({ ...entwurf, b: p });
      const f = fangAn ? einrasten(p, fangpunkte(teil?.formen ?? []), fangSchwelle) : null;
      setFangLinien({ x: f?.fangX, y: f?.fangY });
    }
    if (polyPunkte.length > 0 && fangAn) {
      const f = einrasten(p, fangpunkte(teil?.formen ?? []), fangSchwelle);
      setFangLinien({ x: f.fangX, y: f.fangY });
    }
    if (ziehen && teil) {
      let dx = p[0] - ziehen.start[0];
      let dy = p[1] - ziehen.start[1];
      if (fangAn) {
        const s = verschiebenMitFang(ziehen.original, dx, dy, teil.formen.filter((_, i) => i !== ziehen.index), fangSchwelle);
        dx = s.dx;
        dy = s.dy;
        setFangLinien({ x: s.fangX, y: s.fangY });
      }
      const neu = verschieben(ziehen.original, dx, dy);
      formen(teil.formen.map((f, i) => (i === ziehen.index ? neu : f)), "zug");
    }
  }

  function hoch(e: React.PointerEvent<SVGSVGElement>) {
    setFangLinien({});
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
    setZiehen({ index, start: welt(e, false), original: teil.formen[index] });
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

  function setzeFeld(index: number, patch: Record<string, number | boolean | string | undefined>) {
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
        <label>
          Aus Vorlage
          <select
            data-testid="vorlage"
            value=""
            onChange={(e) => {
              const eigene = e.target.value.startsWith("v:") ? meineVorlagen.find((m) => "v:" + m.id === e.target.value) : undefined;
              const vorlage = eigene ? undefined : VORLAGEN.find((v) => v.id === e.target.value);
              if (!vorlage && !eigene) return;
              einsetzen(
                eigene
                  ? { ...teilVonServer({ ...eigene.teil, id: "E" }), platziert: false, x_mm: 0, y_mm: 0, drehung: 0 }
                  : vorlage!.erzeuge(),
              );
            }}
          >
            <option value="">Vorlage wählen …</option>
            <optgroup label="Mitgelieferte Vorlagen">
              {VORLAGEN.map((v) => (
                <option key={v.id} value={v.id} title={v.text}>
                  {v.name}
                </option>
              ))}
            </optgroup>
            {meineVorlagen.length > 0 && (
              <optgroup label="Meine Vorlagen">
                {meineVorlagen.map((m) => (
                  <option key={m.id} value={"v:" + m.id}>
                    {m.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>
        <ImportPanel
          onEinfuegen={einsetzen}
        />
        {onVorlageSpeichern && teil && (
          <div className="vorlage-speichern" data-testid="vorlage-speichern">
            <label>
              Dieses Teil als Vorlage speichern
              <input
                data-testid="vorlage-name"
                value={vorlagenName}
                placeholder="Name der Vorlage"
                maxLength={60}
                onChange={(e) => setVorlagenName(e.target.value)}
              />
            </label>
            <button
              type="button"
              data-testid="vorlage-sichern"
              disabled={!vorlagenName.trim()}
              onClick={async () => {
                const fehlerText = await onVorlageSpeichern(vorlagenName, teil);
                setVorlagenMeldung(fehlerText ?? `„${vorlagenName.trim()}“ gespeichert.`);
                if (!fehlerText) setVorlagenName("");
              }}
            >
              Als Vorlage speichern
            </button>
            {vorlagenMeldung && <p className="leise" data-testid="vorlage-meldung">{vorlagenMeldung}</p>}
          </div>
        )}
        {meineVorlagen.length > 0 && onVorlageLoeschen && (
          <details className="meine-vorlagen">
            <summary>Meine Vorlagen verwalten</summary>
            <ul>
              {meineVorlagen.map((m) => (
                <li key={m.id}>
                  <span>{m.name}</span>
                  <button type="button" aria-label={`Vorlage ${m.name} löschen`} data-testid={`vorlage-loeschen-${m.id}`} onClick={() => onVorlageLoeschen(m.id)}>
                    ×
                  </button>
                </li>
              ))}
            </ul>
          </details>
        )}
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
                <input type="checkbox" data-testid="fang-an" checked={fangAn} onChange={(e) => setFangAn(e.target.checked)} />
                Einrasten
              </label>
              <label className="check">
                <input type="checkbox" data-testid="masse-an" checked={masseAn} onChange={(e) => setMasseAn(e.target.checked)} />
                Maße anzeigen
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
            <div style={{ position: "relative" }}>
            {masseEdit && (
              <input
                data-testid="masse-eingabe"
                className="masse-eingabe"
                autoFocus
                inputMode="decimal"
                value={masseEdit.text}
                aria-label="Neues Maß in Millimetern"
                style={masseEingabePosition(svgRef.current, masseEdit.x, H - masseEdit.y)}
                onFocus={(e) => e.currentTarget.select()}
                onChange={(e) => setMasseEdit({ ...masseEdit, text: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === "Escape") setMasseEdit(null);
                  if (e.key === "Enter") {
                    const form = teil.formen[masseEdit.index];
                    const neu = form ? masseSetzen(form, masseEdit.feld, masseEdit.text) : null;
                    if (neu) {
                      formen(teil.formen.map((f, i) => (i === masseEdit.index ? neu : f)));
                      setMasseEdit(null);
                    }
                  }
                }}
                onBlur={() => setMasseEdit(null)}
              />
            )}
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
                <g mask={`url(#m${maskenId})`} stroke="#00AE42" strokeWidth={0.5}>
                  {material.map(({ f, i }) => (
                    <g key={i} fill={hoehenFarbe(hoehenanteil(f, teil))} onPointerDown={(e) => formGedrueckt(e, i)} style={{ cursor: werkzeug === "wahl" ? "move" : "crosshair" }} data-testid={`form-${i}`}>
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
                  <g fill="none" stroke="#0F1F3A" strokeWidth={0.9} pointerEvents="none">
                    {formElement(gewaehlt)}
                  </g>
                )}
                {(fangLinien.x !== undefined || fangLinien.y !== undefined) && (
                  <g stroke="#d4572b" strokeWidth={0.35} strokeDasharray="1.5 1" pointerEvents="none" data-testid="fanglinien">
                    {fangLinien.x !== undefined && <line x1={fangLinien.x} y1={0} x2={fangLinien.x} y2={H} />}
                    {fangLinien.y !== undefined && <line x1={0} y1={fangLinien.y} x2={W} y2={fangLinien.y} />}
                  </g>
                )}
                {entwurf && (
                  <g fill="none" stroke="#0F1F3A" strokeDasharray="2 1" strokeWidth={0.6} pointerEvents="none">
                    {entwurf.typ === "rechteck"
                      ? (() => { const f = rechteckAus(entwurf.a, entwurf.b, loch); return f ? formElement(f) : null; })()
                      : (() => { const f = kreisAus(entwurf.a, entwurf.b, loch); return f ? formElement(f) : null; })()}
                  </g>
                )}
                {polyPunkte.length > 0 && (
                  <g fill="none" stroke="#0F1F3A" strokeWidth={0.6} pointerEvents="none">
                    <polyline points={[...polyPunkte, ...(zeiger ? [zeiger] : [])].map((p) => p.join(",")).join(" ")} />
                    {polyPunkte.map((p, i) => (<circle key={i} cx={p[0]} cy={p[1]} r={1.2} fill="#0F1F3A" />))}
                  </g>
                )}
              </g>
              {masseAn && (
                <g fontFamily="Segoe UI, sans-serif" fontSize={W / 38} pointerEvents="none" textAnchor="middle">
                  {[
                    ...teil.formen.map((f, i) => ({ f, aktiv: i === auswahl, index: i })),
                    ...(entwurf
                      ? [{ f: entwurf.typ === "rechteck" ? rechteckAus(entwurf.a, entwurf.b, loch) : kreisAus(entwurf.a, entwurf.b, loch), aktiv: true, index: -1 }]
                      : []),
                  ].flatMap(({ f, aktiv, index }, k) =>
                    f
                      ? massangaben(f, W / 40, aktiv).map((m, j) => (
                          <g key={`${k}-${j}`} data-testid="masse">
                            {m.linie && <line x1={m.linie[0]} y1={H - m.linie[1]} x2={m.linie[2]} y2={H - m.linie[3]} stroke={aktiv ? "#1c1915" : "#8a8272"} strokeWidth={0.3} />}
                            <text
                              x={m.x}
                              y={H - m.y + W / 110}
                              fill={aktiv ? "#1c1915" : "#6b6455"}
                              stroke="#fff"
                              strokeWidth={W / 150}
                              paintOrder="stroke"
                              data-testid={m.feld && index >= 0 ? `masse-${m.feld}` : undefined}
                              {...(m.feld && index >= 0 && !ziehen && !entwurf
                                ? {
                                    pointerEvents: "all" as const,
                                    style: { cursor: "text" },
                                    onPointerDown: (e: React.PointerEvent) => e.stopPropagation(),
                                    onClick: () => {
                                      if (!m.feld) return;
                                      setAuswahl(index);
                                      setMasseEdit({ index, feld: m.feld, text: masswertText(f, m.feld), x: m.x, y: m.y });
                                    },
                                  }
                                : {})}
                            >
                              {m.text}
                            </text>
                          </g>
                        ))
                      : [],
                  )}
                </g>
              )}
            </svg>
            </div>
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
            <Zahlfeld label="Standardhöhe (mm)" wert={teil.hoehe_mm} testid="teil-hoehe" onChange={(v) => aendereTeil((t) => ({ ...t, hoehe_mm: v }), "tippen")} />
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
              {maß ? `Außenmaß ${maß.breite} × ${maß.tiefe} × ${gesamthoehe(teil)} mm` : "Noch keine Form, die Material hinzufügt."}
              {maß && (maß.breite > 256 || maß.tiefe > 256 || gesamthoehe(teil) > 256) && " · passt nicht aufs Druckbett (256 mm)"}
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
                <OptZahlfeld
                  label={gewaehlt.loch ? "Loch ab Höhe (mm, leer = ab Boden)" : "Starthöhe (mm, leer = 0)"}
                  wert={gewaehlt.z_mm}
                  testid="form-z"
                  onChange={(v) => setzeFeld(auswahl, { z_mm: v })}
                />
                <OptZahlfeld
                  label={gewaehlt.loch ? "Lochtiefe (mm, leer = bis oben)" : "Höhe der Form (mm, leer = bis Teilhöhe)"}
                  wert={gewaehlt.h_mm}
                  testid="form-h"
                  onChange={(v) => setzeFeld(auswahl, { h_mm: v })}
                />
                <OptZahlfeld
                  label={gewaehlt.loch ? "Aufweitung nach oben, Senkung (mm)" : "Verjüngung nach oben (mm)"}
                  wert={gewaehlt.schraege_mm}
                  testid="form-schraege"
                  onChange={(v) => setzeFeld(auswahl, { schraege_mm: v })}
                />
                {gewaehlt.typ === "rechteck" && (
                  <>
                    <OptZahlfeld
                      label="Drehwinkel (°, gegen den Uhrzeigersinn, um die Mitte)"
                      wert={gewaehlt.winkel}
                      testid="form-winkel"
                      onChange={(v) => setzeFeld(auswahl, { winkel: v })}
                    />
                    <div className="knopfzeile">
                      <button type="button" data-testid="winkel-plus90" onClick={() => setzeFeld(auswahl, { winkel: (((gewaehlt.winkel ?? 0) + 90) % 360) || undefined })}>
                        +90°
                      </button>
                      <button type="button" data-testid="winkel-plus15" onClick={() => setzeFeld(auswahl, { winkel: (((gewaehlt.winkel ?? 0) + 15) % 360) || undefined })}>
                        +15°
                      </button>
                    </div>
                  </>
                )}
                {gewaehlt.typ === "rechteck" && !gewaehlt.loch && (
                  <OptZahlfeld
                    label="Keil: Höhenzuwachs nach hinten (mm, negativ = fällt)"
                    wert={gewaehlt.keil_mm}
                    testid="form-keil"
                    onChange={(v) => setzeFeld(auswahl, { keil_mm: v })}
                  />
                )}
                <div className="ausrichten" data-testid="ausrichten">
                  <span className="leise">Ausrichten am Außenmaß der übrigen Formen</span>
                  <div className="knopfzeile">
                    {(
                      [
                        ["mitte-x", "Mitte ↔"],
                        ["mitte-y", "Mitte ↕"],
                        ["links", "Links"],
                        ["rechts", "Rechts"],
                        ["unten", "Unten"],
                        ["oben", "Oben"],
                      ] as Array<[AusrichtModus, string]>
                    ).map(([modus, titel]) => (
                      <button
                        key={modus}
                        type="button"
                        data-testid={`ausrichten-${modus}`}
                        disabled={!bezugsrahmen(teil.formen, auswahl)}
                        onClick={() => formen(teil.formen.map((f, i) => (i === auswahl ? ausrichten(f, modus, bezugsrahmen(teil.formen, auswahl)) : f)))}
                      >
                        {titel}
                      </button>
                    ))}
                  </div>
                </div>
                <MusterPanel
                  key={`${teil.id}-${auswahl}`}
                  form={gewaehlt}
                  rahmen={bezugsrahmen(teil.formen, auswahl)}
                  teilHoehe={teil.hoehe_mm}
                  anzahlFormen={teil.formen.length}
                  meldung={musterMeldung}
                  onMeldung={setMusterMeldung}
                  onAdd={(neu) => {
                    formen([...teil.formen, ...neu]);
                    setAuswahl(teil.formen.length + neu.length - 1);
                  }}
                  onErsetzen={(neu) => formen(teil.formen.map((f, i) => (i === auswahl ? neu : f)))}
                />
                <label>
                  {gewaehlt.loch ? "Lochrand" : "Oberrand dieser Form"}
                  <select
                    data-testid="form-kante-art"
                    value={gewaehlt.kante_art ?? "keine"}
                    onChange={(e) => setzeFeld(auswahl, { kante_art: e.target.value, kante_mm: e.target.value === "keine" ? undefined : gewaehlt.kante_mm ?? 1 })}
                  >
                    <option value="keine">scharfkantig</option>
                    <option value="fase">Fase</option>
                    <option value="rund">Rundung</option>
                  </select>
                </label>
                {gewaehlt.kante_art && gewaehlt.kante_art !== "keine" && (
                  <OptZahlfeld label="Größe der Kante (mm)" wert={gewaehlt.kante_mm} testid="form-kante-mm" onChange={(v) => setzeFeld(auswahl, { kante_mm: v })} />
                )}
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
  if (f.typ === "rechteck") {
    return (
      <rect
        x={f.x}
        y={f.y}
        width={f.b}
        height={f.t}
        rx={f.radius || 0}
        ry={f.radius || 0}
        transform={f.winkel ? `rotate(${f.winkel} ${f.x + f.b / 2} ${f.y + f.t / 2})` : undefined}
      />
    );
  }
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
    const m = svg?.getScreenCTM?.();
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
      style={{ touchAction: "none", width: "100%", background: "#fff", border: "1px solid #d5d9de", borderRadius: 12 }}
      onPointerMove={(e) => {
        if (!zug) return;
        const [px, py] = punkt(e);
        onMove(Math.max(0, Math.round(px - zug.dx)), Math.max(0, Math.round(py - zug.dy)));
      }}
      onPointerUp={() => setZug(null)}
    >
      <rect x={0} y={0} width={plan.breite} height={plan.tiefe} fill="#fff" stroke="#0F1F3A" strokeWidth={1.2} />
      {plan.platten.map((p, i) => (
        <rect key={i} x={p.links_mm} y={p.vorne_mm} width={p.breite_mm} height={p.tiefe_mm} fill="none" stroke="#00AE42" strokeWidth={0.8} />
      ))}
      {plan.boxen.map((b) => (
        <rect key={b.id} x={b.links_mm} y={b.vorne_mm} width={b.breite_mm} height={b.tiefe_mm} fill="#D9F5E5" fillOpacity={0.85} stroke="#0F1F3A" strokeWidth={0.5} />
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
              fill={istAktiv ? "#00AE42" : "#E4E7EB"}
              stroke="#0F1F3A"
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
            <text x={r.x + 2} y={r.y + 8} fontSize={7} fill="#0F1F3A" pointerEvents="none">{t.id}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** Hell bis dunkel je nach Oberkante der Form: höhere Formen erscheinen dunkler. */
function hoehenFarbe(anteil: number): string {
  const von = [232, 248, 238];
  const bis = [0, 140, 53];
  const mix = von.map((v, i) => Math.round(v + (bis[i] - v) * anteil));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

function OptZahlfeld({ label, wert, onChange, testid }: { label: string; wert: number | undefined; onChange: (v: number | undefined) => void; testid?: string }) {
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

function MusterPanel({
  form,
  rahmen,
  teilHoehe,
  anzahlFormen,
  meldung,
  onMeldung,
  onAdd,
  onErsetzen,
}: {
  form: FormTyp;
  rahmen: [number, number, number, number] | null;
  teilHoehe: number;
  anzahlFormen: number;
  meldung: string;
  onMeldung: (text: string) => void;
  onAdd: (neu: FormTyp[]) => void;
  onErsetzen: (neu: FormTyp) => void;
}) {
  const vorschlag = abstandsvorschlag(form);
  const mitteStart = rahmen ? ([(rahmen[0] + rahmen[2]) / 2, (rahmen[1] + rahmen[3]) / 2] as [number, number]) : formMitte(form);
  // Eingaben bleiben als Text stehen und werden erst beim Erzeugen ausgewertet.
  const [spalten, setSpalten] = useState("3");
  const [zeilen, setZeilen] = useState("1");
  const [abstandX, setAbstandX] = useState(String(vorschlag.x));
  const [abstandY, setAbstandY] = useState(String(vorschlag.y));
  const [anzahl, setAnzahl] = useState("6");
  const [winkel, setWinkel] = useState("360");
  const [mitteX, setMitteX] = useState(String(mitteStart[0]));
  const [mitteY, setMitteY] = useState(String(mitteStart[1]));
  const [ersetzen, setErsetzen] = useState(false);
  const setMeldung = onMeldung;

  function hinzufuegen(neu: FormTyp[], text: string) {
    if (neu.length === 0) {
      setMeldung("Es entstehen keine neuen Formen.");
      return;
    }
    if (anzahlFormen + neu.length > MAX_FORMEN) {
      setMeldung(`Zu viele Formen: höchstens ${MAX_FORMEN} je Teil.`);
      return;
    }
    onAdd(neu);
    setMeldung(`${neu.length} ${neu.length === 1 ? "Form" : "Formen"} ${text}.`);
  }

  const zahl = (wert: string, standard: number) => {
    const n = Number(wert.trim().replace(",", "."));
    return wert.trim() !== "" && Number.isFinite(n) ? n : standard;
  };
  const ganz = (wert: string, standard: number, min: number, max: number) => Math.max(min, Math.min(max, Math.round(zahl(wert, standard))));

  return (
    <details className="muster" data-testid="muster">
      <summary>Muster, Kopie und Spiegeln</summary>
      <div className="knopfzeile">
        <button type="button" data-testid="form-kopieren" onClick={() => hinzufuegen([kopieren(form, 5, 5)], "kopiert, um 5 / 5 mm versetzt")}>
          Form kopieren
        </button>
      </div>

      <h3>Reihe oder Gitter</h3>
      <div className="formular">
        <label>
          Spalten
          <input data-testid="muster-spalten" inputMode="numeric" value={spalten} onChange={(e) => setSpalten(e.target.value)} />
        </label>
        <label>
          Zeilen
          <input data-testid="muster-zeilen" inputMode="numeric" value={zeilen} onChange={(e) => setZeilen(e.target.value)} />
        </label>
        <label>
          Abstand X (mm, von Mitte zu Mitte)
          <input data-testid="muster-abstand-x" inputMode="decimal" value={abstandX} onChange={(e) => setAbstandX(e.target.value)} />
        </label>
        <label>
          Abstand Y (mm)
          <input data-testid="muster-abstand-y" inputMode="decimal" value={abstandY} onChange={(e) => setAbstandY(e.target.value)} />
        </label>
      </div>
      <button type="button" data-testid="muster-gitter" onClick={() => hinzufuegen(
            gitter(form, ganz(spalten, 3, 1, 50), ganz(zeilen, 1, 1, 50), zahl(abstandX, vorschlag.x), zahl(abstandY, vorschlag.y)),
            "als Gitter erzeugt",
          )}>
        Gitter erzeugen
      </button>

      <h3>Kreismuster</h3>
      {laesstSichDrehen(form) ? (
        <>
          <div className="formular">
            <label>
              Anzahl (mit Original)
              <input data-testid="kreis-anzahl" inputMode="numeric" value={anzahl} onChange={(e) => setAnzahl(e.target.value)} />
            </label>
            <label>
              Gesamtwinkel (360 = Vollkreis)
              <input data-testid="kreis-winkel" inputMode="decimal" value={winkel} onChange={(e) => setWinkel(e.target.value)} />
            </label>
            <label>
              Mitte x (mm)
              <input data-testid="kreis-mitte-x" inputMode="decimal" value={mitteX} onChange={(e) => setMitteX(e.target.value)} />
            </label>
            <label>
              Mitte y (mm)
              <input data-testid="kreis-mitte-y" inputMode="decimal" value={mitteY} onChange={(e) => setMitteY(e.target.value)} />
            </label>
          </div>
          <button type="button" data-testid="muster-kreis" onClick={() => hinzufuegen(
                kreismuster(form, [zahl(mitteX, mitteStart[0]), zahl(mitteY, mitteStart[1])], ganz(anzahl, 6, 2, 100), zahl(winkel, 360)),
                "im Kreis angeordnet",
              )}>
            Kreismuster erzeugen
          </button>
        </>
      ) : (
        <p className="leise">Ein Rechteck mit Keil lässt sich nicht drehen, daher gibt es dafür kein Kreismuster.</p>
      )}

      <h3>Spiegeln</h3>
      <label className="check">
        <input type="checkbox" data-testid="spiegeln-ersetzen" checked={ersetzen} onChange={(e) => setErsetzen(e.target.checked)} />
        Original ersetzen (statt Spiegelkopie)
      </label>
      <p className="leise">{rahmen ? "Achse: Mitte der übrigen Formen." : "Achse: Mitte dieser Form."}</p>
      <div className="knopfzeile">
        {(["x", "y"] as const).map((achse) => {
          const pos = achse === "x" ? (rahmen ? (rahmen[0] + rahmen[2]) / 2 : formMitte(form)[0]) : rahmen ? (rahmen[1] + rahmen[3]) / 2 : formMitte(form)[1];
          return (
            <button
              key={achse}
              type="button"
              data-testid={`spiegeln-${achse}`}
              onClick={() => {
                const neu = spiegeln(form, achse, pos, teilHoehe);
                if (ersetzen) {
                  onErsetzen(neu);
                  setMeldung("Form gespiegelt.");
                } else {
                  hinzufuegen([neu], "gespiegelt kopiert");
                }
              }}
            >
              {achse === "x" ? "Links ↔ rechts spiegeln" : "Vorn ↔ hinten spiegeln"}
            </button>
          );
        })}
      </div>
      {meldung && <p className="leise" data-testid="muster-meldung">{meldung}</p>}
    </details>
  );
}

/** Position des Eingabefelds über dem Maß: Weltpunkt (x, y nach unten) in Pixel relativ zum Blatt. */
function masseEingabePosition(svg: SVGSVGElement | null, x: number, ySvg: number): React.CSSProperties {
  const basis: React.CSSProperties = { position: "absolute", width: 76, transform: "translate(-50%, -50%)", zIndex: 2, textAlign: "center" };
  const m = svg?.getScreenCTM?.();
  if (!svg || !m || !svg.parentElement) return { ...basis, left: "50%", top: 8 };
  const pt = svg.createSVGPoint();
  pt.x = x;
  pt.y = ySvg;
  const p = pt.matrixTransform(m);
  const rahmen = svg.parentElement.getBoundingClientRect();
  return { ...basis, left: p.x - rahmen.left, top: p.y - rahmen.top };
}

const MAX_IMPORT_BYTES = 5 * 1024 * 1024;

function ImportPanel({ onEinfuegen }: { onEinfuegen: (neu: Partial<Eigenteil>) => void }) {
  const [datei, setDatei] = useState<{ name: string; ergebnis: ImportErgebnis } | null>(null);
  const [massstab, setMassstab] = useState("1");
  const [hoehe, setHoehe] = useState("10");
  const [fehler, setFehler] = useState("");

  async function einlesen(file: File | undefined) {
    setFehler("");
    setDatei(null);
    if (!file) return;
    if (file.size > MAX_IMPORT_BYTES) {
      setFehler("Die Datei ist größer als 5 MB.");
      return;
    }
    try {
      const text = await dateiText(file);
      const dxf = /\.dxf$/i.test(file.name) || (!/\.svg$/i.test(file.name) && /^\s*0\s*\r?\n\s*SECTION/.test(text));
      const ergebnis = dxf ? leseDxf(text) : leseSvg(text);
      setDatei({ name: file.name, ergebnis });
      setMassstab(String(Math.round(ergebnis.einheitMm * 1e6) / 1e6).replace(".", ","));
    } catch {
      setFehler("Die Datei ließ sich nicht lesen.");
    }
  }

  const faktor = Number(massstab.trim().replace(",", "."));
  const hoeheMm = Number(hoehe.trim().replace(",", "."));
  const vorschau = datei ? zuFormen(datei.ergebnis, faktor) : null;
  const gueltig = Boolean(vorschau && vorschau.formen.some((f) => !f.loch) && Number.isFinite(hoeheMm) && hoeheMm >= 0.4 && hoeheMm <= 256);

  return (
    <div className="import-panel" data-testid="import-panel">
      <label>
        Umriss importieren (SVG oder DXF)
        <input type="file" data-testid="import-datei" accept=".svg,.dxf,image/svg+xml" onChange={(e) => einlesen(e.target.files?.[0])} />
      </label>
      {fehler && <p className="alarm" role="alert">{fehler}</p>}
      {datei && vorschau && (
        <div data-testid="import-vorschau">
          <p>
            <strong>{datei.name}</strong>
            <br />
            {vorschau.formen.length === 0
              ? "Keine Formen."
              : `${vorschau.formen.length} Formen, davon ${vorschau.anzahlLoecher} Löcher, ${vorschau.breite} × ${vorschau.tiefe} mm.`}
          </p>
          <label>
            Maßstab (mm je Einheit der Datei)
            <input data-testid="import-massstab" inputMode="decimal" value={massstab} onChange={(e) => setMassstab(e.target.value)} />
          </label>
          <label>
            Höhe des Teils (mm)
            <input data-testid="import-hoehe" inputMode="decimal" value={hoehe} onChange={(e) => setHoehe(e.target.value)} />
          </label>
          {vorschau.hinweise.length > 0 && (
            <ul className="leise" data-testid="import-hinweise">
              {vorschau.hinweise.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          )}
          <div className="knopfzeile">
            <button
              type="button"
              className="primaer"
              data-testid="import-einfuegen"
              disabled={!gueltig}
              onClick={() => {
                onEinfuegen({ name: datei.name.replace(/\.[^.]+$/, "") || "Import", hoehe_mm: hoeheMm, formen: vorschau.formen });
                setDatei(null);
              }}
            >
              Als neues Teil einfügen
            </button>
            <button type="button" onClick={() => setDatei(null)}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
