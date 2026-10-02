import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { DutyEvent, PlanResult, RoadLeg } from "./contracts.generated";
import { eventLabels } from "./Itinerary";
import { moment } from "./format";

const glyphs = { origin: "O", pickup: "P", dropoff: "D", fuel: "F", break: "B", daily_rest: "R", cycle_restart: "C", drive: "→" };
const markerIcon = (kind: keyof typeof glyphs, selected = false) => L.divIcon({ className: "haul-marker-wrapper", html: `<span class="haul-marker ${selected ? "is-selected" : ""}">${glyphs[kind]}</span>`, iconSize: [34, 34], iconAnchor: [17, 17] });
const geometry = (leg: RoadLeg): [number, number][] => leg.steps.flatMap((step) => step.geometry.map(([longitude, latitude]) => [latitude, longitude]));

export default function RouteMap({ result, selectedEventId, onSelectEvent }: { result: PlanResult; selectedEventId: string | null; onSelectEvent: (id: string) => void }) {
  const markers = useRef(new Map<string, L.Marker>());
  const selectedEvent = result.events.find((event) => event.id === selectedEventId);
  const first = result.request.current_location;
  return <div className="relative isolate overflow-hidden rounded-[12px] border">
    <MapContainer center={[first.latitude, first.longitude]} zoom={6} className="route-map" scrollWheelZoom={false}>
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' maxZoom={19}/>
      {result.road_legs.map((leg) => <Polyline key={leg.id} positions={geometry(leg)} pathOptions={{ color: "#7132f5", opacity: .9, weight: selectedEvent?.driving_leg_id === leg.id ? 7 : 4 }} eventHandlers={{ click: () => { const event = result.events.find((item) => item.driving_leg_id === leg.id); if (event) onSelectEvent(event.id); } }}/>) }
      <Marker title={`Current location ${first.label}`} position={[first.latitude, first.longitude]} icon={markerIcon("origin")}><Popup><p className="font-semibold">Current location</p><p>{first.label}</p></Popup></Marker>
      {result.events.filter((event) => event.kind !== "drive").map((event) => <Marker key={event.id} title={`${eventLabels[event.kind]} ${event.start_location.label}`} ref={(marker) => { if (marker) markers.current.set(event.id, marker); else markers.current.delete(event.id); }} position={[event.start_location.latitude, event.start_location.longitude]} icon={markerIcon(event.kind, event.id === selectedEventId)} eventHandlers={{ click: () => onSelectEvent(event.id) }}><Popup><p className="font-semibold">{eventLabels[event.kind]}</p><p>{event.start_location.label}</p><p>{moment(event.start_at, result.request.log_timezone, true)} — {moment(event.end_at, result.request.log_timezone)}</p><p>{event.reasons.join(". ")}</p>{event.poi_id && <p>Live parking availability has not been checked.</p>}</Popup></Marker>)}
      <MapFocus result={result} selectedEvent={selectedEvent} markers={markers.current}/>
    </MapContainer>
    <div className="flex flex-wrap gap-x-4 gap-y-2 border-t bg-white p-3 text-xs text-muted-foreground">{[["O", "Origin"], ["P", "Pickup"], ["D", "Drop-off"], ["F", "Fuel"], ["B", "Break"], ["R", "Daily rest"], ["C", "Cycle restart"]].map(([glyph, label]) => <span key={glyph} className="inline-flex items-center gap-1.5"><b className="flex size-5 items-center justify-center rounded-[6px] bg-accent text-primary">{glyph}</b>{label}</span>)}</div>
  </div>;
}

function MapFocus({ result, selectedEvent, markers }: { result: PlanResult; selectedEvent: DutyEvent | undefined; markers: Map<string, L.Marker> }) {
  const map = useMap();
  const bounds = useMemo(() => L.latLngBounds([
    ...result.road_legs.flatMap(geometry), [result.request.current_location.latitude, result.request.current_location.longitude],
    [result.request.pickup_location.latitude, result.request.pickup_location.longitude], [result.request.dropoff_location.latitude, result.request.dropoff_location.longitude],
  ]), [result]);
  useEffect(() => { map.invalidateSize(); map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 }); }, [bounds, map]);
  useEffect(() => {
    if (!selectedEvent) return;
    const leg = result.road_legs.find((item) => item.id === selectedEvent.driving_leg_id);
    if (leg) map.fitBounds(L.latLngBounds(geometry(leg)), { padding: [35, 35], maxZoom: 13 });
    else { map.panTo([selectedEvent.start_location.latitude, selectedEvent.start_location.longitude]); markers.get(selectedEvent.id)?.openPopup(); }
  }, [map, markers, result, selectedEvent]);
  return null;
}
