/* Generated from Django API serializers. Run npm run contracts:generate. Do not edit. */

export type HaulHoursContracts = TripRequest | PlanResult | LocationSearchResult | PlanningProblem | PDFExportRequest;

export interface TripRequest {
  current_location: Location;
  cycle_used_hours: string;
  departure_at: string;
  dropoff_location: Location;
  log_timezone: string;
  metadata?: LogMetadata;
  pickup_location: Location;
}
export interface Location {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
  timezone: string;
}
export interface LogMetadata {
  carrier_address?: string | null;
  carrier_name?: string | null;
  driver_name?: string | null;
  shipment_reference?: string | null;
  starting_odometer_miles?: string | null;
  trailer_number?: string | null;
  truck_number?: string | null;
}
export interface PlanResult {
  assumptions: string[];
  daily_logs: DailyLog[];
  events: DutyEvent[];
  export_token: string;
  planner_version: string;
  request: TripRequest;
  road_legs: RoadLeg[];
  summary: TripSummary;
  warnings: string[];
}
export interface DailyLog {
  date: string;
  distance_m: number;
  duration_s: number;
  end_at: string;
  graph: LogGraph;
  intervals: LogInterval[];
  remarks: LogRemark[];
  start_at: string;
  timezone: string;
  totals_s: {
    [k: string]: number;
  };
}
export interface LogGraph {
  paths: GraphPath[];
  ticks: GraphTick[];
}
export interface GraphPath {
  event_id: string | null;
  points: [number, number][];
}
export interface GraphTick {
  elapsed_s: number;
  label: string;
  utc_offset_s: number;
}
export interface LogInterval {
  assumed_outside_trip: boolean;
  distance_m: number;
  end_at: string;
  event_id: string | null;
  start_at: string;
  status: "OFF" | "SB" | "D" | "ON";
}
export interface LogRemark {
  at: string;
  event_id: string | null;
  location_label: string;
  note: string;
}
export interface DutyEvent {
  distance_m: number;
  driving_leg_id: string | null;
  end_at: string;
  end_location: Location;
  id: string;
  kind: "drive" | "pickup" | "dropoff" | "fuel" | "break" | "daily_rest" | "cycle_restart";
  poi_id: string | null;
  reasons: string[];
  start_at: string;
  start_location: Location;
  status: "OFF" | "SB" | "D" | "ON";
}
export interface RoadLeg {
  destination: Location;
  distance_m: number;
  duration_s: number;
  id: string;
  origin: Location;
  steps: RoadStep[];
}
export interface RoadStep {
  distance_m: number;
  duration_s: number;
  geometry: [number, number][];
  instruction: string;
}
export interface TripSummary {
  completed_at: string;
  cycle_restart_count: number;
  daily_rest_count: number;
  distance_m: number;
  driving_s: number;
  dropoff_arrival_at: string;
  elapsed_s: number;
  fuel_stop_count: number;
  off_duty_s: number;
  on_duty_s: number;
  pickup_arrival_at: string;
  short_break_count: number;
}
export interface LocationSearchResult {
  locations: Location[];
}
export interface PlanningProblem {
  code: string;
  field_errors: {
    [k: string]: string[];
  };
  message: string;
  retryable: boolean;
  safe_prefix: DutyEvent[];
}
export interface PDFExportRequest {
  date?: string;
  export_token: string;
  metadata?: LogMetadata;
}
