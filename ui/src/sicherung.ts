import { useEffect, useRef, useState } from "react";

const KEY = "cadstudio.sicherung.v1";
export interface Sicherung { version: 1; zeit: string; projekt: Record<string, unknown>; pfad: string }
export function leseSicherung(): Sicherung | null {
  try {
    const d = JSON.parse(localStorage.getItem(KEY) || "null");
    return d?.version === 1 && d.projekt?.format === "cadstudio.projekt" && d.projekt?.schublade && Array.isArray(d.projekt.boxen) ? d : null;
  } catch { return null; }
}

/** Separate Rettungskopie; überschreibt niemals die manuell gespeicherte Projektdatei. */
export function useSicherung(projekt: Record<string, unknown>, pfad: string, aktiv: boolean) {
  const [rettung, setRettung] = useState(leseSicherung);
  const [hinweis, setHinweis] = useState("");
  const [basis, setBasis] = useState(() => JSON.stringify(projekt));
  const [begonnen, setBegonnen] = useState(false);
  const aktuell = JSON.stringify(projekt);
  const schmutzig = begonnen && aktuell !== basis;
  const live = useRef({ projekt, pfad, schmutzig, rettung });
  live.current = { projekt, pfad, schmutzig, rettung };
  useEffect(() => { if (aktiv) setBegonnen(true); }, [aktiv]);

  function sichern(): boolean {
    const v = live.current;
    if (!v.schmutzig || v.rettung) return false;
    try {
      localStorage.setItem(KEY, JSON.stringify({ version: 1, zeit: new Date().toISOString(), projekt: v.projekt, pfad: v.pfad }));
      setHinweis("Wiederherstellungskopie gesichert.");
      return true;
    } catch {
      setHinweis("Automatische Sicherung fehlgeschlagen. Bitte Projekt manuell speichern.");
      return false;
    }
  }
  useEffect(() => {
    if (!schmutzig || rettung) return;
    const timer = window.setTimeout(sichern, 1000);
    return () => window.clearTimeout(timer);
  }, [aktuell, pfad, schmutzig, rettung]);
  useEffect(() => {
    const schliessen = (e: BeforeUnloadEvent) => {
      if (!live.current.schmutzig) return;
      sichern();
      e.preventDefault();
      e.returnValue = "";
    };
    const versteckt = () => { if (document.visibilityState === "hidden") sichern(); };
    window.addEventListener("beforeunload", schliessen);
    document.addEventListener("visibilitychange", versteckt);
    // Tauri benötigt zusätzlich das native Schließereignis.
    let weg: (() => void) | undefined;
    let beendet = false;
    if ("__TAURI_INTERNALS__" in window) {
      import("@tauri-apps/api/window").then(async ({ getCurrentWindow }) => {
        const abmelden = await getCurrentWindow().onCloseRequested((event) => {
          if (live.current.schmutzig) {
            sichern();
            if (!window.confirm("Ungespeicherte Änderungen. CAD Studio trotzdem schließen?")) event.preventDefault();
          }
        });
        if (beendet) abmelden(); else weg = abmelden;
      }).catch(() => setHinweis("Schließschutz nicht verfügbar. Bitte vor dem Schließen speichern."));
    }
    return () => {
      beendet = true;
      weg?.();
      window.removeEventListener("beforeunload", schliessen);
      document.removeEventListener("visibilitychange", versteckt);
    };
  }, []);
  function verwerfen() {
    try { localStorage.removeItem(KEY); } catch { /* Der alte Entwurf bleibt verfügbar. */ }
    setRettung(null);
  }
  function gespeichert(daten: Record<string, unknown>) {
    setBasis(JSON.stringify(daten));
    // Nur löschen, wenn die gespeicherte Fassung noch die aktuelle ist.
    if (JSON.stringify(daten) === JSON.stringify(live.current.projekt)) verwerfen();
  }
  return { rettung, hinweis, schmutzig, verwerfen, gespeichert,
    wechseln: () => !schmutzig || window.confirm("Ungespeicherte Änderungen verwerfen und ein anderes Projekt öffnen?"),
  };
}
