import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function RouteMapSkeleton() {
  return <div className="route-map relative overflow-hidden rounded-[12px] border bg-secondary/40" aria-hidden="true"><Skeleton className="absolute inset-0 rounded-none"/><div className="absolute left-4 top-4 space-y-2"><Skeleton className="h-9 w-9 bg-white/70"/><Skeleton className="h-9 w-9 bg-white/70"/></div><div className="absolute inset-x-8 top-1/2 flex items-center gap-3"><Skeleton className="size-8 rounded-full bg-white/70"/><Skeleton className="h-2 flex-1 bg-white/70"/><Skeleton className="size-8 rounded-full bg-white/70"/></div></div>;
}

export function TripPlanSkeleton() {
  return <section aria-label="Trip plan preview" aria-busy="true" className="no-print space-y-6">
    <div aria-hidden="true" className="space-y-5"><Skeleton className="h-8 w-2/3"/><div className="grid grid-cols-3 gap-3">{[0, 1, 2].map((item) => <Card key={item}><CardContent className="space-y-3 px-3"><Skeleton className="h-3 w-3/4"/><Skeleton className="h-7 w-2/3"/></CardContent></Card>)}</div></div>
    <Card><CardContent className="space-y-6"><div aria-hidden="true" className="flex gap-3"><Skeleton className="h-10 flex-1"/><Skeleton className="h-10 flex-1"/></div><div className="route-workspace grid min-w-0 gap-6"><RouteMapSkeleton/><div aria-hidden="true" className="space-y-5"><Skeleton className="h-5 w-1/2"/>{[0, 1, 2, 3].map((item) => <div key={item} className="flex gap-3"><Skeleton className="size-8 shrink-0"/><div className="flex-1 space-y-3"><Skeleton className="h-4 w-4/5"/><Skeleton className="h-3 w-2/3"/><Skeleton className="h-3 w-1/3"/></div></div>)}</div></div></CardContent></Card>
  </section>;
}
