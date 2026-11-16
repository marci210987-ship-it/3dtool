import { useState } from "react";
import { api } from "./api";
import { neuesTeil, type Eigenteil } from "./zeichnen";

export interface Druckprofil {
  id: string; name: string; material: string; bauraum_mm: number[];
  spiel_mm: number; schubladenspiel_mm: number; gedruckt: boolean;
}
export function profilPruefen(p: Druckprofil): string | null {
  if (!p.name.trim()) return "Bitte einen Profilnamen eingeben.";
  if (p.bauraum_mm.length !== 3 || p.bauraum_mm.some((x) => !Number.isFinite(x) || x < 20 || x > 2000)) return "Bauraum: drei Maße zwischen 20 und 2000 mm eingeben.";
  if (!Number.isFinite(p.spiel_mm) || p.spiel_mm < 0.1 || p.spiel_mm > 0.5) return "Passungsspiel muss zwischen 0,10 und 0,50 mm liegen.";
  if (!Number.isFinite(p.schubladenspiel_mm) || p.schubladenspiel_mm < 0 || p.schubladenspiel_mm > 10) return "Schubladenspiel muss zwischen 0 und 10 mm liegen.";
  return null;
}

/** Lochspiel je Seite. Pro Wert eine Lochplatte und ein unabhängiger, gleich großer Prüfstift. */
export function kalibrierteile(): Eigenteil[] {
  const teile: Eigenteil[] = [];
  for (const spiel of [0.1, 0.2, 0.3, 0.4, 0.5]) {
    const platte = neuesTeil(teile);
    platte.name = `Lochplatte ${spiel.toFixed(2)} mm je Seite`;
    platte.hoehe_mm = 5;
    platte.formen = [
      { typ: "rechteck", x: 0, y: 0, b: 20, t: 20, loch: false },
      { typ: "kreis", x: 10, y: 10, r: 5 + spiel, loch: true },
    ];
    platte.notiz = "Teststück für Loch/Stift-Passung; ersetzt keinen Test der konkreten Steckverbindung oder des Deckels.";
    teile.push(platte);
    const stift = neuesTeil(teile);
    stift.name = `Prüfstift Ø10 mm für ${spiel.toFixed(2)}`;
    stift.hoehe_mm = 5;
    stift.formen = [{ typ: "kreis", x: 5, y: 5, r: 5, loch: false }];
    teile.push(stift);
  }
  return teile;
}

export function Druckprofile({ werte, onChange, onAnwenden, onKalibrieren }: {
  werte: Record<string, unknown>; onChange: (w: Record<string, unknown>) => void;
  onAnwenden: (p: Druckprofil) => void; onKalibrieren: (teile: Eigenteil[]) => void;
}) {
  const [wahl, setWahl] = useState("");
  const [name, setName] = useState("Mein Drucker · PLA");
  const [material, setMaterial] = useState("PLA");
  const [masse, setMasse] = useState(["256", "256", "256"]);
  const [spiel, setSpiel] = useState("0,20");
  const [wand, setWand] = useState("1,0");
  const [gedruckt, setGedruckt] = useState(false);
  const [meldung, setMeldung] = useState("");
  const [busy, setBusy] = useState(false);
  const profile = (Array.isArray(werte.druckprofile) ? werte.druckprofile : []) as Druckprofil[];
  function profil(): Druckprofil {
    const zahl = (s: string) => s.trim() ? Number(s.replace(",", ".")) : NaN;
    return { id: wahl || crypto.randomUUID(), name: name.trim(), material, bauraum_mm: masse.map(zahl), spiel_mm: zahl(spiel), schubladenspiel_mm: zahl(wand), gedruckt };
  }
  return <section className="druckprofile" aria-label="Druckprofile und Kalibrierung">
    <h2>Druckprofile und Passungskalibrierung</h2>
    <p>Profile speichern Druckermaße, Material und deine ermittelten Spiele. Ein Loch/Stift-Test gibt einen Ausgangswert; Deckel und Steckverbinder brauchen zusätzlich einen eigenen Testdruck.</p>
    <label>Gespeichertes Profil<select value={wahl} onChange={(e) => {
      setWahl(e.target.value);
      const p = profile.find((p) => p.id === e.target.value);
      if (p) { setName(p.name); setMaterial(p.material); setMasse(p.bauraum_mm.map(String)); setSpiel(String(p.spiel_mm)); setWand(String(p.schubladenspiel_mm)); setGedruckt(p.gedruckt); }
      else setGedruckt(false);
    }}><option value="">Neues Profil</option>{profile.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <div className="formular">
      <label>Profilname<input value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label>Profilmaterial<select value={material} onChange={(e) => { setMaterial(e.target.value); setGedruckt(false); }}><option>PLA</option><option>PETG</option><option>ABS</option></select></label>
      {masse.map((v, i) => <label key={i}>Bauraum {"XYZ"[i]} (mm)<input inputMode="decimal" value={v} onChange={(e) => { setMasse((a) => a.map((x, j) => i === j ? e.target.value : x)); setGedruckt(false); }} /></label>)}
      <label>Passungsspiel je Seite (mm)<input inputMode="decimal" value={spiel} onChange={(e) => { setSpiel(e.target.value); setGedruckt(false); }} /></label>
      <label>Schubladenspiel (mm)<input inputMode="decimal" value={wand} onChange={(e) => { setWand(e.target.value); setGedruckt(false); }} /></label>
    </div>
    <label className="check"><input type="checkbox" checked={gedruckt} onChange={(e) => setGedruckt(e.target.checked)} />Diese Werte habe ich mit meinem Drucker und Material geprüft.</label>
    <p className="hinweis">{gedruckt ? "Als eigener Drucktest gekennzeichnet." : "Noch nicht durch einen Drucktest bestätigt."}</p>
    <div className="knopfzeile">
      <button type="button" disabled={busy} onClick={async () => {
        const p = profil(); const fehler = profilPruefen(p);
        if (fehler) { setMeldung(fehler); return; }
        setBusy(true);
        try {
          const neu = { ...werte, druckprofile: [...profile.filter((alt) => alt.id !== p.id), p] };
          const r = await api<Record<string, unknown>>("settings_set", { settings: neu });
          if (!r.ok) throw new Error();
          onChange(r.result || neu); setWahl(p.id); setMeldung("Druckprofil gespeichert.");
        } catch { setMeldung("Profil konnte nicht gespeichert werden. Bitte Dienst prüfen."); }
        finally { setBusy(false); }
      }}>Druckprofil speichern</button>
      <button type="button" onClick={() => {
        const p = profil(); const fehler = profilPruefen(p);
        if (fehler) { setMeldung(fehler); return; }
        onAnwenden(p); setMeldung("Material und Bauraum im Projekt übernommen; Passungsspiel für Kabel und Gehäuse sowie Verbinder-Spiel für die Schublade übernommen.");
      }}>Auf aktuelles Projekt anwenden</button>
      <button type="button" onClick={() => onKalibrieren(kalibrierteile())}>Kalibrierprojekt mit fünf Spielmaßen erstellen</button>
    </div>
    {meldung && <p role="status">{meldung}</p>}
  </section>;
}
