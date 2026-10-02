import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { DailyLog } from "./contracts.generated";
import { dayLabel } from "./format";

export function LogNavigation({ logs, selectedDate, onSelectDate }: { logs: DailyLog[]; selectedDate: string; onSelectDate: (date: string) => void }) {
  const index = logs.findIndex((log) => log.date === selectedDate);
  return <div className="flex min-w-0 flex-wrap items-center gap-2"><Button variant="secondary" size="icon" aria-label="Previous day" disabled={index <= 0} onClick={() => { const date = logs[index - 1]?.date; if (date) onSelectDate(date); }}><ChevronLeft className="size-4"/></Button><NativeSelect aria-label="Log date" className="min-h-11 min-w-0 text-sm" value={selectedDate} onChange={(event) => onSelectDate(event.target.value)}>{logs.map((log) => <NativeSelectOption key={log.date} value={log.date}>{dayLabel(log.date)}</NativeSelectOption>)}</NativeSelect><Button variant="secondary" size="icon" aria-label="Next day" disabled={index >= logs.length - 1} onClick={() => { const date = logs[index + 1]?.date; if (date) onSelectDate(date); }}><ChevronRight className="size-4"/></Button><span className="ml-1 text-xs text-muted-foreground">Day {index + 1} of {logs.length}</span></div>;
}
