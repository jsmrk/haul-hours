import { useState } from "react";
import { Download, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { PlanResult } from "./contracts.generated";
import { downloadLogs } from "./api";

function printLogs(date?: string) {
  const style = document.createElement("style");
  if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) style.textContent = `@media print { .print-sheet:not([data-log-date="${date}"]) { display: none !important; } }`;
  document.head.append(style);
  window.print();
  style.remove();
}

export function ExportControls({ result, date }: { result: PlanResult; date: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function exportLogs(selectedDate?: string) {
    if (busy) return;
    setBusy(true); setError("");
    try { await downloadLogs(result, result.request.metadata ?? {}, selectedDate); }
    catch (problem) { setError(problem instanceof Error ? problem.message : "The PDF could not be downloaded. Try again."); }
    finally { setBusy(false); }
  }
  return <div className="space-y-3"><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={busy} onClick={() => void exportLogs(date)}>{busy ? <Spinner/> : <Download className="size-4"/>}Download this day</Button><Button size="sm" disabled={busy} onClick={() => void exportLogs()}>Download all days</Button><Button variant="secondary" size="sm" onClick={() => printLogs(date)}><Printer className="size-4"/>Print this day</Button><Button variant="ghost" size="sm" onClick={() => printLogs()}>Print all days</Button></div>{error && <p role="alert" className="text-sm">{error}</p>}</div>;
}
