/** Kurze Fehlermeldung im Arbeitsfluss, vollständige Diagnose auf Wunsch. */
export function ExportFehler({ fehler }: { fehler?: string[] }) {
  const texte = fehler?.length ? fehler : ["Die Prüfung ist fehlgeschlagen."];
  return <div className="alarm" role="alert" data-testid="export-fehler">
    <strong>Nicht exportiert.</strong>
    <p>{texte[0].split("\n")[0]}</p>
    <details><summary>Technische Details</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{texte.join("\n\n")}</pre></details>
  </div>;
}
