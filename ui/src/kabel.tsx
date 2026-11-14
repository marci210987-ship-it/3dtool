import { useEffect, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { dateiUrl } from "./api";

export interface KabelFeld {
  key: string;
  label: string;
  min?: number;
  max?: number;
  step?: number;
  einheit?: string;
  gruppe?: string;
  auswahl?: Array<{ wert: string; text: string }>;
}

export interface KabelArt {
  id: string;
  name: string;
  text: string;
  druck: string;
  standard: Record<string, string | number>;
  felder: KabelFeld[];
}

export interface Kabelteil {
  id: string;
  art: string;
  name: string;
  parameter: Record<string, string | number>;
}

const PROFIL = ["innenbreite_mm", "innenhoehe_mm", "wand_mm", "spiel_mm", "zapfen_mm"];

export function KabelAnsicht({
  katalog,
  teile,
  aktivId,
  fehler,
  soll,
  stuecke,
  onWaehlen,
  onNeu,
  onEntfernen,
  onParameter,
  onAngleichen,
  onErzeugen,
  ergebnis,
  rechnet,
  jobText,
  speicherpfad,
  onSpeicherpfad,
  onSpeichern,
}: {
  katalog: KabelArt[];
  teile: Kabelteil[];
  aktivId: string | null;
  fehler: string[];
  soll: number[] | null;
  stuecke: number;
  onWaehlen: (id: string) => void;
  onNeu: (art: string) => void;
  onEntfernen: (id: string) => void;
  onParameter: (id: string, key: string, wert: string | number) => void;
  onAngleichen: () => void;
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
  const profil = art?.felder.filter((f) => f.gruppe === "profil") ?? [];
  const eigen = art?.felder.filter((f) => f.gruppe !== "profil") ?? [];
  const passung = fehler.filter((f) => f.includes("passen nicht"));
  return (
    <main>
      <h1>Kabelmanagement</h1>
      <p className="leise">
        Kanäle, Ecken und Halter eines Systems teilen sich Innenmaß, Wand, Spiel und Einstecktiefe. So passen Stecker und Buchse zusammen. Maße in Millimeter.
      </p>
      <div className="editor">
        <aside className="katalog">
          <h2>Teile</h2>
          <ul>
            {katalog.map((eintrag) => (
              <li key={eintrag.id}>
                <button type="button" data-testid={`kabel-${eintrag.id}`} onClick={() => onNeu(eintrag.id)}>
                  <strong>{eintrag.name}</strong>
                  <span>{eintrag.text}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <div>
          {teile.length > 0 && (
            <div className="knopfzeile">
              {teile.map((teil) => (
                <button key={teil.id} type="button" className={teil.id === aktiv?.id ? "primaer" : ""} data-testid={`kabel-teil-${teil.id}`} onClick={() => onWaehlen(teil.id)}>
                  {teil.name}
                </button>
              ))}
            </div>
          )}
          {art && aktiv && (
            <div className="formular" data-testid="kabel-form">
              <h2>Verbindung</h2>
              {profil.map((feld) => (
                <Feld key={feld.key} feld={feld} teil={aktiv} onParameter={onParameter} />
              ))}
              <button type="button" data-testid="kabel-angleichen" onClick={onAngleichen}>
                Dieses Profil auf alle Teile übertragen
              </button>
              <h2>{art.name}</h2>
              {eigen.map((feld) => (
                <Feld key={feld.key} feld={feld} teil={aktiv} onParameter={onParameter} />
              ))}
              {teile.length > 1 && (
                <button type="button" data-testid="kabel-entfernen" onClick={() => onEntfernen(aktiv.id)}>
                  Dieses Teil entfernen
                </button>
              )}
            </div>
          )}
          {art && <p className="hinweis">{art.druck}</p>}
          {soll && !fehler.length && (
            <p data-testid="kabel-mass">
              Außenmaß eines Stücks {soll.map((v) => v.toLocaleString("de-DE", { maximumFractionDigits: 1 })).join(" × ")} mm
              {stuecke > 1 ? ` Wird in ${stuecke} Stücke geteilt.` : ""}
            </p>
          )}
          {passung.length > 0 && (
            <div className="alarm" role="alert" data-testid="kabel-passung">
              {passung.map((f) => (
                <p key={f}>{f}</p>
              ))}
            </div>
          )}
          {fehler.filter((f) => !f.includes("passen nicht")).length > 0 && (
            <div className="alarm" role="alert" data-testid="kabel-fehler">
              {fehler
                .filter((f) => !f.includes("passen nicht"))
                .map((f) => (
                  <p key={f}>{f}</p>
                ))}
            </div>
          )}
          <Skizze soll={soll} />
          <TeilVorschau soll={soll} stl={stl || null} />
          <button type="button" className="primaer" data-testid="kabel-erzeugen" disabled={rechnerGesperrt(fehler, rechnet, teile)} onClick={onErzeugen}>
            {rechnet ? "Berechnet …" : "Teile berechnen"}
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
              <p className="erfolg" data-testid="export-erfolg">Die Teile sind erzeugt. Datei, Netz und Körper sind geprüft.</p>
              <ul className="dateien" data-testid="kabel-dateien">
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
              <input data-testid="speicherpfad" value={speicherpfad} onChange={(e) => onSpeicherpfad(e.target.value)} placeholder="kabel.cadstudio.json" />
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

export function profilKopieren(teile: Kabelteil[], vonId: string): Kabelteil[] {
  const quelle = teile.find((t) => t.id === vonId);
  if (!quelle) return teile;
  return teile.map((teil) => {
    if (teil.id === vonId) return teil;
    const parameter = { ...teil.parameter };
    for (const key of PROFIL) parameter[key] = quelle.parameter[key];
    return { ...teil, parameter };
  });
}

function Feld({ feld, teil, onParameter }: { feld: KabelFeld; teil: Kabelteil; onParameter: (id: string, key: string, wert: string | number) => void }) {
  if (feld.auswahl) {
    return (
      <label>
        {feld.label}
        <select data-testid={`feld-${feld.key}`} value={String(teil.parameter[feld.key] ?? "")} onChange={(e) => onParameter(teil.id, feld.key, e.target.value)}>
          {feld.auswahl.map((wahl) => (
            <option key={wahl.wert} value={wahl.wert}>
              {wahl.text}
            </option>
          ))}
        </select>
      </label>
    );
  }
  return (
    <label>
      {feld.label}
      <input
        data-testid={`feld-${feld.key}`}
        inputMode="decimal"
        value={String(teil.parameter[feld.key] ?? "")}
        onChange={(e) => onParameter(teil.id, feld.key, e.target.value.replace(",", "."))}
      />
      {feld.einheit && <span>{feld.einheit}</span>}
    </label>
  );
}

function rechnerGesperrt(fehler: string[], rechnet: boolean, teile: Kabelteil[]) {
  return rechnet || fehler.length > 0 || teile.length === 0;
}

function Skizze({ soll }: { soll: number[] | null }) {
  if (!soll) return null;
  const [laenge, breite, hoehe] = soll;
  const mass = Math.max(laenge, breite, 1);
  const b = 280;
  const h = 72;
  const nutz = (laenge / mass) * (b - 16);
  const quer = Math.max(8, (breite / mass) * 36);
  return (
    <div className="vorschau">
      <svg data-testid="kabel-skizze" viewBox={`0 0 ${b} ${h}`} width="100%" height="72" role="img" aria-label="Vereinfachte Skizze">
        <rect x="8" y={(h - quer) / 2} width={nutz} height={quer} fill="#e7d7c3" stroke="#8a5a32" />
        <text x="8" y="14" fontSize="11" fill="#5c5146">
          vereinfachte Skizze {laenge.toLocaleString("de-DE", { maximumFractionDigits: 0 })} × {breite.toLocaleString("de-DE", { maximumFractionDigits: 0 })} × {hoehe.toLocaleString("de-DE", { maximumFractionDigits: 0 })} mm
        </text>
      </svg>
      <p className="kennzeichnung">Vereinfachte Skizze. Das ist noch nicht die Druckgeometrie.</p>
    </div>
  );
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
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(x, z, y), new THREE.MeshStandardMaterial({ color: "#c9844a", roughness: 0.7 }));
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
      <div ref={host} className="buehne" data-testid="kabel-vorschau" />
      <p className="kennzeichnung" data-testid="vorschau-art">
        {stl ? "3D-Ansicht aus der erzeugten STL-Datei." : "Vereinfachte Vorschau. Das ist noch nicht die echte Druckgeometrie."}
      </p>
    </div>
  );
}
