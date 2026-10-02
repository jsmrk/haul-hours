from planner.constants import BREAK_DRIVE_S, CYCLE_S, DAILY_DRIVE_S, DRIVING_WINDOW_S
from planner.duty.state import DutyState


def driving_allowance(state: DutyState) -> int:
    window_used = 0 if state.window_started_at is None else int((state.now - state.window_started_at).total_seconds())
    return max(0, min(DAILY_DRIVE_S - state.daily_drive_s, BREAK_DRIVE_S - state.break_drive_s,
                      DRIVING_WINDOW_S - window_used, CYCLE_S - state.cycle_used_s))
