import { Badge } from "@/components/ui/badge";
import type { DailyLog, LogMetadata } from "./contracts.generated";
import { logDuration, miles, moment } from "./format";

interface Props { log: DailyLog; metadata: LogMetadata; selectedEventId?: string | null; onSelectEvent?: (id: string) => void }
export function DailyLogSheet({ log, metadata, selectedEventId = null, onSelectEvent }: Props) {
  const left = 132, top = 65, width = 752, rowHeight = 37;
  return <article className="log-sheet bg-white" aria-label={`Daily log ${log.date}`}>
    <div className="mb-5 flex items-start justify-between gap-5"><div><h3 className="text-[22px] font-semibold">Projected driver daily log</h3><p className="mt-2 text-sm text-muted-foreground">{log.date} · {log.timezone} · {logDuration(log.duration_s)} elapsed</p></div><Badge variant="neutral">Projected</Badge></div>
    <dl className="log-metadata mb-6 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">{[["Driver", metadata.driver_name], ["Carrier", metadata.carrier_name], ["Carrier address", metadata.carrier_address], ["Truck / trailer", `${metadata.truck_number || "Not provided"} / ${metadata.trailer_number || "Not provided"}`], ["Shipment", metadata.shipment_reference], ["Starting odometer", metadata.starting_odometer_miles ? `${metadata.starting_odometer_miles} mi` : null]].map(([label, value]) => <div key={label} className="min-w-0"><dt className="font-medium">{label}</dt><dd className="mt-1 break-words text-muted-foreground">{value || "Not provided"}</dd></div>)}</dl>
    <div className="log-graph-scroll overflow-x-auto rounded-[8px] border" role="region" aria-label={`Scrollable duty graph for ${log.date}`} tabIndex={0}>
      <svg viewBox="0 0 1040 255" className="log-graph block min-w-[1000px] w-full" role="img" aria-label={`Duty graph for ${log.date}, ${log.duration_s / 3600} elapsed hours`}>
        {Array.from({ length: Math.floor(log.duration_s / 900) + 1 }, (_, index) => { const x = left + index * 900 / log.duration_s * width; return <line key={index} x1={x} x2={x} y1={top} y2={top + 4 * rowHeight} stroke="#dedee5" strokeWidth={index % 4 === 0 ? 1 : .5}/>; })}
        {Array.from({ length: 5 }, (_, row) => <line key={row} x1={left} x2={left + width} y1={top + row * rowHeight} y2={top + row * rowHeight} stroke="#686b82" strokeWidth=".7"/>)}
        {log.graph.ticks.map((tick) => <g key={tick.elapsed_s}><text x={left + tick.elapsed_s / log.duration_s * width} y={top - 13} textAnchor="middle" fontSize="12" fill="#101114">{tick.label.slice(0, 2)}</text>{log.duration_s !== 86400 && <text x={left + tick.elapsed_s / log.duration_s * width} y={top - 31} textAnchor="middle" fontSize="10" fill="#686b82">{tick.label.split("UTC")[1]}</text>}</g>)}
        <text x="932" y={top - 13} textAnchor="middle" fontSize="12" fontWeight="600">TOTAL</text>
        {[{ key: "OFF", label: "Off duty" }, { key: "SB", label: "Sleeper berth" }, { key: "D", label: "Driving" }, { key: "ON", label: "On duty" }].map(({ key, label }, row) => <g key={key}><text x="12" y={top + (row + .5) * rowHeight + 5} fontSize="14" fontWeight="500">{label}</text><text x="932" y={top + (row + .5) * rowHeight + 5} textAnchor="middle" fontSize="14">{logDuration(log.totals_s[key] ?? 0)}</text></g>)}
        {log.graph.paths.map((path, index) => { const status = log.intervals[index]?.status ?? "OFF"; return <polyline key={index} data-event-id={path.event_id ?? undefined} className="duty-trace" points={path.points.map(([x, row]) => `${left + x * width},${top + (row + .5) * rowHeight}`).join(" ")} fill="none" stroke={path.event_id && path.event_id === selectedEventId ? "#7132f5" : "#101114"} strokeWidth={path.event_id && path.event_id === selectedEventId ? 4 : 2.5} role={path.event_id ? "button" : undefined} aria-label={path.event_id ? `Select ${status} event ${path.event_id}` : undefined} aria-pressed={path.event_id ? path.event_id === selectedEventId : undefined} tabIndex={path.event_id && onSelectEvent ? 0 : undefined} onClick={() => { if (path.event_id) onSelectEvent?.(path.event_id); }} onKeyDown={(event) => { if (path.event_id && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); onSelectEvent?.(path.event_id); } }}/>; })}
      </svg>
    </div>
    <p className="mt-2 text-xs text-muted-foreground no-print">Scroll horizontally to see the full graph and status totals.</p>
    {log.duration_s !== 86400 && <p className="mt-2 text-sm text-muted-foreground">This daylight-saving transition day has {log.duration_s / 3600} elapsed hours. Repeated or skipped local hours are labeled with UTC offsets.</p>}
    <p className="my-5 text-sm font-semibold">Planned miles: {miles(log.distance_m, 2)}</p>
    <h4 className="mb-3 text-sm font-semibold">Remarks & locations</h4>
    <div className="space-y-3">{log.remarks.map((remark, index) => <div key={index} className="grid gap-1 border-b pb-3 text-sm sm:grid-cols-[100px_1fr]"><time dateTime={remark.at} className="text-muted-foreground">{moment(remark.at, log.timezone)}</time><div><p className="break-words font-medium">{remark.location_label}</p><p className="mt-1 break-words leading-relaxed text-muted-foreground">{remark.note}</p></div></div>)}</div>
    <div className="mt-6 flex flex-wrap items-end justify-between gap-5 text-sm"><p><span className="block font-medium">Signature</span><span className="mt-4 block w-56 max-w-full border-b">&nbsp;</span></p><p className="text-muted-foreground">Not signed · Based on supplied trip assumptions</p></div>
  </article>;
}
