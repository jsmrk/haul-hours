import { Clock3, Flag, Route } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PlanResult } from "./contracts.generated";
import { duration, miles, moment } from "./format";

export function TripSummary({ result }: { result: PlanResult }) {
  const { summary, request } = result;
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-[22px] font-semibold">Your trip, mapped out.</h2><Badge variant="success">Plan ready</Badge></div>
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Card className="py-5"><CardContent className="px-5"><p className="mb-3 flex items-center gap-2 text-sm text-muted-foreground"><Route className="size-4"/>Total distance</p><p className="text-[28px] font-semibold tracking-tight">{miles(summary.distance_m)}<span className="ml-2 text-sm font-normal text-muted-foreground">mi</span></p></CardContent></Card>
      <Card className="py-5"><CardContent className="px-5"><p className="mb-3 flex items-center gap-2 text-sm text-muted-foreground"><Clock3 className="size-4"/>Driving time</p><p className="text-[28px] font-semibold tracking-tight">{duration(summary.driving_s)}</p></CardContent></Card>
      <Card className="col-span-2 py-5 sm:col-span-1"><CardContent className="px-5"><p className="mb-3 flex items-center gap-2 text-sm text-muted-foreground"><Flag className="size-4"/>Trip duration</p><p className="text-[28px] font-semibold tracking-tight">{duration(summary.elapsed_s)}</p></CardContent></Card>
    </div>
    <div className="grid gap-3 rounded-[12px] border p-4 sm:grid-cols-3">
      {[{ label: "Pickup arrival", at: summary.pickup_arrival_at }, { label: "Drop-off arrival", at: summary.dropoff_arrival_at }, { label: "Delivery complete", at: summary.completed_at }].map(({ label, at }) => <div key={label}><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold">{moment(at, request.log_timezone, true)}</p></div>)}
    </div>
    <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground"><span><b className="font-semibold text-foreground">{summary.fuel_stop_count}</b> fuel stops</span><span><b className="font-semibold text-foreground">{summary.short_break_count}</b> short breaks</span><span><b className="font-semibold text-foreground">{summary.daily_rest_count}</b> daily rests</span><span><b className="font-semibold text-foreground">{summary.cycle_restart_count}</b> cycle restarts</span><span><b className="font-semibold text-foreground">{result.daily_logs.length}</b> log sheets</span></div>
  </div>;
}
