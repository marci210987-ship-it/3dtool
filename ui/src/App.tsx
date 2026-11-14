import { useEffect, useMemo, useRef, useState } from "react";
import { api, dateiUrl, gesundheit, jobStatus, leereSchublade, Schublade } from "./api";
import { Ansicht3D } from "./ansicht3d";
import { Editor } from "./editor";
import { ErsatzArt, Ersatzteil, ErsatzteilAnsicht } from "./ersatzteile";
import { KabelArt, Kabelteil, KabelAnsicht, profilKopieren } from "./kabel";
import { GehaeuseAnsicht, GehaeuseDaten, Vorlage, gehaeuseZahlen } from "./gehaeuse";
import { Box, KATALOG } from "./layout";
import { Vorschau } from "./preview";
import { Eigenteil, neuesTeil, teilVonServer } from "./zeichnen";
import { type MeineVorlage, Zeichnen } from "./zeichenblatt";

type Ansicht = "start" | "arbeit" | "einstellungen" | "ersatz" | "kabel" | "gehaeuse";

interface Plan {
  ok: boolean;
  fehler: string[];
  hinweise: string[];
  text: string;
  einheiten_x: number;
  einheiten_y: number;
  nutz_x: number;
  nutz_y: number;
  rest_x: number;
  rest_y: number;
  plattenhoehe_mm: number;
  ursprung_x_mm: number;
  ursprung_y_mm: number;
  raster_mm: number;
  platten: Array<{
    id: string;
    einheiten_x: number;
    einheiten_y: number;
    breite_mm: number;
    tiefe_mm: number;
    passt_in_bauraum: boolean;
    lage: { links_mm: number; vorne_mm: number; breite_mm: number; tiefe_mm: number };
  }>;
  verbinder_anzahl: number;
  randstreifen: Array<{ seite: string; breite_mm: number; laenge_mm: number }>;
  randstreifen_hinweis: string;
  freie_zellen: Array<{ x: number; y: number }>;
  boxen_mm?: Array<{ id: string; links_mm: number; vorne_mm: number; breite_mm: number; tiefe_mm: number }>;
}

interface Ergebnis {
  ok: boolean;
  fehler?: string[];
  teile?: Array<{
    id: string;
    name?: string;
    ok: boolean;
    anzahl?: number;
    dateien?: Array<{ id: string; stl?: string; fcstd?: string; ok?: boolean; platz?: Record<string, number | boolean> }>;
  }>;
  montage?: { html?: string; pdf?: string; png?: string; svg?: string };
  stueckliste?: string;
  hinweise?: string[];
}

const BEREICHE = [
  { id: "schublade", titel: "Schubladen-Konfigurator", text: "Schublade ausmessen, Raster legen, Boxen verteilen, Druckdateien erzeugen.", bereit: true },
  { id: "zeichnen", titel: "Eigene Teile zeichnen", text: "Formen zeichnen, extrudieren und als STL/FCStd ausgeben, ohne Schublade.", bereit: true },
  { id: "ersatz", titel: "Ersatzteile", text: "Clip, Hülse, Scheibe, Haken und andere kleine Teile erzeugen.", bereit: true },
  { id: "kabel", titel: "Kabelmanagement", text: "Kanäle, Ecken und Halter mit gemeinsamer Steckverbindung.", bereit: true },
  { id: "gehaeuse", titel: "Elektronikgehäuse", text: "Gehäuse mit Deckel, Platinenstützen und Wandöffnungen.", bereit: true },
];

export function App() {
  const [ansicht, setAnsicht] = useState<Ansicht>("start");
  const [schritt, setSchritt] = useState(1);
  const [name, setName] = useState("Schublade");
  const [schublade, setSchublade] = useState<Schublade>(leereSchublade());
  const [boxen, setBoxen] = useState<Box[]>([]);
  const [eigene, setEigene] = useState<Eigenteil[]>([]);
  const [nurEigene, setNurEigene] = useState(false);
  const [ersatzteile, setErsatzteile] = useState<Ersatzteil[]>([]);
  const [nurErsatz, setNurErsatz] = useState(false);
  const [ersatzKatalog, setErsatzKatalog] = useState<ErsatzArt[]>([]);
  const [ersatzAktiv, setErsatzAktiv] = useState<string | null>(null);
  const [ersatzFehler, setErsatzFehler] = useState<string[]>([]);
  const [ersatzSoll, setErsatzSoll] = useState<number[] | null>(null);
  const [kabel, setKabel] = useState<Kabelteil[]>([]);
  const [nurKabel, setNurKabel] = useState(false);
  const [kabelKatalog, setKabelKatalog] = useState<KabelArt[]>([]);
  const [kabelAktiv, setKabelAktiv] = useState<string | null>(null);
  const [kabelFehler, setKabelFehler] = useState<string[]>([]);
  const [kabelSoll, setKabelSoll] = useState<number[] | null>(null);
  const [kabelStuecke, setKabelStuecke] = useState(1);
  const [gehaeuse, setGehaeuse] = useState<GehaeuseDaten>({ oeffnungen: [] });
  const [nurGehaeuse, setNurGehaeuse] = useState(false);
  const [vorlagen, setVorlagen] = useState<Record<string, Vorlage>>({});
  const [gehaeuseFehler, setGehaeuseFehler] = useState<string[]>([]);
  const [gehaeuseSoll, setGehaeuseSoll] = useState<{ korpus: number[]; deckel: number[] } | null>(null);
  const [meineVorlagen, setMeineVorlagen] = useState<MeineVorlage[]>([]);
  const [wuensche, setWuensche] = useState<Record<string, number>>({});
  // Zu jedem Wunsch: gewünschte Seite der Schublade und Gruppe (zusammen platzieren)
  const [wunschZusatz, setWunschZusatz] = useState<Record<string, { seite: string; gruppe: string }>>({});
  const [restFuellen, setRestFuellen] = useState(true);
  const [fuellstil, setFuellstil] = useState("einheitlich");
  const [plan, setPlan] = useState<Plan | null>(null);
  // Antworten von „plane“ können außer der Reihe eintreffen: nur die jüngste Anfrage darf den Plan setzen
  const planNr = useRef(0);
  async function planAbrufen(projektDaten: Record<string, unknown>) {
    const nr = ++planNr.current;
    const antwort = await api<Plan>("plane", { projekt: projektDaten });
    return { antwort, aktuell: nr === planNr.current };
  }
  const [dienst, setDienst] = useState<boolean | null>(null);
  const [recent, setRecent] = useState<Array<{ pfad: string; name: string }>>([]);
  const [einstellungen, setEinstellungen] = useState<Record<string, unknown>>({});
  const [freecad, setFreecad] = useState<Record<string, unknown> | null>(null);
  const [speicherpfad, setSpeicherpfad] = useState("");
  const [meldung, setMeldung] = useState("");
  const [jobText, setJobText] = useState("");
  const [ergebnis, setErgebnis] = useState<Ergebnis | null>(null);
  const [rechnet, setRechnet] = useState(false);

  const projekt = useMemo(
    () => anProjekt(name, schublade, boxen, eigene, nurEigene, ersatzteile, nurErsatz, kabel, nurKabel, gehaeuse, nurGehaeuse),
    [name, schublade, boxen, eigene, nurEigene, ersatzteile, nurErsatz, kabel, nurKabel, gehaeuse, nurGehaeuse],
  );

  useEffect(() => {
    let aktiv = true;
    (async () => {
      for (let versuch = 0; versuch < 5 && aktiv; versuch += 1) {
        if (await gesundheit()) {
          if (aktiv) setDienst(true);
          return;
        }
        await new Promise((warten) => setTimeout(warten, 400));
      }
      if (aktiv) setDienst(false);
    })();
    api<Record<string, unknown>[]>("recent").then((r) => setRecent((r.result as Array<{ pfad: string; name: string }>) || [])).catch(() => undefined);
    api<Record<string, unknown>>("settings_get").then((r) => {
      if (r.result) {
        setEinstellungen(r.result);
        setSchublade((alt) =>
          leereSchublade({
            ...alt,
            spiel_mm: Number(r.result?.schubladenspiel_mm ?? alt.spiel_mm),
            verbinder_spiel_mm: Number(r.result?.verbinder_spiel_mm ?? alt.verbinder_spiel_mm),
            wandstaerke_mm: Number(r.result?.wandstaerke_mm ?? alt.wandstaerke_mm),
            material: String(r.result?.material ?? alt.material),
            nutzhoehe_mm: Number(r.result?.nutzhoehe_mm ?? alt.nutzhoehe_mm),
          }),
        );
      }
    }).catch(() => undefined);
    (async () => {
      for (let versuch = 0; versuch < 5 && aktiv; versuch += 1) {
        try {
          const r = await api<MeineVorlage[]>("vorlagen");
          if (aktiv) setMeineVorlagen((r.result as MeineVorlage[]) || []);
          return;
        } catch {
          await new Promise((warten) => setTimeout(warten, 400));
        }
      }
    })();
    api("detect", { probe: false }).then((r) => setFreecad((r.result as Record<string, unknown>) || null)).catch(() => undefined);
    api<ErsatzArt[]>("ersatz_katalog").then((r) => setErsatzKatalog(r.result || [])).catch(() => undefined);
    api<KabelArt[]>("kabel_katalog").then((r) => setKabelKatalog(r.result || [])).catch(() => undefined);
    api<{ vorlagen: Record<string, Vorlage>; standard: GehaeuseDaten }>("gehaeuse_vorlagen")
      .then((r) => {
        if (!r.result) return;
        setVorlagen(r.result.vorlagen || {});
        setGehaeuse(r.result.standard);
      })
      .catch(() => undefined);
    return () => {
      aktiv = false;
    };
  }, []);

  async function rasterBerechnen(naechsterSchritt = true) {
    setMeldung("");
    const { antwort, aktuell } = await planAbrufen(projekt);
    if (!antwort.ok || !antwort.result) {
      setMeldung(antwort.fehler || "Das Raster konnte nicht berechnet werden.");
      return;
    }
    if (aktuell) setPlan(antwort.result);
    if (naechsterSchritt) setSchritt(2);
  }

  async function boxenAktualisieren(neu: Box[]) {
    setBoxen(neu);
    setErgebnis(null);
    const { antwort, aktuell } = await planAbrufen(anProjekt(name, schublade, neu, eigene, nurEigene));
    if (aktuell && antwort.result) setPlan(antwort.result);
  }

  async function vorlageSpeichern(vorlagenName: string, teil: Eigenteil): Promise<string | null> {
    const antwort = await api<MeineVorlage[]>("vorlage_save", { name: vorlagenName, teil });
    if (!antwort.ok) return antwort.fehler || "Die Vorlage ließ sich nicht speichern.";
    setMeineVorlagen((antwort.result as MeineVorlage[]) || []);
    return null;
  }

  async function vorlageLoeschen(id: string) {
    const antwort = await api<MeineVorlage[]>("vorlage_delete", { id });
    if (antwort.ok) setMeineVorlagen((antwort.result as MeineVorlage[]) || []);
  }

  async function eigeneAktualisieren(neu: Eigenteil[]) {
    setEigene(neu);
    setErgebnis(null);
    const { antwort, aktuell } = await planAbrufen(anProjekt(name, schublade, boxen, neu, nurEigene));
    if (aktuell && antwort.result) setPlan(antwort.result);
  }

  async function automatischFuellen(mitWuenschen = false) {
    setMeldung("");
    const liste = mitWuenschen
      ? Object.entries(wuensche)
          .filter(([, anzahl]) => anzahl > 0)
          .map(([sorte, anzahl]) => ({ sorte, anzahl, seite: wunschZusatz[sorte]?.seite || "egal", gruppe: wunschZusatz[sorte]?.gruppe || "" }))
      : [];
    const antwort = await api<{ neu: number; hinweise?: string[] }>("autofill", {
      projekt,
      max_zellen: 3,
      wuensche: liste,
      rest_fuellen: mitWuenschen ? restFuellen : true,
      stil: fuellstil,
    });
    if (!antwort.ok || !antwort.projekt) {
      setMeldung(antwort.fehler || "Die Schublade ließ sich nicht automatisch füllen.");
      return;
    }
    const roh = antwort.projekt as Record<string, unknown>;
    const neueBoxen = ((roh.boxen as Array<Record<string, unknown>>) || []).map(boxVonServer);
    await boxenAktualisieren(neueBoxen);
    const hinweise = (antwort.result?.hinweise || []).join(" ");
    setMeldung(`${antwort.result?.neu ?? 0} Boxen ergänzt. Vorhandene Boxen blieben unverändert. ${hinweise}`.trim());
  }

  async function speichern() {
    const antwort = await api("save", { path: speicherpfad, projekt });
    if (!antwort.ok) {
      setMeldung(antwort.fehler || "Speichern fehlgeschlagen.");
      return;
    }
    setSpeicherpfad(antwort.pfad || speicherpfad);
    setMeldung(`Gespeichert: ${antwort.pfad}`);
    const liste = await api<Array<{ pfad: string; name: string }>>("recent");
    setRecent(liste.result || []);
  }

  async function oeffnen(pfad: string) {
    const antwort = await api("load", { path: pfad });
    if (!antwort.ok || !antwort.projekt) {
      setMeldung(antwort.fehler || "Projekt ließ sich nicht öffnen.");
      return;
    }
    await uebernehmen(antwort.projekt as Record<string, unknown>, antwort.pfad || pfad);
  }

  async function uebernehmen(roh: Record<string, unknown>, pfad: string) {
    const geladenName = String(roh.name || "Schublade");
    const geladenSchublade = roh.schublade as Schublade;
    const geladenBoxen = ((roh.boxen as Array<Record<string, unknown>>) || []).map(boxVonServer);
    setName(geladenName);
    setSchublade(geladenSchublade);
    setBoxen(geladenBoxen);
    const geladeneEigene = ((roh.eigene as Array<Record<string, unknown>>) || []).map(teilVonServer);
    const geladenNurEigene = Boolean(roh.nur_eigene);
    setEigene(geladeneEigene);
    setNurEigene(geladenNurEigene);
    const geladeneErsatz = ((roh.ersatzteile as Ersatzteil[]) || []).map((e) => ({ ...e, parameter: { ...(e.parameter || {}) } }));
    const geladenNurErsatz = Boolean(roh.nur_ersatz);
    setErsatzteile(geladeneErsatz);
    setNurErsatz(geladenNurErsatz);
    setErsatzAktiv(geladeneErsatz[0]?.id ?? null);
    const geladenesKabel = ((roh.kabel as Kabelteil[]) || []).map((e) => ({ ...e, parameter: { ...(e.parameter || {}) } }));
    const geladenNurKabel = Boolean(roh.nur_kabel);
    setKabel(geladenesKabel);
    setNurKabel(geladenNurKabel);
    setKabelAktiv(geladenesKabel[0]?.id ?? null);
    const geladenesGehaeuse = (roh.gehaeuse as GehaeuseDaten) || { oeffnungen: [] };
    const geladenNurGehaeuse = Boolean(roh.nur_gehaeuse);
    setGehaeuse({ ...geladenesGehaeuse, oeffnungen: geladenesGehaeuse.oeffnungen || [] });
    setNurGehaeuse(geladenNurGehaeuse);
    setSpeicherpfad(pfad);
    setErgebnis(null);
    setSchritt(geladenNurEigene ? 4 : 1);
    setAnsicht(geladenNurGehaeuse ? "gehaeuse" : geladenNurKabel ? "kabel" : geladenNurErsatz ? "ersatz" : "arbeit");
    setMeldung("");
    const { antwort, aktuell } = await planAbrufen(
      anProjekt(
        geladenName,
        geladenSchublade,
        geladenBoxen,
        geladeneEigene,
        geladenNurEigene,
        geladeneErsatz,
        geladenNurErsatz,
        geladenesKabel,
        geladenNurKabel,
        geladenesGehaeuse,
        geladenNurGehaeuse,
      ),
    );
    if (aktuell && antwort.result) setPlan(antwort.result);
  }

  async function dateiOeffnen(file: File) {
    const text = await file.text();
    const roh = JSON.parse(text);
    // Die Dateiauswahl liefert keinen Speicherort. Der alte Pfad würde sonst überschrieben.
    await uebernehmen(roh, "");
    setMeldung("Projekt gelesen. Speichern legt eine neue Datei an.");
  }

  useEffect(() => {
    if (!nurErsatz) return;
    const teil = ersatzteile.find((t) => t.id === ersatzAktiv) ?? ersatzteile[0];
    if (!teil) {
      setErsatzFehler(["Noch kein Ersatzteil ausgewählt."]);
      setErsatzSoll(null);
      return;
    }
    const timer = window.setTimeout(() => {
      api("ersatz_pruefen", { art: teil.art, parameter: parameterZahlen(teil.parameter) }).then((antwort) => {
        const daten = antwort as { ok?: boolean; fehler?: string[]; soll_mm?: number[] | null };
        setErsatzFehler(daten.ok ? [] : daten.fehler || ["Die Maße passen nicht."]);
        setErsatzSoll(daten.soll_mm || null);
      }).catch(() => setErsatzFehler(["Der lokale Dienst antwortet nicht."]));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [nurErsatz, ersatzteile, ersatzAktiv]);

  useEffect(() => {
    if (!nurKabel) return;
    const timer = window.setTimeout(() => {
      api("kabel_system", {
        teile: kabel.map((teil) => ({ ...teil, parameter: parameterZahlen(teil.parameter) })),
        aktiv: kabelAktiv,
      }).then((antwort) => {
        const daten = antwort as { ok?: boolean; fehler?: string[]; soll_mm?: number[] | null; stuecke?: number };
        setKabelFehler(daten.ok ? [] : daten.fehler || ["Die Maße passen nicht."]);
        setKabelSoll(daten.soll_mm || null);
        setKabelStuecke(daten.stuecke || 1);
      }).catch(() => setKabelFehler(["Der lokale Dienst antwortet nicht."]));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [nurKabel, kabel, kabelAktiv]);

  useEffect(() => {
    if (!nurGehaeuse || !gehaeuse.innen_b_mm) return;
    const timer = window.setTimeout(() => {
      api("gehaeuse_pruefen", { parameter: gehaeuseZahlen(gehaeuse) }).then((antwort) => {
        const daten = antwort as { ok?: boolean; fehler?: string[]; soll_mm?: { korpus: number[]; deckel: number[] } | null };
        setGehaeuseFehler(daten.ok ? [] : daten.fehler || ["Die Maße passen nicht."]);
        setGehaeuseSoll(daten.soll_mm || null);
      }).catch(() => setGehaeuseFehler(["Der lokale Dienst antwortet nicht."]));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [nurGehaeuse, gehaeuse]);

  async function erzeugen() {
    if (nurGehaeuse) {
      if (gehaeuseFehler.length) {
        setMeldung("Zuerst die markierten Maße korrigieren.");
        return;
      }
    } else if (nurKabel) {
      if (kabelFehler.length) {
        setMeldung("Zuerst die markierten Maße korrigieren.");
        return;
      }
    } else if (nurErsatz) {
      if (ersatzFehler.length) {
        setMeldung("Zuerst die markierten Maße korrigieren.");
        return;
      }
    } else if (!plan?.ok) {
      setMeldung("Zuerst die markierten Konflikte lösen. Ein Export mit Überlappung gilt nicht als erfolgreich.");
      return;
    }
    setRechnet(true);
    setErgebnis(null);
    setJobText("FreeCAD startet …");
    const antwort = await api("generate", {
      projekt,
      freecad_pfad: String(einstellungen.freecad_pfad || ""),
    });
    if (!antwort.ok || !antwort.job) {
      setRechnet(false);
      setErgebnis({ ok: false, fehler: [antwort.fehler || "Der Auftrag wurde nicht gestartet."] });
      return;
    }
    const job = antwort.job;
    for (;;) {
      await new Promise((r) => setTimeout(r, 800));
      const stand = await jobStatus(job);
      const fort = (stand.fortschritt || {}) as { teil?: string; schritt?: number; gesamt?: number };
      if (fort.teil) setJobText(`Teil ${fort.schritt} von ${fort.gesamt}: ${fort.teil}`);
      if (stand.status === "fertig" || stand.status === "fehler") {
        setErgebnis((stand.ergebnis as Ergebnis) || { ok: false, fehler: ["Keine Rückmeldung."] });
        setRechnet(false);
        return;
      }
    }
  }

  return (
    <div className="app" data-modus={nurGehaeuse ? "gehaeuse" : nurKabel ? "kabel" : nurErsatz ? "ersatz" : nurEigene ? "zeichnen" : "schublade"}>
      <header>
        <button type="button" className="marke" onClick={() => setAnsicht("start")}>
          <img src="/brand/frohnlabs-auf-dunkel.svg" alt="" className="wortmarke" />
          <span className="produkt">CAD Studio</span>
        </button>
        <p>Eigene Ordnung für den 3D-Druck. Maße in Millimeter.</p>
        <button type="button" className="ghost" onClick={() => setAnsicht("einstellungen")}>
          Einstellungen
        </button>
      </header>
      {dienst === false && (
        <div className="alarm" role="alert">
          Der lokale Dienst antwortet nicht. Zum Starten werden Python 3 und der Sidecar gebraucht (Port 47321). FreeCAD 1.1 wird zusätzlich für die Konstruktion gebraucht und nicht mitgeliefert.
        </div>
      )}
      {ansicht === "start" && (
        <Start
          recent={recent}
          onNeu={() => {
            setName("Schublade");
            setSchublade(leereSchublade({
              spiel_mm: Number(einstellungen.schubladenspiel_mm ?? 1),
              verbinder_spiel_mm: Number(einstellungen.verbinder_spiel_mm ?? 0.2),
              wandstaerke_mm: Number(einstellungen.wandstaerke_mm ?? 1.2),
              material: String(einstellungen.material ?? "PLA"),
              nutzhoehe_mm: Number(einstellungen.nutzhoehe_mm ?? 80),
            }));
            setBoxen([]);
            setEigene([]);
            setNurEigene(false);
            setNurErsatz(false);
            setNurKabel(false);
            setNurGehaeuse(false);
            setPlan(null);
            setErgebnis(null);
            setSchritt(1);
            setSpeicherpfad("");
            setAnsicht("arbeit");
          }}
          onOeffnen={oeffnen}
          onBereich={async (id) => {
            if (id === "schublade") {
              setNurEigene(false);
              setNurErsatz(false);
              setNurKabel(false);
            setNurGehaeuse(false);
              setAnsicht("arbeit");
            }
            if (id === "ersatz") {
              let katalog = ersatzKatalog;
              if (!katalog.length) {
                const geladen = await api<ErsatzArt[]>("ersatz_katalog");
                katalog = geladen.result || [];
                setErsatzKatalog(katalog);
              }
              const start = ersatzStart(katalog);
              setName("Ersatzteil");
              setBoxen([]);
              setEigene([]);
              setNurEigene(false);
              setNurErsatz(true);
              setNurKabel(false);
            setNurGehaeuse(false);
              setErsatzteile(start);
              setErsatzAktiv(start[0]?.id ?? null);
              setErgebnis(null);
              setSpeicherpfad("");
              setAnsicht("ersatz");
            }
            if (id === "zeichnen") {
              const start = [neuesTeil([])];
              setName("Eigene Teile");
              setBoxen([]);
              setEigene(start);
              setNurEigene(true);
              setNurErsatz(false);
              setNurKabel(false);
            setNurGehaeuse(false);
              setErgebnis(null);
              setSpeicherpfad("");
              setSchritt(4);
              setAnsicht("arbeit");
              const { antwort, aktuell } = await planAbrufen(anProjekt("Eigene Teile", schublade, [], start, true));
              if (aktuell && antwort.result) setPlan(antwort.result);
            }
            if (id === "kabel") {
              let katalog = kabelKatalog;
              if (!katalog.length) {
                const geladen = await api<KabelArt[]>("kabel_katalog");
                katalog = geladen.result || [];
                setKabelKatalog(katalog);
              }
              const start = kabelStart(katalog);
              setName("Kabelmanagement");
              setBoxen([]);
              setEigene([]);
              setNurEigene(false);
              setNurErsatz(false);
              setNurKabel(true);
              setNurGehaeuse(false);
              setKabel(start);
              setKabelAktiv(start[0]?.id ?? null);
              setErgebnis(null);
              setSpeicherpfad("");
              setAnsicht("kabel");
            }
            if (id === "gehaeuse") {
              setName("Elektronikgehäuse");
              setBoxen([]);
              setEigene([]);
              setNurEigene(false);
              setNurErsatz(false);
              setNurKabel(false);
              setNurGehaeuse(true);
              setErgebnis(null);
              setSpeicherpfad("");
              setAnsicht("gehaeuse");
            }
          }}
        />
      )}
      {ansicht === "ersatz" && (
        <>
        <ErsatzteilAnsicht
          katalog={ersatzKatalog}
          teile={ersatzteile}
          aktivId={ersatzAktiv}
          fehler={ersatzFehler}
          soll={ersatzSoll}
          onWaehlen={setErsatzAktiv}
          onNeu={(art) => {
            const neu = neuesErsatzteil(ersatzKatalog, art, ersatzteile);
            if (!neu) return;
            setErsatzteile((alt) => [...alt, neu]);
            setErsatzAktiv(neu.id);
            setErgebnis(null);
          }}
          onParameter={(id, key, wert) => {
            setErsatzteile((alt) => alt.map((teil) => (teil.id === id ? { ...teil, parameter: { ...teil.parameter, [key]: wert } } : teil)));
            setErgebnis(null);
          }}
          onErzeugen={erzeugen}
          ergebnis={ergebnis}
          rechnet={rechnet}
          jobText={jobText}
          speicherpfad={speicherpfad}
          onSpeicherpfad={setSpeicherpfad}
          onSpeichern={speichern}
        />
        <div className="ansicht3d-rahmen"><Ansicht3D projekt={projekt} modus="ersatz" freecadPfad={String(einstellungen.freecad_pfad || "")} titel="3D-Ansicht des Ersatzteils" /></div>
        </>
      )}
      {ansicht === "kabel" && (
        <>
        <KabelAnsicht
          katalog={kabelKatalog}
          teile={kabel}
          aktivId={kabelAktiv}
          fehler={kabelFehler}
          soll={kabelSoll}
          stuecke={kabelStuecke}
          onWaehlen={setKabelAktiv}
          onNeu={(art) => {
            const neu = neuesKabelteil(kabelKatalog, art, kabel, kabelAktiv);
            if (!neu) return;
            setKabel((alt) => [...alt, neu]);
            setKabelAktiv(neu.id);
            setErgebnis(null);
          }}
          onEntfernen={(id) => {
            setKabel((alt) => alt.filter((teil) => teil.id !== id));
            setKabelAktiv((bisher) => (bisher === id ? null : bisher));
            setErgebnis(null);
          }}
          onParameter={(id, key, wert) => {
            setKabel((alt) => alt.map((teil) => (teil.id === id ? { ...teil, parameter: { ...teil.parameter, [key]: wert } } : teil)));
            setErgebnis(null);
          }}
          onAngleichen={() => {
            if (!kabelAktiv) return;
            setKabel((alt) => profilKopieren(alt, kabelAktiv));
            setErgebnis(null);
          }}
          onErzeugen={erzeugen}
          ergebnis={ergebnis}
          rechnet={rechnet}
          jobText={jobText}
          speicherpfad={speicherpfad}
          onSpeicherpfad={setSpeicherpfad}
          onSpeichern={speichern}
        />
        <div className="ansicht3d-rahmen"><Ansicht3D projekt={projekt} modus="kabel" freecadPfad={String(einstellungen.freecad_pfad || "")} titel="3D-Ansicht des Kabelteils" /></div>
        </>
      )}
      {ansicht === "gehaeuse" && (
        <>
        <GehaeuseAnsicht
          daten={gehaeuse}
          vorlagen={vorlagen}
          fehler={gehaeuseFehler}
          soll={gehaeuseSoll}
          onAendern={(key, wert) => {
            setGehaeuse((alt) => ({ ...alt, [key]: wert }));
            setErgebnis(null);
          }}
          onOeffnung={(index, key, wert) => {
            setGehaeuse((alt) => ({
              ...alt,
              oeffnungen: alt.oeffnungen.map((oeffnung, i) => (i === index ? { ...oeffnung, [key]: wert } : oeffnung)),
            }));
            setErgebnis(null);
          }}
          onOeffnungNeu={() => {
            setGehaeuse((alt) => ({
              ...alt,
              oeffnungen: [...alt.oeffnungen, { seite: "vorne", form: "rechteck", pos_mm: 40, unten_mm: 14, breite_mm: 12, hoehe_mm: 6 }],
            }));
            setErgebnis(null);
          }}
          onOeffnungWeg={(index) => {
            setGehaeuse((alt) => ({ ...alt, oeffnungen: alt.oeffnungen.filter((_, i) => i !== index) }));
            setErgebnis(null);
          }}
          onErzeugen={erzeugen}
          ergebnis={ergebnis}
          rechnet={rechnet}
          jobText={jobText}
          speicherpfad={speicherpfad}
          onSpeicherpfad={setSpeicherpfad}
          onSpeichern={speichern}
        />
        <div className="ansicht3d-rahmen"><Ansicht3D projekt={projekt} modus="gehaeuse" freecadPfad={String(einstellungen.freecad_pfad || "")} titel="3D-Ansicht von Gehäuse und Deckel" /></div>
        </>
      )}
      {ansicht === "einstellungen" && (
        <Einstellungen
          werte={einstellungen}
          freecad={freecad}
          onChange={setEinstellungen}
          onSave={async () => {
            const antwort = await api("settings_set", { settings: einstellungen });
            if (antwort.result) setEinstellungen(antwort.result as Record<string, unknown>);
            setMeldung("Einstellungen gespeichert.");
          }}
          onPruefen={async () => {
            const antwort = await api("detect", { user_path: einstellungen.freecad_pfad || "", probe: true });
            setFreecad((antwort.result as Record<string, unknown>) || null);
          }}
        />
      )}
      {ansicht === "arbeit" && (
        <main>
          <ol className="schritte">
            {["Vermessen", "Raster", "Boxen", "Eigene Teile", "Drucken"]
              .map((titel, index) => ({ titel, nr: index + 1 }))
              .filter((eintrag) => !nurEigene || eintrag.nr >= 4)
              .map(({ titel, nr }) => (
                <li key={titel} className={schritt === nr ? "aktiv" : ""}>
                  <button type="button" onClick={() => setSchritt(nr)}>
                    {nr}. {titel}
                  </button>
                </li>
              ))}
          </ol>
          {schritt === 1 && (
            <section>
              <h1>Schublade vermessen</h1>
              <p className="leise">Innenmaß der Schublade, dort wo die Platten stehen sollen. Nicht das Außenmaß des Möbels.</p>
              <div className="formular">
                <Feld label="Name" wert={name} onChange={setName} testid="name" />
                <Zahl label="Innenbreite" wert={schublade.innenbreite_mm} onChange={(v) => setSchublade({ ...schublade, innenbreite_mm: v })} testid="breite" />
                <Zahl label="Innentiefe" wert={schublade.innentiefe_mm} onChange={(v) => setSchublade({ ...schublade, innentiefe_mm: v })} testid="tiefe" />
                <Zahl label="Nutzbare Höhe" wert={schublade.nutzhoehe_mm} onChange={(v) => setSchublade({ ...schublade, nutzhoehe_mm: v })} testid="hoehe-schublade" />
                <Zahl label="Spiel zur Wand, je Seite" wert={schublade.spiel_mm} onChange={(v) => setSchublade({ ...schublade, spiel_mm: v })} testid="spiel" />
                <Zahl label="Verbinder-Spiel" wert={schublade.verbinder_spiel_mm} onChange={(v) => setSchublade({ ...schublade, verbinder_spiel_mm: v })} testid="verbinder" />
                <Zahl label="Extra-Rand links" wert={schublade.rand_links_mm} onChange={(v) => setSchublade({ ...schublade, rand_links_mm: v })} />
                <Zahl label="Extra-Rand rechts" wert={schublade.rand_rechts_mm} onChange={(v) => setSchublade({ ...schublade, rand_rechts_mm: v })} />
                <Zahl label="Extra-Rand vorn" wert={schublade.rand_vorne_mm} onChange={(v) => setSchublade({ ...schublade, rand_vorne_mm: v })} />
                <Zahl label="Extra-Rand hinten" wert={schublade.rand_hinten_mm} onChange={(v) => setSchublade({ ...schublade, rand_hinten_mm: v })} />
              </div>
              <p className="hinweis">
                Spiel zur Wand ({schublade.spiel_mm} mm) und Verbinder-Spiel ({schublade.verbinder_spiel_mm} mm) sind ungeprüfte Vorgaben. Am Drucker können sie zu straff oder zu lose sein.
              </p>
              <button type="button" className="primaer" data-testid="raster-berechnen" onClick={() => rasterBerechnen(true)}>
                Raster erzeugen
              </button>
            </section>
          )}
          {schritt === 2 && plan && (
            <section>
              <h1>Raster</h1>
              <p>
                {plan.einheiten_x} × {plan.einheiten_y} Felder à 42 mm. Nutzfläche {plan.nutz_x} × {plan.nutz_y} mm.
                Rest {plan.rest_x} mm in der Breite und {plan.rest_y} mm in der Tiefe, in die Außenplatten eingearbeitet, soweit der Bauraum das hergibt.
              </p>
              <ul className="plattenliste">
                {plan.platten.map((platte) => (
                  <li key={platte.id}>
                    <strong>{platte.id}</strong> {platte.einheiten_x}×{platte.einheiten_y}, {platte.breite_mm} × {platte.tiefe_mm} mm
                    {platte.passt_in_bauraum ? " · passt aufs Druckbett" : " · passt nicht aufs Druckbett"}
                  </li>
                ))}
              </ul>
              {plan.randstreifen.length > 0 && <div className="alarm">{plan.randstreifen_hinweis}</div>}
              {!plan.ok && (
                <div className="alarm" role="alert">
                  {plan.fehler.map((f) => (
                    <p key={f}>{f}</p>
                  ))}
                </div>
              )}
              <button type="button" className="primaer" onClick={() => setSchritt(3)} disabled={!plan.platten.length}>
                Boxen platzieren
              </button>
            </section>
          )}
          {schritt === 3 && plan && (
            <section>
              <h1>Boxen stellen</h1>
              <Editor breite={schublade.innenbreite_mm} tiefe={schublade.innentiefe_mm} plan={plan} boxen={boxen} onChange={boxenAktualisieren} />
              <details className="wunschliste" data-testid="wunschliste">
                <summary>Wunschliste: Was brauchst du?</summary>
                <p className="leise">Das Tool setzt die gewünschten Boxen zuerst an freie Stellen (größte zuerst, bei Bedarf gedreht) und füllt danach optional den Rest. Mit „Seite“ drängt es eine Sorte nach links, rechts, vorne oder hinten, Boxen derselben „Gruppe“ liegen beieinander. Es probiert mehrere Anordnungen und füllt den Rest mit möglichst wenigen Boxen. Vorhandene Boxen und platzierte eigene Teile bleiben unberührt.</p>
                <div className="formular">
                  {KATALOG.map((eintrag) => (
                    <div key={eintrag.id} className="wunschzeile">
                      <label>
                        {eintrag.name} <small>({eintrag.text})</small>
                        <input
                          data-testid={`wunsch-${eintrag.id}`}
                          inputMode="numeric"
                          value={String(wuensche[eintrag.id] ?? 0)}
                          onChange={(e) => {
                            const zahl = Math.max(0, Math.min(200, Math.round(Number(e.target.value) || 0)));
                            setWuensche({ ...wuensche, [eintrag.id]: zahl });
                          }}
                        />
                      </label>
                      {(wuensche[eintrag.id] ?? 0) > 0 && (
                        <div className="wunsch-zusatz" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <label>
                            Seite
                            <select
                              data-testid={`wunsch-seite-${eintrag.id}`}
                              value={wunschZusatz[eintrag.id]?.seite || "egal"}
                              onChange={(e) => setWunschZusatz({ ...wunschZusatz, [eintrag.id]: { seite: e.target.value, gruppe: wunschZusatz[eintrag.id]?.gruppe || "" } })}
                            >
                              <option value="egal">egal</option>
                              <option value="links">links</option>
                              <option value="rechts">rechts</option>
                              <option value="vorne">vorne</option>
                              <option value="hinten">hinten</option>
                            </select>
                          </label>
                          <label>
                            Gruppe
                            <select
                              data-testid={`wunsch-gruppe-${eintrag.id}`}
                              value={wunschZusatz[eintrag.id]?.gruppe || ""}
                              onChange={(e) => setWunschZusatz({ ...wunschZusatz, [eintrag.id]: { seite: wunschZusatz[eintrag.id]?.seite || "egal", gruppe: e.target.value } })}
                            >
                              <option value="">keine</option>
                              <option value="A">A</option>
                              <option value="B">B</option>
                              <option value="C">C</option>
                            </select>
                          </label>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <label className="check">
                  <input type="checkbox" data-testid="wunsch-rest" checked={restFuellen} onChange={(e) => setRestFuellen(e.target.checked)} />
                  Übrige freie Felder danach automatisch füllen
                </label>
                <button type="button" className="primaer" data-testid="wuensche-platzieren" onClick={() => automatischFuellen(true)}>
                  Wünsche platzieren
                </button>
              </details>
              <Vorschau
                breite={schublade.innenbreite_mm}
                tiefe={schublade.innentiefe_mm}
                boxen={boxen}
                ursprungX={plan.ursprung_x_mm}
                ursprungY={plan.ursprung_y_mm}
                plattenhoehe={plan.plattenhoehe_mm}
                dateien={null}
              />
              <div className="knopfzeile">
                <label className="stil">
                  Füllstil
                  <select data-testid="fuellstil" value={fuellstil} onChange={(e) => setFuellstil(e.target.value)}>
                    <option value="einheitlich">Einheitliche Größe</option>
                    <option value="gross">Möglichst große Boxen</option>
                    <option value="klein">Kleine Boxen (1 × 1)</option>
                  </select>
                </label>
                <button type="button" data-testid="auto-fuellen" onClick={() => automatischFuellen(false)}>
                  Freie Felder automatisch füllen
                </button>
                <button type="button" onClick={() => setSchritt(4)}>
                  Eigene Teile zeichnen
                </button>
                <button type="button" className="primaer" data-testid="weiter-druck" onClick={() => setSchritt(5)}>
                  Weiter zur Konstruktion
                </button>
              </div>
            </section>
          )}
          {schritt === 4 && (
            <section>
              <h1>Eigene Teile zeichnen</h1>
              <p className="leise">Formen zeichnen, Höhe festlegen, als STL und FCStd ausgeben. Löcher schneiden Material weg.</p>
              <Zeichnen
                teile={eigene}
                onChange={eigeneAktualisieren}
                meineVorlagen={meineVorlagen}
                onVorlageSpeichern={vorlageSpeichern}
                onVorlageLoeschen={vorlageLoeschen}
                freecadPfad={String(einstellungen.freecad_pfad || "")}
                fehler={plan && !plan.ok ? plan.fehler : []}
                lageplan={
                  nurEigene || !plan
                    ? null
                    : {
                        breite: schublade.innenbreite_mm,
                        tiefe: schublade.innentiefe_mm,
                        platten: plan.platten.map((p) => p.lage),
                        boxen: plan.boxen_mm || [],
                      }
                }
              />
              <button type="button" className="primaer" onClick={() => setSchritt(5)}>
                Weiter zur Konstruktion
              </button>
            </section>
          )}
          {schritt === 5 && (
            <section>
              <h1>Konstruktion und Export</h1>
              <p className="leise">STL und FCStd entstehen erst hier, mit FreeCAD 1.1 und dem Hausraster-Generator 0.2-qs1. Ohne bestandene Mesh-Prüfung gibt es keine Erfolgsmeldung.</p>
              {plan && !plan.ok && (
                <div className="alarm" role="alert" data-testid="export-gesperrt">
                  {plan.fehler.map((f) => (
                    <p key={f}>{f}</p>
                  ))}
                </div>
              )}
              <button type="button" className="primaer" data-testid="erzeugen" disabled={!plan?.ok || rechnet} onClick={erzeugen}>
                {rechnet ? "Berechnet …" : "Alle Teile berechnen"}
              </button>
              {jobText && rechnet && <p data-testid="fortschritt">{jobText}</p>}
              {ergebnis && <ErgebnisAnsicht ergebnis={ergebnis} schublade={schublade} boxen={boxen} plan={nurEigene ? null : plan} />}
              <div className="speichern">
                <label>
                  Projektdatei
                  <input data-testid="speicherpfad" value={speicherpfad} onChange={(e) => setSpeicherpfad(e.target.value)} placeholder="schublade.cadstudio.json" />
                </label>
                <button type="button" data-testid="speichern" onClick={speichern}>
                  Speichern
                </button>
                <label className="datei">
                  Öffnen
                  <input
                    data-testid="oeffnen"
                    type="file"
                    accept="application/json,.json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) dateiOeffnen(file);
                    }}
                  />
                </label>
              </div>
            </section>
          )}
          {meldung && <p className="meldung" data-testid="meldung">{meldung}</p>}
        </main>
      )}
    </div>
  );
}

function Start({
  recent,
  onNeu,
  onOeffnen,
  onBereich,
}: {
  recent: Array<{ pfad: string; name: string }>;
  onNeu: () => void;
  onOeffnen: (pfad: string) => void;
  onBereich: (id: string) => void;
}) {
  return (
    <main>
      <h1>Was möchtest du bauen?</h1>
      <div className="kacheln">
        {BEREICHE.map((bereich) => (
          <button key={bereich.id} type="button" className={bereich.bereit ? "kachel" : "kachel vorbereitung"} disabled={!bereich.bereit} onClick={() => onBereich(bereich.id)}>
            <strong>{bereich.titel}</strong>
            <span>{bereich.text}</span>
            {!bereich.bereit && <em>in Vorbereitung</em>}
          </button>
        ))}
      </div>
      <button type="button" className="primaer" data-testid="neue-schublade" onClick={onNeu}>
        Neue Schublade
      </button>
      <h2>Zuletzt geöffnet</h2>
      {recent.length === 0 && <p className="leise">Noch keine Projekte auf diesem Rechner.</p>}
      <ul className="recent">
        {recent.map((eintrag) => (
          <li key={eintrag.pfad}>
            <button type="button" onClick={() => onOeffnen(eintrag.pfad)}>
              {eintrag.name}
              <small>{eintrag.pfad}</small>
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}

function Einstellungen({
  werte,
  freecad,
  onChange,
  onSave,
  onPruefen,
}: {
  werte: Record<string, unknown>;
  freecad: Record<string, unknown> | null;
  onChange: (werte: Record<string, unknown>) => void;
  onSave: () => void;
  onPruefen: () => void;
}) {
  function set(key: string, value: unknown) {
    onChange({ ...werte, [key]: value });
  }
  const hinweis = String(freecad?.hinweis || "");
  return (
    <main>
      <h1>Einstellungen</h1>
      <div className="formular">
        <label>
          Pfad zu FreeCADCmd
          <input value={String(werte.freecad_pfad || "")} onChange={(e) => set("freecad_pfad", e.target.value)} placeholder="C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" />
        </label>
        <label>
          Material
          <select value={String(werte.material || "PLA")} onChange={(e) => set("material", e.target.value)}>
            <option>PLA</option>
            <option>PETG</option>
            <option>ABS</option>
          </select>
        </label>
        <label>
          Standard-Spiel zur Wand (mm)
          <input value={String(werte.schubladenspiel_mm ?? 1)} onChange={(e) => set("schubladenspiel_mm", Number(e.target.value.replace(",", ".")))} />
        </label>
        <label>
          Standard-Verbinder-Spiel (mm)
          <input value={String(werte.verbinder_spiel_mm ?? 0.2)} onChange={(e) => set("verbinder_spiel_mm", Number(e.target.value.replace(",", ".")))} />
        </label>
        <label>
          Wandstärke (mm)
          <input value={String(werte.wandstaerke_mm ?? 1.2)} onChange={(e) => set("wandstaerke_mm", Number(e.target.value.replace(",", ".")))} />
        </label>
        <label>
          Nutzbare Höhe, Vorschlag (mm)
          <input value={String(werte.nutzhoehe_mm ?? 80)} onChange={(e) => set("nutzhoehe_mm", Number(e.target.value.replace(",", ".")))} />
        </label>
      </div>
      <p className="hinweis">Bauraum des Bambu Lab P2S: 256 × 256 × 256 mm. FreeCAD 1.1 wird getrennt installiert und nicht mitgeliefert (LGPL).</p>
      <div className="knopfzeile">
        <button type="button" onClick={onPruefen}>
          FreeCAD suchen
        </button>
        <button type="button" className="primaer" onClick={onSave}>
          Speichern
        </button>
      </div>
      {hinweis && <p className={freecad?.geeignet ? "meldung" : "alarm"}>{hinweis}</p>}
    </main>
  );
}

function ErgebnisAnsicht({
  ergebnis,
  schublade,
  boxen,
  plan,
}: {
  ergebnis: Ergebnis;
  schublade: Schublade;
  boxen: Box[];
  plan: Plan | null;
}) {
  if (!ergebnis.ok) {
    return (
      <div className="alarm" role="alert" data-testid="export-fehler">
        <strong>Nicht exportiert.</strong>
        {(ergebnis.fehler || ["Die Prüfung ist fehlgeschlagen."]).map((f) => (
          <p key={f}>{f}</p>
        ))}
      </div>
    );
  }
  const dateien = (ergebnis.teile || []).flatMap((teil) =>
    (teil.dateien || []).map((d) => ({ ...d, platz: d.platz })),
  );
  return (
    <div data-testid="export-erfolg">
      <p className="erfolg">Alle Teile sind erzeugt. Dateien sind vorhanden, die Netze sind geschlossen und die FCStd-Dateien enthalten einen gültigen Körper.</p>
      {plan && (
        <Vorschau
          breite={schublade.innenbreite_mm}
          tiefe={schublade.innentiefe_mm}
          boxen={boxen}
          ursprungX={plan.ursprung_x_mm}
          ursprungY={plan.ursprung_y_mm}
          plattenhoehe={plan.plattenhoehe_mm}
          dateien={dateien as never}
        />
      )}
      <ul className="dateien">
        {ergebnis.stueckliste && (
          <li>
            <a href={dateiUrl(ergebnis.stueckliste)}>Stückliste</a>
          </li>
        )}
        {ergebnis.montage?.html && (
          <li>
            <a href={dateiUrl(ergebnis.montage.html)}>Montageübersicht (HTML)</a>
          </li>
        )}
        {ergebnis.montage?.pdf && (
          <li>
            <a href={dateiUrl(ergebnis.montage.pdf)}>Montageübersicht (PDF)</a>
          </li>
        )}
        {ergebnis.montage?.png && (
          <li>
            <a href={dateiUrl(ergebnis.montage.png)}>Montageübersicht (PNG)</a>
          </li>
        )}
        {dateien.map((d) => (
          <li key={d.id}>
            {d.id}
            {d.stl && (
              <>
                {" "}
                <a href={dateiUrl(d.stl)}>STL</a>
              </>
            )}
            {d.fcstd && (
              <>
                {" "}
                <a href={dateiUrl(d.fcstd)}>FCStd</a>
              </>
            )}
          </li>
        ))}
      </ul>
      {(ergebnis.hinweise || []).map((h) => (
        <p key={h} className="leise">
          {h}
        </p>
      ))}
    </div>
  );
}

function Feld({ label, wert, onChange, testid }: { label: string; wert: string; onChange: (v: string) => void; testid?: string }) {
  return (
    <label>
      {label}
      <input data-testid={testid} value={wert} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function Zahl({ label, wert, onChange, testid }: { label: string; wert: number; onChange: (v: number) => void; testid?: string }) {
  return (
    <label>
      {label}
      <input
        data-testid={testid}
        inputMode="decimal"
        value={String(wert)}
        onChange={(e) => onChange(Number(e.target.value.replace(",", ".")))}
      />
      <span>mm</span>
    </label>
  );
}

function anProjekt(
  name: string,
  schublade: Schublade,
  boxen: Box[],
  eigene: Eigenteil[] = [],
  nurEigene = false,
  ersatzteile: Ersatzteil[] = [],
  nurErsatz = false,
  kabel: Kabelteil[] = [],
  nurKabel = false,
  gehaeuse: GehaeuseDaten = { oeffnungen: [] },
  nurGehaeuse = false,
) {
  return {
    format: "cadstudio.projekt",
    version: 1,
    name,
    schublade,
    notiz: "",
    eigene,
    nur_eigene: nurEigene,
    ersatzteile,
    nur_ersatz: nurErsatz,
    kabel,
    nur_kabel: nurKabel,
    gehaeuse,
    nur_gehaeuse: nurGehaeuse,
    boxen: boxen.map((box) => ({
      id: box.id,
      name: box.name,
      x: box.x,
      y: box.y,
      ex: box.ex,
      ey: box.ey,
      ez: box.ez,
      rotation: box.rotation,
      fach_x: box.fachX,
      fach_y: box.fachY,
      stapellippe: box.stapellippe,
      deckel: box.deckel,
      herausnehmbar: box.herausnehmbar,
      kabelkerben: box.kabelkerben,
      art: box.art,
    })),
  };
}

function parameterZahlen(parameter: Record<string, string | number>) {
  const aus: Record<string, string | number> = {};
  for (const [key, wert] of Object.entries(parameter)) {
    if (typeof wert === "string" && /^-?\d+(\.\d+)?$/.test(wert)) aus[key] = Number(wert);
    else aus[key] = wert;
  }
  return aus;
}

function neuesErsatzteil(katalog: ErsatzArt[], art: string, vorhanden: Ersatzteil[]): Ersatzteil | null {
  const vorlage = katalog.find((e) => e.id === art);
  if (!vorlage) return null;
  const nummern = vorhanden.map((t) => Number(/^ET(\d+)$/.exec(t.id)?.[1] || 0));
  const id = `ET${Math.max(0, ...nummern) + 1}`;
  return { id, art, name: `${vorlage.name} ${id}`, parameter: { ...vorlage.standard } };
}

function neuesKabelteil(katalog: KabelArt[], art: string, vorhanden: Kabelteil[], vonId?: string | null): Kabelteil | null {
  const vorlage = katalog.find((e) => e.id === art);
  if (!vorlage) return null;
  const nummern = vorhanden.map((t) => Number(/^K(\d+)$/.exec(t.id)?.[1] || 0));
  const id = `K${Math.max(0, ...nummern) + 1}`;
  const quelle = (vorhanden.find((t) => t.id === vonId) ?? vorhanden[0])?.parameter;
  const parameter = { ...vorlage.standard };
  if (quelle) {
    for (const key of ["innenbreite_mm", "innenhoehe_mm", "wand_mm", "spiel_mm", "zapfen_mm"]) {
      if (quelle[key] !== undefined) parameter[key] = quelle[key];
    }
  }
  return { id, art, name: `${vorlage.name} ${id}`, parameter };
}

function kabelStart(katalog: KabelArt[]): Kabelteil[] {
  const kanal = katalog.find((e) => e.id === "kanal") ?? katalog[0];
  if (!kanal) return [];
  return [{ id: "K1", art: kanal.id, name: kanal.name, parameter: { ...kanal.standard } }];
}

function ersatzStart(katalog: ErsatzArt[]): Ersatzteil[] {
  const clip = katalog.find((e) => e.id === "kabelclip") ?? katalog[0];
  if (!clip) return [];
  return [{ id: "ET1", art: clip.id, name: clip.name, parameter: { ...clip.standard } }];
}

function boxVonServer(roh: Record<string, unknown>): Box {
  return {
    id: String(roh.id),
    name: String(roh.name || roh.id),
    x: Number(roh.x),
    y: Number(roh.y),
    ex: Number(roh.ex),
    ey: Number(roh.ey),
    ez: Number(roh.ez),
    rotation: Number(roh.rotation || 0),
    fachX: Number(roh.fach_x ?? 1),
    fachY: Number(roh.fach_y ?? 1),
    stapellippe: Boolean(roh.stapellippe),
    deckel: Boolean(roh.deckel),
    herausnehmbar: Boolean(roh.herausnehmbar),
    kabelkerben: Boolean(roh.kabelkerben),
    art: (roh.art as Box["art"]) || "raster",
  };
}
