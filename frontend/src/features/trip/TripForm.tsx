import { ArrowRight, ChevronDown, Clock3, FileText, RotateCcw, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Spinner } from "@/components/ui/spinner";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { LocationField } from "./LocationField";
import { isValidCycle, metadataFields, type useTripPlanner } from "./useTripPlanner";

export type Planner = ReturnType<typeof useTripPlanner>;
const metadataLabels = { driver_name: "Driver name", carrier_name: "Carrier name", carrier_address: "Carrier address", truck_number: "Truck number", trailer_number: "Trailer number", shipment_reference: "Shipment reference", starting_odometer_miles: "Starting odometer (miles)" };

export function TripForm({ planner }: { planner: Planner }) {
  const { form, update, problem, phase, timezone } = planner;
  const error = (name: string) => problem?.field_errors[name]?.join(" ");
  const used = isValidCycle(form.cycleUsed) ? Number(form.cycleUsed) : 0;
  return <Card className="trip-form self-start overflow-visible">
    <CardHeader><div className="flex items-center justify-between gap-3"><CardTitle className="text-[22px] font-semibold">Trip details</CardTitle><Settings2 className="size-5 text-muted-foreground"/></div><p className="mt-1 text-sm text-muted-foreground">Complete the route and hours below. Extra settings are optional.</p></CardHeader>
    <CardContent>
      <form onSubmit={(event) => { event.preventDefault(); void planner.submit(); }} noValidate>
        <FieldGroup className="gap-6">
          <div className="route-fields relative grid gap-5">
            <h3 className="flex items-center gap-2 text-sm font-semibold"><span className="flex size-6 items-center justify-center rounded-[6px] bg-accent text-xs text-primary">1</span>Where are you going?</h3>
            <LocationField id="current-location" label="Current location" description="Where your truck is starting from." value={form.current} error={error("current_location")} onChange={(current) => update({ current })}/>
            <LocationField id="pickup-location" label="Pickup location" description="Where you collect the load." value={form.pickup} error={error("pickup_location")} onChange={(pickup) => update({ pickup })}/>
            <LocationField id="dropoff-location" label="Drop-off location" description="Where you deliver the load." value={form.dropoff} error={error("dropoff_location")} onChange={(dropoff) => update({ dropoff })}/>
          </div>
          <h3 className="flex items-center gap-2 border-t pt-5 text-sm font-semibold"><span className="flex size-6 items-center justify-center rounded-[6px] bg-accent text-xs text-primary">2</span>Hours already worked</h3>
          <Field className="gap-2" data-invalid={Boolean(error("cycle_used_hours"))}>
            <div className="flex items-center justify-between gap-2"><FieldLabel htmlFor="cycle-used" className="text-sm">Current cycle used</FieldLabel><span className="text-xs text-muted-foreground">70-hour / 8-day cycle</span></div>
            <div className="relative"><Input id="cycle-used" inputMode="decimal" value={form.cycleUsed} onChange={(event) => update({ cycleUsed: event.target.value })} aria-invalid={Boolean(error("cycle_used_hours"))} aria-describedby="cycle-hint cycle-error" className="pr-16"/><span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">hours</span></div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-[3px] bg-secondary" aria-hidden="true"><div className="h-full rounded-[3px] bg-primary" style={{ width: `${Math.min(100, used / 70 * 100)}%` }}/></div>
            <FieldDescription id="cycle-hint" className="text-xs leading-relaxed">Driving and on-duty hours used in your current 8-day cycle. Enter 0 if you have not worked any hours.<span className="mt-2 block font-medium text-primary">{(70 - used).toFixed(used % 1 ? 2 : 0)} hours available before this trip.</span></FieldDescription>
            {error("cycle_used_hours") && <FieldError id="cycle-error">{error("cycle_used_hours")}</FieldError>}
          </Field>
          <div className="grid gap-3">
            <Button type="submit" disabled={phase === "loading"} aria-busy={phase === "loading"} className="w-full">{phase === "loading" ? <><Spinner/>Planning your trip…</> : <>Plan my trip<ArrowRight className="size-4"/></>}</Button>
            {phase === "loading" ? <Button type="button" variant="secondary" onClick={planner.cancel}>Cancel planning</Button> : <Button type="button" variant="ghost" className="text-sm text-muted-foreground" onClick={planner.reset}><RotateCcw className="size-4"/>Clear trip</Button>}
            <p className="text-center text-xs leading-relaxed text-muted-foreground">Your plan includes the route, required breaks,<br/>rest stops, and projected daily logs.</p>
          </div>
          <Collapsible className="border-t pt-5" defaultOpen={Boolean(form.departureLocal || form.timezoneOverride)}>
            <CollapsibleTrigger asChild><Button type="button" variant="ghost" className="w-full justify-between px-0 text-sm"><span className="flex items-center gap-2"><Clock3 className="size-4 text-primary"/>Departure & time zone</span><ChevronDown className="size-4"/></Button></CollapsibleTrigger>
            <CollapsibleContent className="mt-4 grid gap-4">
              <Field className="gap-2"><FieldLabel htmlFor="departure" className="text-sm">Departure (optional)</FieldLabel><Input id="departure" type="datetime-local" value={form.departureLocal} onChange={(event) => update({ departureLocal: event.target.value, timeChoice: "reject" })} aria-describedby="departure-hint departure-error" aria-invalid={Boolean(error("departure_at"))}/><FieldDescription id="departure-hint">Leave blank to depart when you submit. Entered times use {timezone}.</FieldDescription>{error("departure_at") && <FieldError id="departure-error">{error("departure_at")}</FieldError>}</Field>
              {form.departureLocal && <Field className="gap-2"><FieldLabel htmlFor="time-choice" className="text-sm">Repeated-hour choice</FieldLabel><NativeSelect id="time-choice" className="min-h-11 w-full text-sm" value={form.timeChoice} onChange={(event) => { const choice = event.target.value; update({ timeChoice: choice === "earlier" || choice === "later" ? choice : "reject" }); }}><NativeSelectOption value="reject">Ask if the time occurs twice</NativeSelectOption><NativeSelectOption value="earlier">First occurrence</NativeSelectOption><NativeSelectOption value="later">Second occurrence</NativeSelectOption></NativeSelect></Field>}
              <Field className="gap-2"><FieldLabel htmlFor="log-zone" className="text-sm">Home-terminal time zone</FieldLabel><Input id="log-zone" list="timezones" value={form.timezoneOverride} placeholder="Automatic from current location" onChange={(event) => update({ timezoneOverride: event.target.value })} aria-describedby="zone-hint"/><datalist id="timezones">{["America/New_York", "America/Chicago", "America/Denver", "America/Phoenix", "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu", "UTC"].map((zone) => <option key={zone} value={zone}/>)}</datalist><FieldDescription id="zone-hint">All daily sheets use {timezone}.</FieldDescription>{error("log_timezone") && <FieldError>{error("log_timezone")}</FieldError>}</Field>
            </CollapsibleContent>
          </Collapsible>
          <Collapsible className="border-t pt-5" defaultOpen={Object.values(form.metadata).some(Boolean)}>
            <CollapsibleTrigger asChild><Button type="button" variant="ghost" className="w-full justify-between px-0 text-sm"><span className="flex items-center gap-2"><FileText className="size-4 text-primary"/>Log sheet details<span className="text-xs font-normal text-muted-foreground">Optional</span></span><ChevronDown className="size-4"/></Button></CollapsibleTrigger>
            <CollapsibleContent className="mt-4 grid gap-4">{metadataFields.map((field) => <Field key={field} className="gap-2"><FieldLabel htmlFor={field} className="text-sm">{metadataLabels[field]}</FieldLabel><Input id={field} value={form.metadata[field] ?? ""} maxLength={field === "carrier_address" ? 240 : field === "carrier_name" ? 120 : field === "truck_number" || field === "trailer_number" ? 80 : 100} inputMode={field === "starting_odometer_miles" ? "decimal" : "text"} onChange={(event) => update({ metadata: { ...form.metadata, [field]: event.target.value } })}/></Field>)}{error("metadata") && <FieldError>{error("metadata")}</FieldError>}</CollapsibleContent>
          </Collapsible>
        </FieldGroup>
      </form>
    </CardContent>
  </Card>;
}
