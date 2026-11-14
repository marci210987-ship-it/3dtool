import { useEffect, useRef, useState } from "react";
import { KATALOG, KatalogEintrag, Box, footprint, freieZellen, kollisionen, ausserhalb, neueBox, dupliziere, lageplanSchriftPx, lageplanZeilen } from "./layout";

interface Plan {
  einheiten_x: number;
  einheiten_y: number;
  ursprung_x_mm: number;
  ursprung_y_mm: number;
  raster_mm: number;
  platten: Array<{
    id: string;
    einheiten_x: number;
    einheiten_y: number;
    lage: { links_mm: number; vorne_mm: number; breite_mm: number; tiefe_mm: number };
  }>;
  verbinder_anzahl: number;
  fehler: string[];
  hinweise: string[];
}

interface Props {
  breite: number;
  tiefe: number;
  plan: Plan;
  boxen: Box[];
  onChange: (boxen: Box[]) => void;
}

export function Editor({ breite, tiefe, plan, boxen, onChange }: Props) {
  const [aktiv, setAktiv] = useState<string | null>(boxen[0]?.id ?? null);
  const aktuell = useRef(boxen);
  aktuell.current = boxen;
  const gewaehlt = boxen.find((b) => b.id === aktiv) ?? null;
  const konflikte = kollisionen(boxen);
  const frei = freieZellen(boxen, plan.einheiten_x, plan.einheiten_y);
  const raster = plan.raster_mm || 42;

  function hinzufuegen(vorlage: KatalogEintrag) {
    const neu = neueBox(vorlage, aktuell.current, plan.einheiten_x, plan.einheiten_y);
    if (!neu) return;
    const neuListe = [...aktuell.current, neu];
    aktuell.current = neuListe;
    onChange(neuListe);
    setAktiv(neu.id);
  }

  function aendere(id: string, patch: Partial<Box>) {
    const neu = aktuell.current.map((b) => (b.id === id ? { ...b, ...patch } : b));
    aktuell.current = neu;
    onChange(neu);
  }

  function ziehe(id: string, x: number, y: number) {
    const box = aktuell.current.find((b) => b.id === id);
    if (!box) return;
    const [, , w, h] = footprint({ ...box, x, y });
    const nx = Math.max(0, Math.min(plan.einheiten_x - w, x));
    const ny = Math.max(0, Math.min(plan.einheiten_y - h, y));
    aendere(id, { x: nx, y: ny });
  }

  return (
    <div className="editor">
      <aside className="katalog">
        <h2>Boxen</h2>
        <p className="leise">Antippen, um sie auf das nächste freie Feld zu setzen. Danach ziehen, drehen oder teilen.</p>
        <ul>
          {KATALOG.map((eintrag) => (
            <li key={eintrag.id}>
              <button type="button" data-testid={`katalog-${eintrag.id}`} onClick={() => hinzufuegen(eintrag)}>
                <strong>{eintrag.name}</strong>
                <span>{eintrag.text}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
      <div className="flaeche">
        <Schubladenbild
          breite={breite}
          tiefe={tiefe}
          plan={plan}
          boxen={boxen}
          aktiv={aktiv}
          frei={frei}
          raster={raster}
          onWaehlen={setAktiv}
          onZiehen={ziehe}
        />
        <p className="leise">
          {frei.length} von {plan.einheiten_x * plan.einheiten_y} Feldern frei.
          {plan.verbinder_anzahl ? ` ${plan.verbinder_anzahl} Plattenverbinder an den Stößen.` : ""}
        </p>
        {konflikte.length > 0 && (
          <div className="alarm" role="alert" data-testid="ueberlappung">
            {konflikte.map((k) => (
              <p key={k.boxen.join()}>{k.text} So kann nicht exportiert werden.</p>
            ))}
          </div>
        )}
        {boxen.some((b) => ausserhalb(b, plan.einheiten_x, plan.einheiten_y)) && (
          <div className="alarm" role="alert">
            Eine Box ragt aus dem Raster.
          </div>
        )}
      </div>
      <aside className="eigenschaften">
        <h2>Ausgewählt</h2>
        {!gewaehlt && <p>Noch keine Box ausgewählt.</p>}
        {gewaehlt && (
          <BoxForm
            box={gewaehlt}
            onChange={(patch) => aendere(gewaehlt.id, patch)}
            onDrehen={() => aendere(gewaehlt.id, { rotation: (gewaehlt.rotation + 90) % 360 })}
            onDuplizieren={() => {
              const kopie = dupliziere(gewaehlt, aktuell.current, plan.einheiten_x, plan.einheiten_y);
              const neuListe = [...aktuell.current, kopie];
              aktuell.current = neuListe;
              onChange(neuListe);
              setAktiv(kopie.id);
            }}
            onLoeschen={() => {
              const neuListe = aktuell.current.filter((b) => b.id !== gewaehlt.id);
              aktuell.current = neuListe;
              onChange(neuListe);
              setAktiv(null);
            }}
          />
        )}
      </aside>
    </div>
  );
}

function BoxForm({
  box,
  onChange,
  onDrehen,
  onDuplizieren,
  onLoeschen,
}: {
  box: Box;
  onChange: (patch: Partial<Box>) => void;
  onDrehen: () => void;
  onDuplizieren: () => void;
  onLoeschen: () => void;
}) {
  const [, , w, h] = footprint(box);
  return (
    <div>
      <p className="name">{box.name}</p>
      <p className="leise">
        {w} × {h} Felder, gedreht um {box.rotation}°.
      </p>
      <label>
        Höhe in Stufen (je 7 mm)
        <input
          data-testid="hoehe"
          type="number"
          min={1}
          max={12}
          value={box.ez}
          onChange={(e) => onChange({ ez: Number(e.target.value) })}
        />
      </label>
      {box.art === "raster" && (
        <>
          <label>
            Fächer in der Breite
            <input type="number" min={1} max={8} value={box.fachX} onChange={(e) => onChange({ fachX: Number(e.target.value) })} />
          </label>
          <label>
            Fächer in der Tiefe
            <input type="number" min={1} max={8} value={box.fachY} onChange={(e) => onChange({ fachY: Number(e.target.value) })} />
          </label>
          <label className="check">
            <input type="checkbox" checked={box.stapellippe || box.deckel} disabled={box.deckel} onChange={(e) => onChange({ stapellippe: e.target.checked })} />
            Rand zum Stapeln
          </label>
          <label className="check">
            <input type="checkbox" checked={box.deckel} onChange={(e) => onChange({ deckel: e.target.checked, stapellippe: e.target.checked || box.stapellippe })} />
            Loser Deckel
          </label>
          <label className="check">
            <input type="checkbox" checked={box.herausnehmbar} onChange={(e) => onChange({ herausnehmbar: e.target.checked })} />
            Trennwände herausnehmbar
          </label>
        </>
      )}
      {box.art === "besteck" && <p className="leise">Dieser Einsatz folgt dem Besteck-Generator und wird in druckbare Segmente geteilt.</p>}
      <div className="knopfzeile">
        <button type="button" data-testid="links" onClick={() => onChange({ x: box.x - 1 })}>
          Links
        </button>
        <button type="button" data-testid="rechts" onClick={() => onChange({ x: box.x + 1 })}>
          Rechts
        </button>
        <button type="button" data-testid="vorn" onClick={() => onChange({ y: box.y - 1 })}>
          Nach vorn
        </button>
        <button type="button" data-testid="hinten" onClick={() => onChange({ y: box.y + 1 })}>
          Nach hinten
        </button>
      </div>
      <div className="knopfzeile">
        <button type="button" data-testid="drehen" onClick={onDrehen}>
          Drehen
        </button>
        <button type="button" data-testid="duplizieren" onClick={onDuplizieren}>
          Duplizieren
        </button>
        <button type="button" data-testid="loeschen" className="still" onClick={onLoeschen}>
          Entfernen
        </button>
      </div>
    </div>
  );
}

function Schubladenbild({
  breite,
  tiefe,
  plan,
  boxen,
  aktiv,
  frei,
  raster,
  onWaehlen,
  onZiehen,
}: {
  breite: number;
  tiefe: number;
  plan: Plan;
  boxen: Box[];
  aktiv: string | null;
  frei: { x: number; y: number }[];
  raster: number;
  onWaehlen: (id: string) => void;
  onZiehen: (id: string, x: number, y: number) => void;
}) {
  const freiSet = new Set(frei.map((z) => `${z.x},${z.y}`));
  const svgRef = useRef<SVGSVGElement>(null);
  const [pxJeMm, setPxJeMm] = useState(1.6);
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const messen = () => {
      const rect = el.getBoundingClientRect();
      const vb = el.viewBox?.baseVal?.width || breite;
      if (rect.width > 0 && vb > 0) setPxJeMm(rect.width / vb);
    };
    messen();
    if (typeof ResizeObserver === "undefined") return;
    const beobachter = new ResizeObserver(messen);
    beobachter.observe(el);
    return () => beobachter.disconnect();
  }, [breite]);
  return (
    <svg
      ref={svgRef}
      data-testid="schublade"
      viewBox={`0 0 ${breite} ${tiefe}`}
      role="img"
      aria-label="Schublade von oben"
      onPointerMove={(event) => {
        const id = (event.currentTarget.dataset.ziehen as string) || "";
        if (!id) return;
        const svg = event.currentTarget;
        const punkt = svgPunkt(svg, event.clientX, event.clientY);
        if (!punkt) return;
        const greifX = Number(svg.dataset.greifX || 0);
        const greifY = Number(svg.dataset.greifY || 0);
        const zelleX = Math.floor((punkt.x - plan.ursprung_x_mm) / raster) - greifX;
        const zelleY = Math.floor((punkt.y - plan.ursprung_y_mm) / raster) - greifY;
        onZiehen(id, zelleX, zelleY);
      }}
      onPointerUp={(event) => {
        delete event.currentTarget.dataset.ziehen;
      }}
      onPointerLeave={(event) => {
        delete event.currentTarget.dataset.ziehen;
      }}
    >
      <rect x={0} y={0} width={breite} height={tiefe} className="schublade-rand" />
      {Array.from({ length: plan.einheiten_x * plan.einheiten_y }, (_, n) => {
        const x = n % plan.einheiten_x;
        const y = Math.floor(n / plan.einheiten_x);
        const freiZelle = freiSet.has(`${x},${y}`);
        return (
          <rect
            key={`${x}-${y}`}
            x={plan.ursprung_x_mm + x * raster}
            y={plan.ursprung_y_mm + y * raster}
            width={raster}
            height={raster}
            className={freiZelle ? "feld frei" : "feld"}
          />
        );
      })}
      {plan.platten.map((platte) => (
        <g key={platte.id}>
          <rect
            x={platte.lage.links_mm}
            y={platte.lage.vorne_mm}
            width={platte.lage.breite_mm}
            height={platte.lage.tiefe_mm}
            className="platte"
          />
          <text x={platte.lage.links_mm + 3} y={platte.lage.vorne_mm + 8} className="plattenname">
            {platte.id}
          </text>
        </g>
      ))}
      {boxen.map((box) => {
        const [x, y, w, h] = footprint(box);
        const konflikt = kollisionen(boxen).some((k) => k.boxen.includes(box.id));
        const zeilen = lageplanZeilen(box);
        const boxBreitePx = Math.max(0, w * raster - 2) * pxJeMm;
        const boxHoehePx = Math.max(0, h * raster - 2) * pxJeMm;
        const schriftPx = lageplanSchriftPx(boxBreitePx, boxHoehePx, zeilen);
        const schrift = schriftPx / pxJeMm;
        const mitteX = plan.ursprung_x_mm + (x + w / 2) * raster;
        const mitteY = plan.ursprung_y_mm + (y + h / 2) * raster;
        return (
          <g
            key={box.id}
            data-testid={`box-${box.id}`}
            className={box.id === aktiv ? "box aktiv" : konflikt ? "box konflikt" : "box"}
            onPointerDown={(event) => {
              event.currentTarget.ownerSVGElement!.dataset.ziehen = box.id;
              const punkt = svgPunkt(event.currentTarget.ownerSVGElement!, event.clientX, event.clientY);
              const zelleX = punkt ? Math.floor((punkt.x - plan.ursprung_x_mm) / raster) : x;
              const zelleY = punkt ? Math.floor((punkt.y - plan.ursprung_y_mm) / raster) : y;
              event.currentTarget.ownerSVGElement!.dataset.greifX = String(zelleX - x);
              event.currentTarget.ownerSVGElement!.dataset.greifY = String(zelleY - y);
              onWaehlen(box.id);
            }}
          >
            <rect x={plan.ursprung_x_mm + x * raster + 0.6} y={plan.ursprung_y_mm + y * raster + 0.6} width={w * raster - 1.2} height={h * raster - 1.2} rx={1.5} />
            <clipPath id={`boxschrift-${box.id}`}>
              <rect x={plan.ursprung_x_mm + x * raster + 1.2} y={plan.ursprung_y_mm + y * raster + 1.2} width={w * raster - 2.4} height={h * raster - 2.4} />
            </clipPath>
            <text x={mitteX} y={mitteY} textAnchor="middle" fontSize={schrift} clipPath={`url(#boxschrift-${box.id})`}>
              {zeilen.length === 1 ? (
                <tspan x={mitteX} dy="0.35em">{zeilen[0]}</tspan>
              ) : (
                <>
                  <tspan x={mitteX} dy="-0.45em">{zeilen[0]}</tspan>
                  <tspan x={mitteX} dy="1.2em">{zeilen[1]}</tspan>
                </>
              )}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function svgPunkt(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number } | null {
  if (typeof svg.getScreenCTM !== "function") return null;
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const punkt = svg.createSVGPoint();
  punkt.x = clientX;
  punkt.y = clientY;
  const lokal = punkt.matrixTransform(ctm.inverse());
  return { x: lokal.x, y: lokal.y };
}
