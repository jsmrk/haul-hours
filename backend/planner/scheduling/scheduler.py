from dataclasses import dataclass
from datetime import timedelta

from planner.constants import (
    BREAK_S,
    CYCLE_RESTART_S,
    CYCLE_S,
    DAILY_DRIVE_S,
    DAILY_REST_S,
    DRIVING_WINDOW_S,
    FUEL_RANGE_M,
    FUEL_S,
    MAX_STOPS,
    SERVICE_S,
)
from planner.contracts import DutyEvent, DutyStatus, EventKind, Location, TripRequest
from planner.duty.audit import audit_timeline
from planner.duty.limits import driving_allowance
from planner.duty.state import DutyState, initial_state
from planner.duty.transitions import apply_event
from planner.errors import PlanningProblem
from planner.routing.contracts import (
    ProviderBudget,
    RoadLeg,
    RoutingProvider,
    StopPlace,
    StopProvider,
    StopSearch,
)
from planner.routing.geometry import boundary_elapsed, point_at_elapsed
from planner.scheduling.candidates import projected_progress, rank_candidates


@dataclass(frozen=True)
class ScheduledTrip:
    request: TripRequest
    road_legs: tuple[RoadLeg, ...]
    events: tuple[DutyEvent, ...]
    warnings: tuple[str, ...]


def schedule_trip(request: TripRequest, routing: RoutingProvider, stops: StopProvider,
                  budget: ProviderBudget) -> ScheduledTrip:
    # Validate both mandatory legs before scheduling detours or suggesting a complete result.
    baseline = (routing.route(request.current_location, request.pickup_location, budget),
                routing.route(request.pickup_location, request.dropoff_location, budget))
    best_prefix: tuple[DutyEvent, ...] = ()
    best_progress = (-1, -1, -1)
    backtracks = 0

    def remember(events, stage):
        nonlocal best_prefix, best_progress
        score = stage, sum(event.distance_m for event in events), len(events)
        if score > best_progress:
            best_prefix, best_progress = events, score

    def append(state, events, kind, status, seconds, origin, destination=None, leg=None, poi=None, reasons=()):
        event = DutyEvent(f"event-{len(events) + 1:04d}", kind, status, state.now,
                          state.now + timedelta(seconds=seconds), origin, destination or origin,
                          leg.distance_m if leg else 0, leg.id if leg else None, reasons, poi.id if poi else None)
        return apply_event(state, event), events + (event,)

    def drive(state, events, legs, leg):
        if leg.duration_s == 0:
            return state, events, legs
        state, events = append(state, events, EventKind.DRIVE, DutyStatus.D, leg.duration_s,
                               leg.origin, leg.destination, leg, reasons=("Truck road route",))
        return state, events, legs + (leg,)

    def rest(state, events, current, place, kind):
        seconds = {EventKind.BREAK: BREAK_S, EventKind.DAILY_REST: DAILY_REST_S,
                   EventKind.CYCLE_RESTART: CYCLE_RESTART_S}[kind]
        reasons = {EventKind.BREAK: "30-minute driving interruption",
                   EventKind.DAILY_REST: "10-hour daily off-duty reset",
                   EventKind.CYCLE_RESTART: "34-hour cycle restart; aggregate cycle availability"}
        return append(state, events, kind, DutyStatus.OFF, seconds, current, poi=place,
                      reasons=(reasons[kind],))

    def feasible(state, leg):
        return leg.duration_s <= driving_allowance(state) and leg.distance_m + state.distance_since_fuel_m <= FUEL_RANGE_M

    def visit(state: DutyState, current: Location, stage: int, events: tuple[DutyEvent, ...],
              legs: tuple[RoadLeg, ...], current_place: StopPlace | None, stop_count: int):
        nonlocal backtracks
        budget.check()
        remember(events, stage)
        if stage == 2:
            return events, legs
        if stop_count > MAX_STOPS:
            return None
        target = request.pickup_location if stage == 0 else request.dropoff_location
        try:
            leg = baseline[stage] if current == baseline[stage].origin else routing.route(current, target, budget)
        except PlanningProblem as problem:
            if problem.code == "ROUTE_UNREACHABLE":
                return None
            raise

        # Try the mandatory waypoint first. The recursive proof includes its service and its exit.
        if feasible(state, leg):
            next_state, next_events, next_legs = drive(state, events, legs, leg)
            next_state, next_events = append(next_state, next_events,
                                            EventKind.PICKUP if stage == 0 else EventKind.DROPOFF,
                                            DutyStatus.ON, SERVICE_S, target,
                                            reasons=("One hour loading" if stage == 0 else "One hour unloading",))
            next_place = current_place if current.coordinate == target.coordinate else None
            answer = visit(next_state, target, stage + 1, next_events, next_legs, next_place, stop_count)
            if answer is not None:
                return answer

        allowance = driving_allowance(state)
        distance_left = FUEL_RANGE_M - state.distance_since_fuel_m
        boundary = boundary_elapsed(leg, allowance, distance_left)
        needs_fuel = leg.distance_m > distance_left and boundary_elapsed(leg, leg.duration_s, distance_left) <= allowance
        window_used = 0 if state.window_started_at is None else int((state.now - state.window_started_at).total_seconds())
        cycle_left = CYCLE_S - state.cycle_used_s
        needs_cycle = cycle_left <= allowance
        needs_daily = min(DAILY_DRIVE_S - state.daily_drive_s, DRIVING_WINDOW_S - window_used) <= allowance
        # If arrival/service was tried and its exit failed, an earlier reset is a valid alternative.
        arrival_dead_end = feasible(state, leg)
        if arrival_dead_end and stage == 0:
            needs_cycle = state.cycle_used_s + leg.duration_s + SERVICE_S >= CYCLE_S
            needs_daily = not needs_cycle
        needs_long = (needs_cycle or needs_daily) and not (needs_fuel and boundary < allowance)
        if needs_fuel and boundary < allowance:
            # Fuel is the next constraint. Prove that a later rest site is reachable after fueling.
            needs_cycle = needs_daily = False

        # A verified current stopping place can host an immediate needed reset/refuel.
        can_wait = current.coordinate == request.current_location.coordinate
        current_rest = current_place is not None and current_place.supports_long_rest
        if stop_count < MAX_STOPS:
            if current_place and current_place.supports_fuel and state.distance_since_fuel_m > 0 and leg.distance_m > distance_left:
                fueled, fuel_events = append(state, events, EventKind.FUEL, DutyStatus.ON, FUEL_S,
                                            current, poi=current_place, reasons=("Fuel before the 1,000-mile limit",))
                answer = visit(fueled, current, stage, fuel_events, legs, current_place, stop_count + 1)
                if answer is not None:
                    return answer
            if (allowance == 0 or arrival_dead_end or (needs_cycle and can_wait)) and (current_rest or can_wait):
                kind = EventKind.CYCLE_RESTART if needs_cycle and state.cycle_used_s > 0 else (
                    EventKind.DAILY_REST if needs_daily and state.window_started_at is not None else EventKind.BREAK)
                if not (kind == EventKind.BREAK and state.break_drive_s == 0):
                    reset, reset_events = rest(state, events, current, current_place, kind)
                    answer = visit(reset, current, stage, reset_events, legs, current_place, stop_count + 1)
                    if answer is not None:
                        return answer

        if boundary > 0 and stop_count < MAX_STOPS:
            anchors = tuple(point_at_elapsed(leg, max(0, int(boundary * ratio)))
                            for ratio in (.98, .88, .75, .6, .4, .15))
            candidates = stops.find_candidates(StopSearch(anchors, 2000, needs_fuel, needs_long), budget)
            candidates = tuple(place for place in candidates if place.location.coordinate != current.coordinate)
            progress = {place.id: projected_progress(leg, place) for place in candidates}
            ranked = rank_candidates(candidates, needs_fuel, needs_long, progress, {})[:5]
            matrix = routing.matrix(current, tuple(place.location for place in ranked), budget)
            estimates = {place.id: estimate[1] for place, estimate in zip(ranked, matrix) if estimate is not None}
            ranked = rank_candidates(tuple(place for place, estimate in zip(ranked, matrix)
                                           if estimate is not None and estimate[1] <= allowance and estimate[0] <= distance_left),
                                      needs_fuel, needs_long, progress, estimates)
            for place in ranked[:3]:
                try:
                    approach = routing.route(current, place.location, budget)
                    exit_leg = routing.route(place.location, target, budget)
                except PlanningProblem as problem:
                    if problem.code == "ROUTE_UNREACHABLE":
                        continue
                    raise
                if approach.duration_s <= 0 or not feasible(state, approach):
                    continue
                stopped, stop_events, stop_legs = drive(state, events, legs, approach)
                add_fuel = place.supports_fuel and (needs_fuel or
                    exit_leg.distance_m + stopped.distance_since_fuel_m > FUEL_RANGE_M)
                if add_fuel:
                    stopped, stop_events = append(stopped, stop_events, EventKind.FUEL, DutyStatus.ON, FUEL_S,
                                                  place.location, poi=place,
                                                  reasons=("Fuel before the 1,000-mile limit; qualifies as a driving interruption",))
                choices = []
                if needs_cycle or stopped.cycle_used_s >= CYCLE_S:
                    if place.supports_long_rest:
                        choices.append(EventKind.CYCLE_RESTART)
                elif needs_daily:
                    if place.supports_long_rest:
                        choices.append(EventKind.DAILY_REST)
                elif not add_fuel:
                    choices.append(EventKind.BREAK)
                else:
                    choices.append(None)
                # A short stop may leave the following pickup/exit unreachable; try an early reset there.
                if place.supports_long_rest:
                    if EventKind.DAILY_REST not in choices and EventKind.CYCLE_RESTART not in choices:
                        choices.append(EventKind.DAILY_REST)
                    if stopped.cycle_used_s > 0 and EventKind.CYCLE_RESTART not in choices:
                        choices.append(EventKind.CYCLE_RESTART)
                for kind in choices:
                    if backtracks > 3:
                        break
                    next_state, next_events = (stopped, stop_events) if kind is None else rest(
                        stopped, stop_events, place.location, place, kind)
                    answer = visit(next_state, place.location, stage, next_events, stop_legs, place, stop_count + 1)
                    if answer is not None:
                        return answer
                    backtracks += 1

        # The departure site is assumed to permit waiting; never assume this at a pickup or arbitrary roadside point.
        if can_wait and state.cycle_used_s > 0 and stop_count < MAX_STOPS and not needs_cycle:
            reset, reset_events = rest(state, events, current, current_place, EventKind.CYCLE_RESTART)
            return visit(reset, current, stage, reset_events, legs, current_place, stop_count + 1)
        return None

    try:
        answer = visit(initial_state(request), request.current_location, 0, (), (), None, 0)
    except PlanningProblem as problem:
        problem.safe_prefix = best_prefix
        raise
    if answer is None:
        raise PlanningProblem("NO_FEASIBLE_STOP_FOUND",
                              "No feasible sequence of truck stops was found in the available map data and search budget.",
                              safe_prefix=best_prefix)
    events, legs = answer
    issues = audit_timeline(request, events)
    if issues:
        raise PlanningProblem("TIMELINE_AUDIT_FAILED", "The computed schedule failed its independent duty audit.", 503)
    unique_legs = tuple({leg.id: leg for leg in legs}.values())
    return ScheduledTrip(request, unique_legs, events, (
        "Vehicle dimensions and live parking availability have not been checked.",
        "Cycle availability is conservatively accumulated until a 34-hour restart; prior daily recap records were not supplied.",
    ))
