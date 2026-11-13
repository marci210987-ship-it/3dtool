import { useEffect, useRef } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { dateiUrl } from "./api";
import { Box, footprint } from "./layout";

interface TeilDatei {
  id: string;
  stl?: string;
  ok?: boolean;
  platz?: {
    zentriert?: boolean;
    mitte_x_mm?: number;
    mitte_y_mm?: number;
    links_mm?: number;
    vorne_mm?: number;
    z_mm?: number;
  };
}

export function Vorschau({
  breite,
  tiefe,
  boxen,
  ursprungX,
  ursprungY,
  plattenhoehe,
  dateien,
}: {
  breite: number;
  tiefe: number;
  boxen: Box[];
  ursprungX: number;
  ursprungY: number;
  plattenhoehe: number;
  dateien: TeilDatei[] | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const echt = Boolean(dateien && dateien.length && dateien.every((d) => d.ok && d.stl));

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(el.clientWidth, 360);
    el.innerHTML = "";
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#f4f1ea");
    const camera = new THREE.PerspectiveCamera(35, el.clientWidth / 360, 1, 5000);
    camera.position.set(breite * 0.15, Math.max(breite, tiefe) * 0.85, tiefe * 1.15);
    camera.lookAt(breite / 2, 0, tiefe / 2);
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const licht = new THREE.DirectionalLight(0xffffff, 1.1);
    licht.position.set(200, 400, 100);
    scene.add(licht);
    const boden = new THREE.Mesh(
      new THREE.BoxGeometry(breite, 2, tiefe),
      new THREE.MeshStandardMaterial({ color: "#d9d3c7" }),
    );
    boden.position.set(breite / 2, -1, tiefe / 2);
    scene.add(boden);

    let abbruch = false;
    if (!echt) {
      for (const box of boxen) {
        const [x, y, w, h] = footprint(box);
        const hoehe = box.ez * 7 + (box.stapellippe && box.art !== "besteck" ? 4 : 0);
        const mesh = new THREE.Mesh(
          new THREE.BoxGeometry(w * 42 - 0.5, hoehe, h * 42 - 0.5),
          new THREE.MeshStandardMaterial({ color: box.art === "besteck" ? "#c9844a" : "#0f6e6e", roughness: 0.55 }),
        );
        mesh.position.set(ursprungX + (x + w / 2) * 42, plattenhoehe + hoehe / 2, ursprungY + (y + h / 2) * 42);
        scene.add(mesh);
      }
    } else {
      const loader = new STLLoader();
      Promise.all(
        (dateien || []).filter((d) => d.stl).map(
          (d) =>
            new Promise<void>((resolve) => {
              loader.load(dateiUrl(d.stl!), (geo) => {
                if (abbruch) return resolve();
                geo.computeVertexNormals();
                const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: "#0f6e6e", metalness: 0.05, roughness: 0.62 }));
                const platz = d.platz || {};
                const z = platz.z_mm || 0;
                if (platz.zentriert) {
                  mesh.position.set(platz.mitte_x_mm || 0, z, platz.mitte_y_mm || 0);
                } else {
                  mesh.position.set(platz.links_mm || 0, z, platz.vorne_mm || 0);
                }
                mesh.rotation.x = -Math.PI / 2;
                scene.add(mesh);
                resolve();
              }, undefined, () => resolve());
            }),
        ),
      ).then(() => {
        if (!abbruch) renderer.render(scene, camera);
      });
    }

    renderer.render(scene, camera);
    const id = window.setInterval(() => renderer.render(scene, camera), 400);
    return () => {
      abbruch = true;
      window.clearInterval(id);
      renderer.dispose();
    };
  }, [breite, tiefe, boxen, ursprungX, ursprungY, plattenhoehe, dateien, echt]);

  return (
    <div className="vorschau">
      <div ref={host} className="buehne" />
      <p className="kennzeichnung" data-testid="vorschau-art">
        {echt ? "3D-Ansicht aus den erzeugten STL-Dateien." : "Vereinfachte Vorschau. Das ist noch nicht die echte Druckgeometrie."}
      </p>
    </div>
  );
}
