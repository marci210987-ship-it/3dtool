const BASIS = import.meta.env.VITE_API ?? "http://127.0.0.1:47321";

let token = "";

export async function sitzung(): Promise<string> {
  if (token) return token;
  const fenster = window as unknown as { __TAURI_INTERNALS__?: unknown };
  if (fenster.__TAURI_INTERNALS__) {
    const { invoke } = await import("@tauri-apps/api/core");
    token = await invoke<string>("sitzungstoken");
    return token;
  }
  const antwort = await fetch(`${BASIS}/sitzung`);
  const daten = await antwort.json();
  token = String(daten.token || "");
  return token;
}

async function kopf(): Promise<Record<string, string>> {
  const wert = await sitzung();
  return { "Content-Type": "application/json", "X-CADStudio-Token": wert };
}

export async function api<T = unknown>(cmd: string, body: Record<string, unknown> = {}): Promise<{ ok: boolean; fehler?: string; result?: T; job?: string; out_dir?: string; projekt?: unknown; pfad?: string }> {
  const antwort = await fetch(`${BASIS}/api`, {
    method: "POST",
    headers: await kopf(),
    body: JSON.stringify({ cmd, ...body }),
  });
  return antwort.json();
}

export async function gesundheit(): Promise<boolean> {
  try {
    const antwort = await fetch(`${BASIS}/health`);
    const daten = await antwort.json();
    return Boolean(daten.ok);
  } catch {
    return false;
  }
}

export function dateiUrl(pfad: string): string {
  const zusatz = token ? `&token=${encodeURIComponent(token)}` : "";
  return `${BASIS}/datei?pfad=${encodeURIComponent(pfad)}${zusatz}`;
}

export async function jobStatus(id: string): Promise<Record<string, unknown>> {
  const antwort = await fetch(`${BASIS}/api/job?id=${encodeURIComponent(id)}`, { headers: await kopf() });
  return antwort.json();
}

export interface Schublade {
  innenbreite_mm: number;
  innentiefe_mm: number;
  nutzhoehe_mm: number;
  spiel_mm: number;
  rand_links_mm: number;
  rand_rechts_mm: number;
  rand_vorne_mm: number;
  rand_hinten_mm: number;
  verbinder_spiel_mm: number;
  wandstaerke_mm: number;
  boden_platte_mm: number;
  material: string;
  bauraum_mm: number[];
}

export interface ProjektDatei {
  format: string;
  version: number;
  name: string;
  schublade: Schublade;
  boxen: Array<Record<string, unknown>>;
  notiz: string;
}

export function leereSchublade(vorgaben: Partial<Schublade> = {}): Schublade {
  return {
    innenbreite_mm: 480,
    innentiefe_mm: 420,
    nutzhoehe_mm: vorgaben.nutzhoehe_mm ?? 80,
    spiel_mm: vorgaben.spiel_mm ?? 1,
    rand_links_mm: 0,
    rand_rechts_mm: 0,
    rand_vorne_mm: 0,
    rand_hinten_mm: 0,
    verbinder_spiel_mm: vorgaben.verbinder_spiel_mm ?? 0.2,
    wandstaerke_mm: vorgaben.wandstaerke_mm ?? 1.2,
    boden_platte_mm: vorgaben.boden_platte_mm ?? 0.8,
    material: vorgaben.material ?? "PLA",
    bauraum_mm: vorgaben.bauraum_mm ?? [256, 256, 256],
  };
}
