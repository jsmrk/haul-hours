import { useEffect, useState } from "react";
import { Truck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function App() {
  const [health, setHealth] = useState("Connecting to planner…");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env["VITE_API_BASE_URL"] ?? ""}/api/v1/health`, { signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error(); setHealth("Planner ready"); })
      .catch(() => { if (!controller.signal.aborted) setHealth("Start the Django API to connect"); });
    return () => controller.abort();
  }, []);
  return <main className="mx-auto max-w-7xl p-6">
    <div className="mb-12 flex items-center gap-3 font-semibold"><Truck className="text-primary" />Haul Hours</div>
    <h1>Plan the road ahead.</h1><p className="mt-4 text-muted-foreground">Your route, your rest stops, your daily logs. One clear plan.</p>
    <Card className="mt-8"><CardContent><p role="status">{health}</p></CardContent></Card>
  </main>;
}
