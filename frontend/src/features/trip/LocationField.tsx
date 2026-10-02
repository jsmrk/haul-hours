import { useEffect, useState } from "react";
import { Check, ChevronsUpDown, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Spinner } from "@/components/ui/spinner";
import { searchLocations } from "./api";
import type { Location } from "./contracts.generated";
import type { LocationSelection } from "./useTripPlanner";

interface Props { label: string; id: string; value: LocationSelection; onChange: (value: LocationSelection) => void; error?: string | undefined }

export function LocationField({ label, id, value, onChange, error }: Props) {
  const [open, setOpen] = useState(false);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLocations([]); setFailure(""); setLoading(false);
    if (!open || value.query.trim().length < 3) return () => { current = false; controller.abort(); };
    const timer = setTimeout(() => {
      setLoading(true);
      searchLocations(value.query.trim(), controller.signal).then((found) => { if (current) setLocations(found); })
        .catch((error: unknown) => { if (current) setFailure(error instanceof Error ? error.message : "Address search failed. Try again."); })
        .finally(() => { if (current) setLoading(false); });
    }, 300);
    return () => { current = false; clearTimeout(timer); controller.abort(); };
  }, [open, value.query]);
  return <Field data-invalid={Boolean(error)} className="min-w-0 gap-2">
    <FieldLabel htmlFor={id} className="text-sm font-medium">{label}</FieldLabel>
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild><Button id={id} type="button" variant="secondary" role="combobox" aria-label={label} aria-expanded={open} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} className="w-full min-w-0 justify-between border border-input bg-white px-3 text-left font-normal">
        <span className="flex min-w-0 items-center gap-2"><MapPin className="size-4 shrink-0 text-primary"/><span className={value.location ? "truncate" : "truncate text-muted-foreground"}>{value.query || "Select a city or address"}</span></span><ChevronsUpDown className="ml-2 size-4 shrink-0 text-muted-foreground"/>
      </Button></PopoverTrigger>
      <PopoverContent align="start" aria-label={`${label} suggestions`} className="w-[var(--radix-popover-trigger-width)] max-w-[calc(100vw-32px)] p-0">
        <Command shouldFilter={false} label={`Search ${label.toLowerCase()}`}>
          <CommandInput aria-label={`Search ${label.toLowerCase()}`} placeholder="Search a US city or address…" value={value.query} onValueChange={(query) => onChange({ query, location: null })}/>
          <CommandList>
            {value.query.trim().length < 3 && <p className="p-4 text-sm text-muted-foreground">Type at least three characters.</p>}
            {loading && <p role="status" className="flex gap-2 p-4 text-sm text-muted-foreground"><Spinner/>Finding locations…</p>}
            {failure && <p role="alert" className="p-4 text-sm">{failure}</p>}
            {!loading && !failure && locations.length === 0 && value.query.trim().length >= 3 && <p className="p-4 text-sm text-muted-foreground">Choose a full address or city in the United States.</p>}
            {locations.map((location) => <CommandItem key={location.id} value={location.id} className="min-h-12 cursor-pointer p-3 text-sm" onSelect={() => { onChange({ query: location.label, location }); setOpen(false); }}>
              <MapPin className="size-4 text-primary"/><span className="min-w-0 flex-1 whitespace-normal">{location.label}</span>{value.location?.id === location.id && <Check className="size-4"/>}
            </CommandItem>)}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
    {error && <FieldError id={`${id}-error`}>{error}</FieldError>}
  </Field>;
}
