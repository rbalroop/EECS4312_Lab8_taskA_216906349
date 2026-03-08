## Student Name: Richard Balroop
## Student ID: 216906349

"""
Task A: Appointment Timeslot Recommender (Stub)

In this lab, you will design and implement an Appointment Slot Recommender using an LLM assistant
as your primary programming collaborator.

You are asked to implement a Python module that recommends available meeting slots within a
defined working window.

The system must:
  • Accept working hours (start and end time).
  • Accept a list of existing busy intervals.
  • Accept a required meeting duration.
  • Accept an optional buffer time between meetings.
  • Optionally restrict suggestions to a candidate time window.
  • Return chronologically ordered appointment slots that satisfy all constraints.

The system must ensure that:
  • Suggested slots fall within working hours.
  • Suggested slots do not overlap busy intervals.
  • Buffer time is respected when evaluating availability.
  • Output ordering is deterministic under identical inputs.

The module must preserve the following invariants:
  • Returned slots must be at least as long as the required duration.
  • No returned slot may violate buffer constraints.
  • The returned list must reflect the current system state.

The system must correctly handle non-trivial scenarios such as:
  • Adjacent busy intervals.
  • Very small gaps between meetings.
  • Buffers eliminating otherwise valid availability.
  • Overlapping or unsorted busy intervals.
  • A meeting duration longer than any available gap.
  • No availability within the working window.

Output:
  The output consists of the next N valid appointment suggestions in chronological order.
  Behavior must be deterministic under ties (if any).

See the lab handout for full requirements.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import List, Optional, Tuple


# ---------------- Data Models ----------------

@dataclass(frozen=True)
class TimeWindow:
    """
    A daily time window.
    Assumption (unless stated otherwise in handout): non-wrapping window where start < end.
    """
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    """
    A busy interval on the given day.
    Invariant: start < end
    """
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    """
    A recommended appointment slot.

    start_time is a time-of-day within the working window.
    Deterministic ordering: sort by start_time ascending.
    """
    start_time: time


class InfeasibleSchedule(Exception):
    """Raised when no valid slots can be produced (if required by handout)."""
    pass


# ---------------- Core Function ----------------
    
def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    n: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None
) -> List[Slot]:
    """
    Suggest up to the next n valid appointment slots (start times) for the given day.

    Args:
        day: the calendar day for which to suggest slots.
        working_hours: the allowed working window for meetings (start < end).
        busy_intervals: list of busy time intervals (may be overlapping / unsorted).
        duration: required meeting length (must be > 0).
        n: maximum number of slot suggestions to return (n >= 0).
        buffer: optional buffer time required between meetings (buffer >= 0).
        candidate_window: optional extra restriction on suggestions (must lie within this window too).

    Returns:
        A list of Slot objects, sorted by start_time ascending, deterministic under identical inputs.
        If no suitable time slots are available, return an empty list.

    Notes:
        - Suggested slots must fall within working_hours (and candidate_window if provided).
        - Suggested slots must not overlap busy_intervals, considering buffer time.
        - You are free to choose internal representation; inputs use time-of-day.
        - See lab handout for required slot granularity (e.g., 5-min/15-min steps), if any.
    """

    # ---------------- Input Validation ----------------

    if working_hours.start >= working_hours.end:
        raise InfeasibleSchedule("Working hours must satisfy start < end.")

    if duration <= timedelta(0):
        raise InfeasibleSchedule("Meeting duration must be positive.")

    if n < 0:
        raise InfeasibleSchedule("Number of suggestions must be >= 0.")

    if buffer < timedelta(0):
        raise InfeasibleSchedule("Buffer must be >= 0.")

    if candidate_window is not None and candidate_window.start >= candidate_window.end:
        raise InfeasibleSchedule("Candidate window must satisfy start < end.")

    for b in busy_intervals:
        if b.start >= b.end:
            raise InfeasibleSchedule("Each busy interval must satisfy start < end.")

    if n == 0:
        return []

    # ---------------- Effective Search Window ----------------

    effective_start = working_hours.start
    effective_end = working_hours.end

    if candidate_window is not None:
        effective_start = max(effective_start, candidate_window.start)
        effective_end = min(effective_end, candidate_window.end)

        if effective_start >= effective_end:
            return []

    window_start_dt = datetime.combine(day, effective_start)
    window_end_dt = datetime.combine(day, effective_end)

    # ---------------- Normalize Busy Intervals ----------------

    expanded_busy = []
    for b in busy_intervals:
        busy_start = datetime.combine(day, b.start) - buffer
        busy_end = datetime.combine(day, b.end) + buffer
        expanded_busy.append((busy_start, busy_end))

    expanded_busy.sort(key=lambda interval: (interval[0], interval[1]))

    merged_busy = []
    for start_dt, end_dt in expanded_busy:
        if not merged_busy or start_dt > merged_busy[-1][1]:
            merged_busy.append([start_dt, end_dt])
        else:
            merged_busy[-1][1] = max(merged_busy[-1][1], end_dt)

    # ---------------- Generate Slots ----------------

    slots: List[Slot] = []
    step = timedelta(minutes=1)  # Assumed granularity

    current_start = window_start_dt
    while current_start + duration <= window_end_dt and len(slots) < n:
        current_end = current_start + duration

        conflict = False
        for busy_start, busy_end in merged_busy:
            if current_start < busy_end and busy_start < current_end:
                conflict = True
                break

        if not conflict:
            slots.append(Slot(start_time=current_start.time()))

        current_start += step

    return slots