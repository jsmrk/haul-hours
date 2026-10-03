import { lazy, Suspense, useState } from "react";
import { FileText, Route, Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import type { PlanResult } from "./contracts.generated";
import { TripSummary } from "./TripSummary";
import { Itinerary } from "./Itinerary";
import { DailyLogSheet } from "./DailyLogSheet";
import { LogNavigation } from "./LogNavigation";
import { ExportControls } from "./ExportControls";
import { RouteMapSkeleton } from "./TripSkeleton";

const RouteMap = lazy(() => import("./RouteMap"));

export function TripResults({ result, selectedEventId, onSelectEvent }: { result: PlanResult; selectedEventId: string | null; onSelectEvent: (id: string) => void }) {
  const [date, setDate] = useState(result.daily_logs[0]?.date ?? "");
  const log = result.daily_logs.find((item) => item.date === date);
  return <><div className="screen-result space-y-6">
    <TripSummary result={result}/>
    <Card><CardContent>
      <Tabs defaultValue="route"><TabsList className="mb-6 h-12 w-full rounded-[12px] bg-secondary p-1"><TabsTrigger value="route" className="min-h-10 rounded-[12px] text-sm"><Route className="size-4"/>Route & stops</TabsTrigger><TabsTrigger value="logs" className="min-h-10 rounded-[12px] text-sm"><FileText className="size-4"/>Daily logs<span className="ml-1 text-xs">{result.daily_logs.length}</span></TabsTrigger></TabsList>
        <TabsContent value="route"><div className="route-workspace grid min-w-0 gap-6"><Suspense fallback={<div role="status" aria-label="Loading route map"><span className="sr-only">Loading route map…</span><RouteMapSkeleton/></div>}><RouteMap result={result} selectedEventId={selectedEventId} onSelectEvent={onSelectEvent}/></Suspense><Itinerary result={result} selectedEventId={selectedEventId} onSelectEvent={onSelectEvent}/></div></TabsContent>
        <TabsContent value="logs"><div className="space-y-6"><div className="flex flex-wrap justify-between gap-4"><LogNavigation logs={result.daily_logs} selectedDate={date} onSelectDate={setDate}/></div><ExportControls result={result} date={date}/>{log && <DailyLogSheet log={log} metadata={result.request.metadata ?? {}} selectedEventId={selectedEventId} onSelectEvent={onSelectEvent}/>}</div></TabsContent>
      </Tabs>
    </CardContent></Card>
    <Collapsible className="rounded-[12px] border p-4"><CollapsibleTrigger asChild><Button variant="ghost" size="sm" className="px-0 text-sm"><Info className="size-4 text-primary"/>Planning assumptions & limitations</Button></CollapsibleTrigger><CollapsibleContent><ul className="mt-3 space-y-2 pl-5 text-sm leading-relaxed text-muted-foreground list-disc">{[...result.assumptions, ...result.warnings].map((item, index) => <li key={index}>{item}</li>)}</ul></CollapsibleContent></Collapsible>
  </div><div className="print-only">{result.daily_logs.map((item) => <div key={item.date} data-log-date={item.date} className="print-sheet"><DailyLogSheet log={item} metadata={result.request.metadata ?? {}}/></div>)}</div></>;
}
