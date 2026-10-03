import { useCallback, useEffect, useRef, useState } from "react";
import { Check, MapPin } from "lucide-react";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover";
import { Command, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Spinner } from "@/components/ui/spinner";
import { searchLocations } from "./api";
import type { Location } from "./contracts.generated";
import type { LocationSelection } from "./useTripPlanner";

interface Props { label: string; id: string; value: LocationSelection; onChange: (value: LocationSelection) => void; error?: string | undefined }

export function LocationField({ label, id, value, onChange, error }: Props) {
  const anchor = useRef<HTMLDivElement>(null);
  const [inputId, setInputId] = useState(id);
  // cmdk restores focus through its generated input ID; bind the visible label to it.
  const bindInput = useCallback((input: HTMLInputElement | null) => { if (input) setInputId(input.id); }, []);
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
    <FieldLabel id={`${id}-label`} htmlFor={inputId} className="text-sm font-medium">{label}</FieldLabel>
    <Popover open={open} onOpenChange={setOpen}>
      <Command shouldFilter={false} label={`Search ${label.toLowerCase()}`} className="h-auto min-w-0 overflow-visible bg-transparent p-0 [&_[data-slot=command-input-wrapper]]:p-0 [&_[data-slot=input-group]]:rounded-xl! [&_[data-slot=input-group]]:focus-within:border-primary/40 [&_[data-slot=input-group]]:focus-within:ring-2 [&_[data-slot=input-group]]:focus-within:ring-primary/20">
        <PopoverAnchor asChild><div ref={anchor}>
          <CommandInput ref={bindInput} asChild aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} autoComplete="off" placeholder="Type a US city or address…" value={value.query}
            onFocus={() => setOpen(true)} onClick={() => setOpen(true)}
            onValueChange={(query) => { onChange({ query, location: null }); setOpen(true); }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpen(false);
              if (event.key === "ArrowDown" || event.key === "ArrowUp") setOpen(true);
              if (event.key === "Enter" && open && (loading || locations.length === 0)) event.preventDefault();
            }}><input aria-labelledby={`${id}-label`} aria-expanded={open}/></CommandInput>
        </div></PopoverAnchor>
        <PopoverContent align="start" aria-label={`${label} suggestions`} className="w-[var(--radix-popover-trigger-width)] max-w-[calc(100vw-32px)] p-1"
          onOpenAutoFocus={(event) => event.preventDefault()} onCloseAutoFocus={(event) => event.preventDefault()}
          onInteractOutside={(event) => { if (event.target instanceof Node && anchor.current?.contains(event.target)) event.preventDefault(); }}>
          <CommandList>
            {value.query.trim().length < 3 && <p className="p-4 text-sm text-muted-foreground">Type at least three characters.</p>}
            {loading && <p role="status" className="flex gap-2 p-4 text-sm text-muted-foreground"><Spinner/>Finding locations…</p>}
            {failure && <p role="alert" className="p-4 text-sm">{failure}</p>}
            {!loading && !failure && locations.length === 0 && value.query.trim().length >= 3 && <p className="p-4 text-sm text-muted-foreground">No matching locations. Try another US city or address.</p>}
            {locations.map((location) => <CommandItem key={location.id} value={location.id} className="min-h-12 cursor-pointer p-3 text-sm" onSelect={() => { onChange({ query: location.label, location }); setOpen(false); }}>
              <MapPin className="size-4 text-primary"/><span className="min-w-0 flex-1 whitespace-normal">{location.label}</span>{value.location?.id === location.id && <Check className="size-4"/>}
            </CommandItem>)}
          </CommandList>
        </PopoverContent>
      </Command>
    </Popover>
    {error && <FieldError id={`${id}-error`}>{error}</FieldError>}
  </Field>;
}
