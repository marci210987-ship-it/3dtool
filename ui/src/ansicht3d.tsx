import { useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { api } from "./api";

export interface Netz {
  teil: string;
  name: string;
  punkte: number[];
  dreiecke: number[];
  bbox_mm: number[];
  volumen_mm3: number;
}

interface VorschauAntwort {
  ok: boolean;
  fehler: string[];
  netze: Netz[];
  hinweise: string[];
  ohne_freecad?: boolean;
}

type Blick = "iso" | "vorne" | "oben" | "seite";

const FARBEN = ["#00ae42", "#3b82c4", "#d98a1f", "#8a5fc7"];

/** Teile nebeneinander legen (nur bei mehreren Körpern, z. B. Gehäuse und Deckel). Liefert den x-Versatz je Netz. */
export function versaetze(netze: Pick<Netz, "bbox_mm">[], abstand = 10): number[] {
  if (netze.length <= 1) return netze.map(() => 0);
  let x = 0;
  return netze.map((n) => {
    const versatz = x - n.bbox_mm[0];
    x += n.bbox_mm[3] - n.bbox_mm[0] + abstand;
    return versatz;
  });
}

/**
 * Echte Geometrie als 3D-Ansicht. Der Dienst baut die Körper in FreeCAD (wie beim Export) und liefert Dreiecksnetze.
 * Änderungen werden nach kurzer Pause neu berechnet. Ohne FreeCAD oder bei ungültigen Eingaben steht die Meldung da.
 */
export function Ansicht3D({
  projekt,
  teilIds,
  freecadPfad,
  modus,
  titel = "3D-Ansicht",
}: {
  projekt: unknown;
  teilIds?: string[];
  /** Bereich, aus dem gebaut wird: ersatz, kabel oder gehaeuse (sonst gezeichnete Teile aus teilIds) */
  modus?: "ersatz" | "kabel" | "gehaeuse";
  freecadPfad?: string;
  titel?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const szene = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    controls: OrbitControls;
    gruppe: THREE.Group;
    zeichnen: () => void;
  } | null>(null);
  const [offen, setOffen] = useState(true);
  const [status, setStatus] = useState<"leer" | "rechnet" | "fertig" | "fehler">("leer");
  const [fehler, setFehler] = useState<string[]>([]);
  const [hinweise, setHinweise] = useState<string[]>([]);
  const [netze, setNetze] = useState<Netz[]>([]);
  const [keinWebGL, setKeinWebGL] = useState(false);
  const zaehler = useRef(0);
  const schluessel = JSON.stringify([projekt, teilIds, freecadPfad, modus]);

  // Bühne einmal aufbauen
  useEffect(() => {
    const el = host.current;
    if (!el || !offen) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setKeinWebGL(true);
      return;
    }
    setKeinWebGL(false);
    const hoehe = 380;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(el.clientWidth || 600, hoehe);
    el.innerHTML = "";
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#eef0f3");
    const camera = new THREE.PerspectiveCamera(35, (el.clientWidth || 600) / hoehe, 0.5, 5000);
    camera.position.set(160, 140, 220);
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const licht = new THREE.DirectionalLight(0xffffff, 1.1);
    licht.position.set(150, 300, 200);
    scene.add(licht);
    const gegenlicht = new THREE.DirectionalLight(0xffffff, 0.35);
    gegenlicht.position.set(-200, 100, -150);
    scene.add(gegenlicht);
    // Druckbett 256 × 256 mm: x nach rechts, y (hinten) nach hinten
    const bett = new THREE.GridHelper(256, 25.6, 0xb8bec8, 0xdde1e7);
    bett.position.set(128, 0, -128);
    scene.add(bett);
    const gruppe = new THREE.Group();
    gruppe.rotation.x = -Math.PI / 2; // Modell: z nach oben, y nach hinten
    scene.add(gruppe);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(60, 10, -40);
    const zeichnen = () => renderer.render(scene, camera);
    controls.addEventListener("change", zeichnen);
    szene.current = { renderer, scene, camera, controls, gruppe, zeichnen };
    const beobachter = new ResizeObserver(() => {
      const breite = el.clientWidth || 600;
      renderer.setSize(breite, hoehe);
      camera.aspect = breite / hoehe;
      camera.updateProjectionMatrix();
      zeichnen();
    });
    beobachter.observe(el);
    zeichnen();
    return () => {
      beobachter.disconnect();
      controls.dispose();
      renderer.dispose();
      szene.current = null;
    };
  }, [offen]);

  // Netze in die Bühne setzen
  useEffect(() => {
    const s = szene.current;
    if (!s) return;
    for (const kind of [...s.gruppe.children]) {
      s.gruppe.remove(kind);
      kind.traverse((o) => {
        const m = o as THREE.Mesh;
        m.geometry?.dispose();
        const mat = m.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
        else mat?.dispose();
      });
    }
    const dx = versaetze(netze);
    netze.forEach((netz, i) => {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(netz.punkte, 3));
      geo.setIndex(netz.dreiecke);
      const flach = geo.toNonIndexed();
      flach.computeVertexNormals();
      geo.dispose();
      const mesh = new THREE.Mesh(flach, new THREE.MeshStandardMaterial({ color: FARBEN[i % FARBEN.length], roughness: 0.6, metalness: 0.05 }));
      const kanten = new THREE.LineSegments(new THREE.EdgesGeometry(flach, 28), new THREE.LineBasicMaterial({ color: 0x1b2a3f }));
      const teilGruppe = new THREE.Group();
      teilGruppe.add(mesh, kanten);
      teilGruppe.position.x = dx[i];
      s.gruppe.add(teilGruppe);
    });
    if (netze.length) {
      const box = new THREE.Box3().setFromObject(s.gruppe);
      const mitte = box.getCenter(new THREE.Vector3());
      const groesse = box.getSize(new THREE.Vector3());
      s.controls.target.copy(mitte);
      const radius = Math.max(groesse.length() / 2, 10);
      const abstand = (radius / Math.tan((s.camera.fov * Math.PI) / 360)) * 0.9;
      const richtung = new THREE.Vector3(0.55, 0.45, 0.75).normalize();
      s.camera.position.copy(mitte).addScaledVector(richtung, abstand);
      s.camera.near = Math.max(0.5, abstand / 200);
      s.camera.far = abstand * 40;
      s.camera.updateProjectionMatrix();
      s.controls.update();
    }
    s.zeichnen();
  }, [netze, offen]);

  // Berechnen nach kurzer Pause
  useEffect(() => {
    if (!offen) return;
    const nr = ++zaehler.current;
    setStatus("rechnet");
    const timer = window.setTimeout(async () => {
      try {
        const antwort = await api<VorschauAntwort>("vorschau", { projekt, teil_ids: teilIds ?? [], freecad_pfad: freecadPfad ?? "", modus: modus ?? "" });
        if (nr !== zaehler.current) return;
        const r = antwort.result;
        if (antwort.ok && r) {
          setNetze(r.netze);
          setFehler([]);
          setHinweise(r.hinweise || []);
          setStatus("fertig");
        } else {
          setFehler(r?.fehler?.length ? r.fehler : [antwort.fehler || "Die Vorschau ist fehlgeschlagen."]);
          setHinweise([]);
          setNetze([]);
          setStatus("fehler");
        }
      } catch {
        if (nr !== zaehler.current) return;
        setFehler(["Der Dienst antwortet nicht."]);
        setNetze([]);
        setStatus("fehler");
      }
    }, 700);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schluessel, offen]);

  const blick = useCallback((b: Blick) => {
    const s = szene.current;
    if (!s) return;
    const box = new THREE.Box3().setFromObject(s.gruppe);
    const mitte = box.isEmpty() ? new THREE.Vector3(60, 10, -40) : box.getCenter(new THREE.Vector3());
    const gr = box.isEmpty() ? new THREE.Vector3(100, 20, 100) : box.getSize(new THREE.Vector3());
    const radius = Math.max(gr.length() / 2, 10);
    const r = (radius / Math.tan((s.camera.fov * Math.PI) / 360)) * 0.9;
    const pos = {
      iso: [mitte.x + r * 0.55 * 0.78, mitte.y + r * 0.45 * 0.78, mitte.z + r * 0.75 * 0.78],
      vorne: [mitte.x, mitte.y, mitte.z + r],
      oben: [mitte.x, mitte.y + r, mitte.z + 0.001],
      seite: [mitte.x + r, mitte.y, mitte.z],
    }[b] as [number, number, number];
    s.controls.target.copy(mitte);
    s.camera.position.set(...pos);
    s.controls.update();
    s.zeichnen();
  }, []);

  const gesamt = netze.reduce((a, n) => a + n.volumen_mm3, 0);

  return (
    <details className="ansicht3d" open={offen} onToggle={(e) => setOffen((e.currentTarget as HTMLDetailsElement).open)} data-testid="ansicht3d">
      <summary>
        {titel} <span className="leise" data-testid="ansicht3d-status">{status === "rechnet" ? "rechnet …" : status === "fertig" ? "aktuell" : status === "fehler" ? "nicht möglich" : ""}</span>
      </summary>
      {keinWebGL && <p className="hinweis">Diese Oberfläche kann kein WebGL darstellen. Die 3D-Ansicht ist nicht verfügbar.</p>}
      <div ref={host} className="buehne" style={{ width: "100%", minHeight: 380, opacity: status === "rechnet" ? 0.7 : 1 }} data-testid="ansicht3d-buehne" />
      <div className="knopfzeile">
        {(["iso", "vorne", "oben", "seite"] as Blick[]).map((b) => (
          <button key={b} type="button" onClick={() => blick(b)}>
            {b === "iso" ? "Schräg" : b === "vorne" ? "Vorne" : b === "oben" ? "Oben" : "Seite"}
          </button>
        ))}
      </div>
      {fehler.length > 0 && (
        <ul className="fehlerliste" data-testid="ansicht3d-fehler" style={{ color: "#b3434b" }}>
          {fehler.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      )}
      {netze.length > 0 && status !== "fehler" && (
        <p className="leise" data-testid="ansicht3d-info">
          {netze.map((n) => `${n.name}: ${Math.round((n.bbox_mm[3] - n.bbox_mm[0]) * 10) / 10} × ${Math.round((n.bbox_mm[4] - n.bbox_mm[1]) * 10) / 10} × ${Math.round((n.bbox_mm[5] - n.bbox_mm[2]) * 10) / 10} mm`).join(" · ")}
          {" · "}Volumen {Math.round(gesamt / 100) / 10} cm³. Echte Geometrie wie beim Export; ziehen dreht, Rad zoomt, rechte Maustaste verschiebt.
        </p>
      )}
      {hinweise.map((h, i) => (
        <p key={i} className="hinweis" data-testid="ansicht3d-hinweis">
          {h}
        </p>
      ))}
    </details>
  );
}
