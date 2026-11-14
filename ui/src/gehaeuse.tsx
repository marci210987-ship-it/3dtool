import { useEffect, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { dateiUrl } from "./api";

export interface Oeffnung {
  seite: string;
  form: string;
  pos_mm: string | number;
  unten_mm: string | number;
  breite_mm?: string | number;
  hoehe_mm?: string | number;
  durchmesser_mm?: string | number;
}

export interface GehaeuseDaten {
  oeffnungen: Oeffnung[];
  [key: string]: string | number | Oeffnung[] | undefined;
}

export interface Vorlage {
  name: string;
  quelle: string;
}

const ZAHL = [
  ["innen_b_mm", "Innenbreite"],
  ["innen_t_mm", "Innentiefe"],
  ["innen_h_mm", "Innenhöhe"],
  ["wand_mm", "Wandstärke"],
  ["boden_mm", "Bodenstärke"],
  ["deckel_mm", "Deckelstärke"],
  ["radius_mm", "Eckenradius"],
  ["spiel_mm", "Spiel zum Deckel"],
  ["standoff_h_mm", "Höhe der Platinenstützen"],
  ["standoff_d_mm", "Durchmesser der Stützen"],
] as const;

export function GehaeuseAnsicht({
  daten,
  vorlagen,
  fehler,
  soll,
  onAendern,
  onOeffnung,
  onOeffnungNeu,
  onOeffnungWeg,
  onErzeugen,
  ergebnis,
  rechnet,
  jobText,
  speicherpfad,
  onSpeicherpfad,
  onSpeichern,
}: {
  daten: GehaeuseDaten;
  vorlagen: Record<string, Vorlage>;
  fehler: string[];
  soll: { korpus: number[]; deckel: number[] } | null;
  onAendern: (key: string, wert: string) => void;
  onOeffnung: (index: number, key: string, wert: string) => void;
  onOeffnungNeu: () => void;
  onOeffnungWeg: (index: number) => void;
  onErzeugen: () => void;
  ergebnis: { ok: boolean; fehler?: string[]; teile?: Array<{ dateien?: Array<{ id: string; stl?: string; fcstd?: string; ok?: boolean }> }> } | null;
  rechnet: boolean;
  jobText: string;
  speicherpfad: string;
  onSpeicherpfad: (wert: string) => void;
  onSpeichern: () => void;
}) {
  const vorlage = vorlagen[String(daten.platine || "")] || null;
  const stl = ergebnis?.ok ? ergebnis.teile?.flatMap((t) => t.dateien || []).find((d) => d.ok && d.stl)?.stl : undefined;
  return (
    <main>
      <h1>Elektronikgehäuse</h1>
      <p className="leise">
        Die Maße sind der Innenraum in Millimeter. Deckel und Gehäuse werden getrennt erzeugt. Das Spiel ist die Lücke im Modell.
      </p>
      <div className="formular" data-testid="gehaeuse-form">
        <h2>Innenraum</h2>
        {ZAHL.slice(0, 3).map(([key, label]) => (
          <Zahl key={key} name={key} label={label} wert={daten[key]} onAendern={onAendern} />
        ))}
        <h2>Wand und Deckel</h2>
        {ZAHL.slice(3, 8).map(([key, label]) => (
          <Zahl key={key} name={key} label={label} wert={daten[key]} onAendern={onAendern} />
        ))}
        <label>
          Deckel
          <select data-testid="feld-deckel" value={String(daten.deckel || "schraube")} onChange={(e) => onAendern("deckel", e.target.value)}>
            <option value="schraube">Schraubdeckel</option>
            <option value="schiebe">Schiebedeckel</option>
          </select>
        </label>
        {daten.deckel !== "schiebe" && (
          <>
            <label>
              Schraube
              <select data-testid="feld-schraube" value={String(daten.schraube || "m3")} onChange={(e) => onAendern("schraube", e.target.value)}>
                <option value="m3">M3, Kernloch 2,5 mm</option>
                <option value="m2_5">M2,5, Kernloch 2,0 mm</option>
              </select>
            </label>
            <label>
              Senkung im Deckel
              <select data-testid="feld-senkung" value={String(daten.senkung || "nein")} onChange={(e) => onAendern("senkung", e.target.value)}>
                <option value="nein">Ohne Senkung</option>
                <option value="ja">Mit Senkung</option>
              </select>
            </label>
          </>
        )}
        <h2>Platine</h2>
        <label>
          Vorlage
          <select data-testid="feld-platine" value={String(daten.platine || "keine")} onChange={(e) => onAendern("platine", e.target.value)}>
            {Object.entries(vorlagen).map(([id, eintrag]) => (
              <option key={id} value={id}>
                {eintrag.name}
              </option>
            ))}
          </select>
        </label>
        {daten.platine === "eigene" && (
          <>
            <Zahl name="platine_b_mm" label="Platinenbreite" wert={daten.platine_b_mm} onAendern={onAendern} />
            <Zahl name="platine_t_mm" label="Platinentiefe" wert={daten.platine_t_mm} onAendern={onAendern} />
            <Zahl name="loch_x_mm" label="Lochabstand in der Breite" wert={daten.loch_x_mm} onAendern={onAendern} />
            <Zahl name="loch_y_mm" label="Lochabstand in der Tiefe" wert={daten.loch_y_mm} onAendern={onAendern} />
          </>
        )}
        {daten.platine !== "keine" &&
          ZAHL.slice(8).map(([key, label]) => <Zahl key={key} name={key} label={label} wert={daten[key]} onAendern={onAendern} />)}
        {vorlage?.quelle && <p className="hinweis">{vorlage.quelle}</p>}
        <h2>Öffnungen</h2>
        {daten.oeffnungen.map((oeffnung, index) => (
          <div key={index} className="knopfzeile" data-testid={`oeffnung-${index}`}>
            <select value={oeffnung.seite} onChange={(e) => onOeffnung(index, "seite", e.target.value)} aria-label="Seite">
              <option value="vorne">Vorne</option>
              <option value="hinten">Hinten</option>
              <option value="links">Links</option>
              <option value="rechts">Rechts</option>
              <option value="boden">Boden</option>
            </select>
            <select value={oeffnung.form} onChange={(e) => onOeffnung(index, "form", e.target.value)} aria-label="Form">
              <option value="rechteck">Rechteck</option>
              <option value="rund">Rund</option>
            </select>
            <input aria-label="Position" inputMode="decimal" value={String(oeffnung.pos_mm)} onChange={(e) => onOeffnung(index, "pos_mm", e.target.value.replace(",", "."))} />
            <input aria-label="Höhe von unten" inputMode="decimal" value={String(oeffnung.unten_mm)} onChange={(e) => onOeffnung(index, "unten_mm", e.target.value.replace(",", "."))} />
            {oeffnung.form === "rund" ? (
              <input aria-label="Durchmesser" inputMode="decimal" value={String(oeffnung.durchmesser_mm ?? "")} onChange={(e) => onOeffnung(index, "durchmesser_mm", e.target.value.replace(",", "."))} />
            ) : (
              <>
                <input aria-label="Breite" inputMode="decimal" value={String(oeffnung.breite_mm ?? "")} onChange={(e) => onOeffnung(index, "breite_mm", e.target.value.replace(",", "."))} />
                <input aria-label="Höhe" inputMode="decimal" value={String(oeffnung.hoehe_mm ?? "")} onChange={(e) => onOeffnung(index, "hoehe_mm", e.target.value.replace(",", "."))} />
              </>
            )}
            <button type="button" onClick={() => onOeffnungWeg(index)}>
              Weg
            </button>
          </div>
        ))}
        <button type="button" data-testid="oeffnung-neu" onClick={onOeffnungNeu}>
          Öffnung hinzufügen
        </button>
        <label>
          Lüftungsschlitze links und rechts
          <select data-testid="feld-lueftung" value={String(daten.lueftung || "nein")} onChange={(e) => onAendern("lueftung", e.target.value)}>
            <option value="nein">Nein</option>
            <option value="ja">Ja</option>
          </select>
        </label>
        <label>
          Wandlaschen
          <select data-testid="feld-laschen" value={String(daten.laschen || "nein")} onChange={(e) => onAendern("laschen", e.target.value)}>
            <option value="nein">Nein</option>
            <option value="ja">Ja, zwei Laschen hinten</option>
          </select>
        </label>
      </div>
      <p className="hinweis">
        {daten.deckel === "schiebe"
          ? "Gehäuse mit der Öffnung nach oben drucken. Den Deckel flach legen und von vorn einschieben."
          : "Gehäuse mit der Öffnung nach oben drucken. Den Deckel flach, die Senkung nach oben."}
      </p>
      {soll && !fehler.length && (
        <p data-testid="gehaeuse-mass">
          Gehäuse {soll.korpus.map((v) => v.toLocaleString("de-DE", { maximumFractionDigits: 1 })).join(" × ")} mm, Deckel{" "}
          {soll.deckel.map((v) => v.toLocaleString("de-DE", { maximumFractionDigits: 1 })).join(" × ")} mm
        </p>
      )}
      {fehler.length > 0 && (
        <div className="alarm" role="alert" data-testid="gehaeuse-fehler">
          {fehler.map((f) => (
            <p key={f}>{f}</p>
          ))}
        </div>
      )}
      <Vorschau soll={soll?.korpus || null} stl={stl || null} />
      <button type="button" className="primaer" data-testid="gehaeuse-erzeugen" disabled={rechnet || fehler.length > 0} onClick={onErzeugen}>
        {rechnet ? "Berechnet …" : "Gehäuse berechnen"}
      </button>
      {jobText && rechnet && <p>{jobText}</p>}
      {ergebnis?.ok && (
        <>
          <p className="erfolg" data-testid="export-erfolg">Gehäuse und Deckel sind erzeugt. Datei, Netz und Körper sind geprüft.</p>
          <ul className="dateien" data-testid="gehaeuse-dateien">
            {(ergebnis.teile || []).flatMap((teil) => teil.dateien || []).map((datei) => (
              <li key={datei.id}>
                {datei.id}
                {datei.stl && (
                  <>
                    {" "}
                    <a href={dateiUrl(datei.stl)}>STL</a>
                  </>
                )}
                {datei.fcstd && (
                  <>
                    {" "}
                    <a href={dateiUrl(datei.fcstd)}>FCStd</a>
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {ergebnis && !ergebnis.ok && (
        <div className="alarm" role="alert">
          {(ergebnis.fehler || ["Nicht exportiert."]).map((f) => (
            <p key={f}>{f}</p>
          ))}
        </div>
      )}
      <div className="speichern">
        <label>
          Projektdatei
          <input data-testid="speicherpfad" value={speicherpfad} onChange={(e) => onSpeicherpfad(e.target.value)} placeholder="gehaeuse.cadstudio.json" />
        </label>
        <button type="button" onClick={onSpeichern}>
          Speichern
        </button>
      </div>
    </main>
  );
}

export function gehaeuseZahlen(daten: GehaeuseDaten) {
  const aus: Record<string, unknown> = {};
  for (const [key, wert] of Object.entries(daten)) {
    if (key === "oeffnungen" && Array.isArray(wert)) {
      aus[key] = wert.map((oeffnung) => {
        const zeile: Record<string, string | number> = {};
        for (const [feld, inhalt] of Object.entries(oeffnung)) {
          zeile[feld] = typeof inhalt === "string" && /^-?\d+(\.\d+)?$/.test(inhalt) ? Number(inhalt) : (inhalt as string | number);
        }
        return zeile;
      });
    } else if (typeof wert === "string" && /^-?\d+(\.\d+)?$/.test(wert)) aus[key] = Number(wert);
    else aus[key] = wert;
  }
  return aus;
}

function Zahl({ name, label, wert, onAendern }: { name: string; label: string; wert: string | number | Oeffnung[] | undefined; onAendern: (key: string, wert: string) => void }) {
  return (
    <label>
      {label}
      <input data-testid={`feld-${name}`} inputMode="decimal" value={String(wert ?? "")} onChange={(e) => onAendern(name, e.target.value.replace(",", "."))} />
      <span>mm</span>
    </label>
  );
}

function webglVorhanden(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl"));
  } catch {
    return false;
  }
}

function Vorschau({ soll, stl }: { soll: number[] | null; stl: string | null }) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = host.current;
    if (!el || !webglVorhanden()) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      return;
    }
    renderer.setSize(el.clientWidth || 640, 280);
    el.innerHTML = "";
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#f4f1ea");
    const camera = new THREE.PerspectiveCamera(35, (el.clientWidth || 640) / 280, 0.1, 4000);
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const licht = new THREE.DirectionalLight(0xffffff, 0.8);
    licht.position.set(40, 80, 60);
    scene.add(licht);
    let weg = false;
    const rahmen = () => {
      if (!weg) renderer.render(scene, camera);
    };
    if (stl) {
      const loader = new STLLoader();
      loader.load(dateiUrl(stl), (geo) => {
        if (weg) return;
        geo.computeVertexNormals();
        geo.computeBoundingBox();
        const bb = geo.boundingBox!;
        const mitte = new THREE.Vector3();
        bb.getCenter(mitte);
        const groesse = new THREE.Vector3();
        bb.getSize(groesse);
        scene.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: "#0f6e6e", roughness: 0.6 })).translateX(-mitte.x).translateY(-mitte.y).translateZ(-mitte.z));
        const weit = Math.max(groesse.x, groesse.y, groesse.z) * 2.2;
        camera.position.set(weit, weit * 0.7, weit);
        camera.lookAt(0, 0, 0);
        rahmen();
      });
    } else if (soll) {
      const [x, y, z] = soll;
      scene.add(new THREE.Mesh(new THREE.BoxGeometry(x, z, y), new THREE.MeshStandardMaterial({ color: "#c9844a", roughness: 0.7 })));
      const weit = Math.max(x, y, z) * 2.4;
      camera.position.set(weit, weit * 0.8, weit);
      camera.lookAt(0, 0, 0);
      rahmen();
    }
    return () => {
      weg = true;
      renderer.dispose();
    };
  }, [soll, stl]);
  return (
    <div className="vorschau">
      <div ref={host} className="buehne" data-testid="gehaeuse-vorschau" />
      <p className="kennzeichnung" data-testid="vorschau-art">
        {stl ? "3D-Ansicht aus der erzeugten STL-Datei." : "Vereinfachte Vorschau. Das ist noch nicht die echte Druckgeometrie."}
      </p>
    </div>
  );
}
