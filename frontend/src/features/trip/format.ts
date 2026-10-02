export function duration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor(seconds % 3600 / 60);
  const remainder = seconds % 60;
  return [hours ? `${hours}h` : "", minutes ? `${minutes}m` : "", remainder ? `${remainder}s` : ""].filter(Boolean).join(" ") || "0m";
}

export function logDuration(seconds: number): string {
  return [Math.floor(seconds / 3600), Math.floor(seconds % 3600 / 60), seconds % 60].map((part) => String(part).padStart(2, "0")).join(":");
}
export const miles = (meters: number, digits = 1) => (meters / 1609.344).toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const moment = (instant: string, zone: string, date = false) => new Intl.DateTimeFormat("en-US", {
  timeZone: zone, ...(date ? { month: "short", day: "numeric" } as const : {}), hour: "numeric", minute: "2-digit", timeZoneName: "short",
}).format(new Date(instant));
export const dayLabel = (date: string) => new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short", day: "numeric", weekday: "short" }).format(new Date(date + "T12:00:00Z"));
