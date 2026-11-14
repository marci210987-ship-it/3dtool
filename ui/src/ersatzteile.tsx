import { useEffect, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { dateiUrl } from "./api";

export interface ErsatzFeld {
  key: string;
  label: string;
  min?: number;
  max?: number;
  step?: number;
  einheit?: string;
  ganzzahl?: boolean;
  auswahl?: Array<{ wert: string; text: string }>;
}

export interface ErsatzArt {
  id: string;
  name: string;
  text: string;
  druck: string;
  standard: Record<string, string | number>;
  felder: ErsatzFeld[];
}

export interface Ersatzteil {
  id: string;
  art: string;
  name: string;
  parameter: Record<string, string | number>;
}

export function ErsatzteilAnsicht({
  katalog,
  teile,
  aktivId,
  fehler,
  soll,
  onWaehlen,
  onNeu,
  onParameter,
  onErzeugen,
  ergebnis,
  rechnet,
  jobText,
  speicherpfad,
  onSpeicherpfad,
  onSpeichern,
}: {
  katalog: ErsatzArt[];
  teile: Ersatzteil[];
  aktivId: string | null;
  fehler: string[];
  soll: number[] | null;
  onWaehlen: (id: string) => void;
  onNeu: (art: string) => void;
  onParameter: (id: string, key: string, wert: string | number) => void;
  onErzeugen: () => void;
  ergebnis: { ok: boolean; fehler?: string[]; teile?: Array<{ dateien?: Array<{ id: string; stl?: string; fcstd?: string; ok?: boolean }> }> } | null;
  rechnet: boolean;
  jobText: string;
  speicherpfad: string;
  onSpeicherpfad: (wert: string) => void;
  onSpeichern: () => void;
}) {
  const aktiv = teile.find((t) => t.id === aktivId) ?? teile[0] ?? null;
  const art = katalog.find((e) => e.id === aktiv?.art);
  const stl = ergebnis?.ok ? ergebnis.teile?.flatMap((t) => t.dateien || []).find((d) => d.ok && d.stl)?.stl : undefined;
  return (
    <main>
      <h1>Ersatzteil</h1>
      <p className="leise">Ein einfaches Teil mit wenigen Maßen. Die Vorgaben passen zu einer 0,4-mm-Düse und in den Bauraum von 256 mm.</p>
      <div className="editor">
        <aside className="katalog">
          <h2>Bibliothek</h2>
          <ul>
            {katalog.map((eintrag) => (
              <li key={eintrag.id}>
                <button type="button" data-testid={`ersatz-${eintrag.id}`} onClick={() => onNeu(eintrag.id)}>
                  <strong>{eintrag.name}</strong>
                  <span>{eintrag.text}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <div>
          {teile.length > 1 && (
            <div className="knopfzeile">
              {teile.map((teil) => (
                <button key={teil.id} type="button" className={teil.id === aktiv?.id ? "primaer" : ""} onClick={() => onWaehlen(teil.id)}>
                  {teil.name}
                </button>
              ))}
            </div>
          )}
          {art && aktiv && (
            <div className="formular" data-testid="ersatz-form">
              {art.felder.map((feld) =>
                feld.auswahl ? (
                  <label key={feld.key}>
                    {feld.label}
                    <select
                      data-testid={`feld-${feld.key}`}
                      value={String(aktiv.parameter[feld.key] ?? "")}
                      onChange={(e) => onParameter(aktiv.id, feld.key, e.target.value)}
                    >
                      {feld.auswahl.map((wahl) => (
                        <option key={wahl.wert} value={wahl.wert}>
                          {wahl.text}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label key={feld.key}>
                    {feld.label}
                    <input
                      data-testid={`feld-${feld.key}`}
                      inputMode="decimal"
                      value={String(aktiv.parameter[feld.key] ?? "")}
                      onChange={(e) => onParameter(aktiv.id, feld.key, e.target.value.replace(",", "."))}
                    />
                    {feld.einheit && <span>{feld.einheit}</span>}
                  </label>
                ),
              )}
            </div>
          )}
          {art && <p className="hinweis">{art.druck}</p>}
          {soll && !fehler.length && (
            <p data-testid="ersatz-mass">
              Außenmaß {soll.map((v) => v.toLocaleString("de-DE", { maximumFractionDigits: 1 })).join(" × ")} mm
            </p>
          )}
          {fehler.length > 0 && (
            <div className="alarm" role="alert" data-testid="ersatz-fehler">
              {fehler.map((f) => (
                <p key={f}>{f}</p>
              ))}
            </div>
          )}
          <TeilVorschau soll={soll} stl={stl || null} />
          <button type="button" className="primaer" data-testid="ersatz-erzeugen" disabled={rechnerGesperrt(fehler, rechnet, teile)} onClick={onErzeugen}>
            {rechnet ? "Berechnet …" : "Teil berechnen"}
          </button>
          {jobText && rechnet && <p>{jobText}</p>}
          {ergebnis && !ergebnis.ok && (
            <div className="alarm" role="alert" data-testid="export-fehler">
              <strong>Nicht exportiert.</strong>
              {(ergebnis.fehler || ["Die Prüfung ist fehlgeschlagen."]).map((f) => (
                <p key={f}>{f}</p>
              ))}
            </div>
          )}
          {ergebnis?.ok && (
            <>
              <p className="erfolg" data-testid="export-erfolg">Das Teil ist erzeugt. Datei, Netz und Körper sind geprüft.</p>
              <ul className="dateien" data-testid="ersatz-dateien">
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
          <div className="speichern">
            <label>
              Projektdatei
              <input data-testid="speicherpfad" value={speicherpfad} onChange={(e) => onSpeicherpfad(e.target.value)} placeholder="ersatzteil.cadstudio.json" />
            </label>
            <button type="button" data-testid="speichern" onClick={onSpeichern}>
              Speichern
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

function rechnerGesperrt(fehler: string[], rechnet: boolean, teile: Ersatzteil[]) {
  return rechnet || fehler.length > 0 || teile.length === 0;
}

function webglVorhanden(): boolean {
  try {
    const leinwand = document.createElement("canvas");
    return Boolean(leinwand.getContext("webgl") || leinwand.getContext("webgl2"));
  } catch {
    return false;
  }
}

function TeilVorschau({ soll, stl }: { soll: number[] | null; stl: string | null }) {
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
    const camera = new THREE.PerspectiveCamera(35, (el.clientWidth || 640) / 280, 0.1, 2000);
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
        const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: "#0f6e6e", roughness: 0.6 }));
        mesh.position.sub(mitte);
        scene.add(mesh);
        const weit = Math.max(groesse.x, groesse.y, groesse.z) * 2.2;
        camera.position.set(weit, weit * 0.7, weit);
        camera.lookAt(0, 0, 0);
        rahmen();
      });
    } else if (soll) {
      const [x, y, z] = soll;
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(x, z, y),
        new THREE.MeshStandardMaterial({ color: "#c9844a", roughness: 0.7 }),
      );
      scene.add(mesh);
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
      <div ref={host} className="buehne" data-testid="ersatz-vorschau" />
      <p className="kennzeichnung" data-testid="vorschau-art">
        {stl ? "3D-Ansicht aus der erzeugten STL-Datei." : "Vereinfachte Vorschau. Das ist noch nicht die echte Druckgeometrie."}
      </p>
    </div>
  );
}
