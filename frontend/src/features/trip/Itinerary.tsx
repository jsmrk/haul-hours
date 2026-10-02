import { Coffee, Fuel, Moon, PackageCheck, PackageOpen, RotateCcw, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { DutyEvent, PlanResult } from "./contracts.generated";
import { duration, miles, moment } from "./format";

export const eventLabels = { drive: "Driving", pickup: "Pickup", dropoff: "Drop-off", fuel: "Fuel stop", break: "Driving break", daily_rest: "Daily rest", cycle_restart: "Cycle restart" };
const icons = { drive: Truck, pickup: PackageOpen, dropoff: PackageCheck, fuel: Fuel, break: Coffee, daily_rest: Moon, cycle_restart: RotateCcw };

export function Itinerary({ result, selectedEventId, onSelectEvent }: { result: PlanResult; selectedEventId: string | null; onSelectEvent: (id: string) => void }) {
  return <section aria-label="Trip itinerary" className="min-w-0"><div className="mb-4 flex justify-between gap-3"><h3 className="font-semibold">Stops & schedule</h3><span className="text-xs text-muted-foreground">{result.events.length} activities</span></div><ol className="itinerary-list space-y-3">
    {result.events.map((event) => <li key={event.id}>
      <ItineraryEvent event={event} zone={result.request.log_timezone} selected={event.id === selectedEventId} onSelect={() => onSelectEvent(event.id)}/>
      {event.driving_leg_id && <Collapsible className="ml-3 mt-1"><CollapsibleTrigger asChild><Button variant="ghost" size="sm" className="text-xs text-muted-foreground">Turn instructions</Button></CollapsibleTrigger><CollapsibleContent><ol className="mt-2 space-y-2 border-l pl-4 text-sm text-muted-foreground">{result.road_legs.find((leg) => leg.id === event.driving_leg_id)?.steps.map((step, index) => <li key={index}>{step.instruction}<span className="ml-2 text-xs">{miles(step.distance_m)} mi</span></li>)}</ol></CollapsibleContent></Collapsible>}
    </li>)}
  </ol></section>;
}

function ItineraryEvent({ event, zone, selected, onSelect }: { event: DutyEvent; zone: string; selected: boolean; onSelect: () => void }) {
  const Icon = icons[event.kind];
  const location = event.kind === "drive" ? `${event.start_location.label} → ${event.end_location.label}` : event.start_location.label;
  return <Button type="button" variant={selected ? "subtle" : "white"} aria-pressed={selected} aria-label={`${eventLabels[event.kind]} ${location}`} onClick={onSelect} className="w-full min-w-0 items-start justify-start gap-3 border p-3 text-left whitespace-normal shadow-none">
    <span className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-[8px] bg-accent text-primary"><Icon className="size-4"/></span>
    <span className="min-w-0 flex-1"><span className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-semibold">{eventLabels[event.kind]}</span><Badge variant="neutral" className="text-xs">{event.status}</Badge></span><span className="mt-1 block break-words text-sm font-normal text-foreground">{location}</span><span className="mt-2 block text-xs font-normal leading-relaxed text-muted-foreground">{moment(event.start_at, zone, true)} → {moment(event.end_at, zone)}<br/>{duration((Date.parse(event.end_at) - Date.parse(event.start_at)) / 1000)}{event.distance_m > 0 ? ` · ${miles(event.distance_m)} mi` : ""}</span>{event.kind !== "drive" && <span className="mt-2 block text-xs font-normal leading-relaxed text-muted-foreground">{event.reasons.join(". ")}</span>}{event.poi_id && <span className="mt-2 block text-xs font-normal text-muted-foreground">Mapped stopping place · Space availability unverified</span>}</span>
  </Button>;
}
