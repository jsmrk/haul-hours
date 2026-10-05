import { Coffee, FileText, MapPinned, Route, ShieldCheck, Truck, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { TripPlanSkeleton } from "@/features/trip/TripSkeleton";
import { TripForm } from "@/features/trip/TripForm";
import { useTripPlanner } from "@/features/trip/useTripPlanner";
import { TripResults } from "@/features/trip/TripResults";
import { usesFixtureData } from "@/features/trip/api";
import { useEffect, useState } from "react";

export default function App() {
  const planner = useTripPlanner();
  const locationCount = [planner.form.current, planner.form.pickup, planner.form.dropoff].filter((value) => value.location).length;
  const [fixtureMode, setFixtureMode] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void usesFixtureData(controller.signal).then(setFixtureMode).catch(() => {});
    return () => controller.abort();
  }, []);
  const [selection, setSelection] = useState<{ token: string; event: string } | null>(null);
  return <>
    <header className="border-b"><div className="page-shell flex min-h-20 items-center justify-between gap-4"><a href="/" className="flex items-center gap-3 text-[22px] font-semibold tracking-tight"><span className="flex size-10 items-center justify-center rounded-[12px] bg-primary text-white"><Truck className="size-6"/></span>haul<span className="-ml-2 text-primary">hours</span></a><div className="flex items-center gap-2 text-sm text-muted-foreground"><ShieldCheck className="size-4 text-primary"/><span className="hidden phone:inline">Built around your duty limits</span><Badge variant="neutral" className="hidden sm:inline-flex">70 hrs / 8 days</Badge></div></div></header>
    <main className="page-shell py-6 sm:py-8">
      {fixtureMode && <Alert role="note" className="mb-6 no-print"><AlertCircle/><AlertTitle>Demo mode — sample routes</AlertTitle><AlertDescription><p>Live data is not connected in this session. These routes and stop times are for testing.</p><p>Search these demo cities: Pittsburgh, Harrisburg, Philadelphia, Los Angeles, San Diego, Boston, or Miami.</p></AlertDescription></Alert>}
      <div className="workspace-hero mb-6 flex flex-wrap items-end justify-between gap-4"><div><h1>Plan your next delivery</h1><p className="mt-3 max-w-2xl text-muted-foreground">Choose your route, add your hours worked, and get a trip plan with daily logs.</p></div><Badge variant="neutral" className="text-xs">US routes · Single driver · 70-hour cycle</Badge></div>
      <ol aria-label="How to plan a trip" className="no-print mb-6 grid gap-3 sm:grid-cols-3">{[{ title: "Choose your route", copy: "Starting point, pickup, and delivery" }, { title: "Add your hours", copy: "Work already used in your 8-day cycle" }, { title: "Review your plan", copy: "Route, breaks, and downloadable logs" }].map((step, index) => <li key={step.title} className="flex items-center gap-3 rounded-[12px] border bg-white p-3"><span className="flex size-8 shrink-0 items-center justify-center rounded-[8px] bg-accent font-semibold text-primary">{index + 1}</span><div className="min-w-0"><p className="text-sm font-semibold">{step.title}</p><p className="mt-1 text-xs text-muted-foreground">{step.copy}</p></div></li>)}</ol>
      <div className="planner-layout grid items-start gap-6">
        <TripForm planner={planner}/>
        <div className="min-w-0 space-y-6">
          {planner.phase === "loading" && <Alert role="status" aria-label="Building your trip plan" className="no-print border-primary/25 bg-accent/30"><Route className="text-primary"/><AlertTitle>Building your trip plan</AlertTitle><AlertDescription>Finding your route and stops, then preparing your daily logs. Longer trips may take a few minutes. You can cancel planning at any time.</AlertDescription></Alert>}
          {planner.problem && <Alert role="alert" className="no-print"><AlertCircle/><AlertTitle>{planner.phase === "blocked" ? "This trip needs a different stopping plan" : "We couldn’t complete this plan"}</AlertTitle><AlertDescription>{planner.problem.message}{planner.problem.safe_prefix.length > 0 && <div className="mt-3"><p>{planner.problem.safe_prefix.length} safe activities were computed. No complete arrival time or trip export is available.</p><ol className="mt-2 list-decimal space-y-1 pl-5">{planner.problem.safe_prefix.map((event) => <li key={event.id}>{event.kind.replaceAll("_", " ")} · {event.end_location.label}</li>)}</ol></div>}{planner.problem.retryable && <Button type="button" variant="outline" size="sm" className="mt-3" onClick={() => void planner.submit()}>Try again</Button>}</AlertDescription></Alert>}
          {planner.phase === "loading" ? <TripPlanSkeleton/> : planner.result && planner.phase !== "blocked" ? <>
            {planner.previousResult && <Alert role="note" className="no-print"><InfoPrevious/><AlertTitle>Previous trip</AlertTitle><AlertDescription>These results belong to your last submitted trip. Plan again to apply your changes.</AlertDescription></Alert>}
            <TripResults key={planner.result.export_token} result={planner.result} selectedEventId={selection?.token === planner.result.export_token ? selection.event : null} onSelectEvent={(event) => { if (planner.result) setSelection({ token: planner.result.export_token, event }); }}/>
          </> : <EmptyWorkspace locationCount={locationCount}/>}
        </div>
      </div>
      <footer className="mt-10 flex flex-wrap justify-between gap-3 border-t py-6 text-xs leading-relaxed text-muted-foreground"><p>Projected schedules based on your trip inputs. Keep your actual duty records current.</p><p>Road data © OpenStreetMap contributors · Routing by openrouteservice · Truck parking: USDOT/BTS</p></footer>
    </main>
  </>;
}

const InfoPrevious = AlertCircle;

function EmptyWorkspace({ locationCount }: { locationCount: number }) {
  return <Card className="empty-workspace"><CardContent>
    <div className="rounded-[12px] border border-dashed bg-secondary/20 px-4 py-8 text-center sm:py-10"><span className="mx-auto mb-4 flex size-14 items-center justify-center rounded-[16px] bg-accent text-primary"><MapPinned className="size-7"/></span><h2>Your route will appear here</h2><p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">Fill in the trip details, then select <strong className="font-semibold text-foreground">Plan my trip</strong>. Your route, stops, and daily logs will appear in this space.</p></div>
    <div className="mt-5 flex items-start gap-3 rounded-[12px] border bg-accent/20 p-4"><CheckCircle2 className="mt-0.5 size-5 shrink-0 text-primary"/><div><p className="text-sm font-semibold">{locationCount} of 3 locations selected</p><p className="mt-1 text-sm text-muted-foreground">{locationCount === 3 ? "Check your hours worked, then plan your trip." : "Type a city or address and choose a matching suggestion for each location."}</p></div></div>
    <div className="mt-6 space-y-5">{[{ icon: Route, title: "Route and stops", copy: "See the drive from your starting point to pickup and delivery." }, { icon: Coffee, title: "Breaks and rest", copy: "See when to stop for fuel, driving breaks, and daily rest." }, { icon: FileText, title: "Daily logs", copy: "Review each day's projected duty sheet and download a PDF." }].map(({ icon: Icon, title, copy }) => <div key={title} className="flex gap-3"><span className="flex size-9 shrink-0 items-center justify-center rounded-[8px] bg-secondary"><Icon className="size-4 text-primary"/></span><div><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-sm leading-relaxed text-muted-foreground">{copy}</p></div></div>)}</div>
  </CardContent></Card>;
}
