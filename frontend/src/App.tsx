import { Coffee, FileText, MapPinned, MoveRight, Route, ShieldCheck, Truck, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { TripForm } from "@/features/trip/TripForm";
import { useTripPlanner } from "@/features/trip/useTripPlanner";

export default function App() {
  const planner = useTripPlanner();
  return <>
    <header className="border-b"><div className="page-shell flex min-h-20 items-center justify-between gap-4"><a href="/" className="flex items-center gap-3 text-[22px] font-semibold tracking-tight"><span className="flex size-10 items-center justify-center rounded-[12px] bg-primary text-white"><Truck className="size-6"/></span>haul<span className="-ml-2 text-primary">hours</span></a><div className="flex items-center gap-2 text-sm text-muted-foreground"><ShieldCheck className="size-4 text-primary"/><span className="hidden phone:inline">Built around your duty limits</span><Badge variant="neutral" className="hidden sm:inline-flex">70 hrs / 8 days</Badge></div></div></header>
    <main className="page-shell py-10 sm:py-12">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5"><div><p className="mb-3 flex items-center gap-2 text-sm font-medium text-primary"><Route className="size-4"/>YOUR NEXT HAUL, PLANNED</p><h1>Plan the road ahead.</h1><p className="mt-4 max-w-2xl text-muted-foreground">A clear route. The right breaks. Daily logs ready to go.</p></div><div className="flex items-center gap-2 text-sm text-muted-foreground"><span className="size-2 rounded-full bg-[var(--color-success)]"/>Property-carrying · Single driver</div></div>
      <div className="planner-layout grid items-start gap-6">
        <TripForm planner={planner}/>
        <div className="min-w-0 space-y-6">
          {planner.phase === "loading" && <Alert role="status" className="border-primary/25 bg-accent/30"><Spinner className="text-primary"/><AlertTitle>Finding your way forward</AlertTitle><AlertDescription>Checking truck routes, real stopping places, and duty limits. Longer trips may take a few minutes.</AlertDescription></Alert>}
          {planner.problem && <Alert role="alert"><AlertCircle/><AlertTitle>{planner.phase === "blocked" ? "This trip needs a different stopping plan" : "We couldn’t complete this plan"}</AlertTitle><AlertDescription>{planner.problem.message}{planner.problem.safe_prefix.length > 0 && <p className="mt-2">{planner.problem.safe_prefix.length} safe activities were computed. No complete arrival time or trip export is available.</p>}</AlertDescription></Alert>}
          {planner.result && planner.phase !== "blocked" ? <Card><CardContent><p>Your trip is ready. {planner.result.daily_logs.length} daily sheets generated.</p></CardContent></Card> : <EmptyWorkspace/>}
        </div>
      </div>
      <footer className="mt-10 flex flex-wrap justify-between gap-3 border-t py-6 text-xs leading-relaxed text-muted-foreground"><p>Projected schedules based on your trip inputs. Keep your actual duty records current.</p><p>Road data © OpenStreetMap contributors · Routing by openrouteservice</p></footer>
    </main>
  </>;
}

function EmptyWorkspace() {
  return <Card className="empty-workspace"><CardContent>
    <div className="empty-map relative -mx-6 -mt-6 mb-8 overflow-hidden border-b" aria-hidden="true">
      <svg viewBox="0 0 720 280" className="h-full w-full" preserveAspectRatio="xMidYMid slice"><defs><pattern id="street-grid" width="72" height="56" patternTransform="rotate(-14)" patternUnits="userSpaceOnUse"><path d="M 72 0 L 0 0 0 56" fill="none" stroke="#dedee5" strokeWidth="1"/></pattern></defs><rect width="720" height="280" fill="#fff"/><rect width="720" height="280" fill="url(#street-grid)"/><path d="M-50 190 Q140 210 210 170 T400 100 T780 130" fill="none" stroke="#dedee5" strokeWidth="32" opacity=".4"/><path d="M140 205 L235 205 Q255 205 255 185 L255 130 Q255 110 275 110 L440 110 Q460 110 460 90 L460 65 L580 65" fill="none" stroke="#7132f5" strokeWidth="4" strokeDasharray="9 7"/><circle cx="140" cy="205" r="9" fill="#7132f5" stroke="white" strokeWidth="4"/><circle cx="460" cy="65" r="9" fill="#7132f5" stroke="white" strokeWidth="4"/><circle cx="580" cy="65" r="11" fill="white" stroke="#7132f5" strokeWidth="4"/><rect x="297" y="149" width="126" height="40" rx="12" fill="white" stroke="#dedee5"/><text x="360" y="174" textAnchor="middle" fill="#686b82" fontSize="14" fontFamily="Arial">Your route awaits</text></svg>
      <div className="absolute left-5 top-5 rounded-[8px] border bg-white px-3 py-2 text-xs font-medium text-muted-foreground">ROUTE PREVIEW</div>
    </div>
    <div className="mx-auto max-w-xl text-center"><span className="mx-auto mb-5 flex size-14 items-center justify-center rounded-[16px] bg-accent text-primary"><MapPinned className="size-7"/></span><h2>Your next trip starts here.</h2><p className="mx-auto mt-3 max-w-md text-muted-foreground">Add your locations and current cycle hours. We’ll connect the route, rest stops, and daily logs.</p></div>
    <div className="mt-8 grid gap-5 sm:grid-cols-3">{[{ icon: Route, title: "See the full route", copy: "Truck routing with real fuel and rest stops." }, { icon: Coffee, title: "Make time for rest", copy: "Breaks and resets planned around duty limits." }, { icon: FileText, title: "Get your daily logs", copy: "A projected sheet for every day of your trip." }].map(({ icon: Icon, title, copy }) => <div key={title} className="rounded-[12px] border bg-secondary/30 p-4"><Icon className="mb-3 size-5 text-primary"/><h3 className="text-sm font-semibold">{title}</h3><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy}</p></div>)}</div>
    <div className="mt-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">Fill in your trip details<MoveRight className="size-4"/>See your plan</div>
  </CardContent></Card>;
}
