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
from typing import List, Optional


# ---------------- Data Models ----------------

@dataclass(frozen=True)
class TimeWindow:
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    start_time: time
    end_time: time


@dataclass
class SlotExplanation:
    slot: Slot
    explanation: str


@dataclass
class SuggestionResult:
    suggested: Optional[Slot]
    alternatives: List[Slot]
    explanations: Optional[List[SlotExplanation]] = None
    no_slot_explanation: Optional[str] = None


class InfeasibleSchedule(Exception):
    pass


# ---------------- Core Function ----------------

def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    n: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None,
    provide_explanations: bool = False
) -> SuggestionResult:

    # ---------------- Input Validation ----------------

    if working_hours.start >= working_hours.end:
        raise InfeasibleSchedule("C7: Working hours must satisfy start < end.")

    working_length = datetime.combine(day, working_hours.end) - datetime.combine(day, working_hours.start)
    if working_length > timedelta(hours=24):
        raise InfeasibleSchedule("C2: Working window exceeds 24 hours.")

    if duration <= timedelta(0):
        raise InfeasibleSchedule("Meeting duration must be positive.")

    if n < 0:
        raise InfeasibleSchedule("Number of suggestions must be >= 0.")

    if buffer < timedelta(0):
        raise InfeasibleSchedule("Buffer must be >= 0.")

    if candidate_window and candidate_window.start >= candidate_window.end:
        raise InfeasibleSchedule("Preferred window must satisfy start < end.")

    for b in busy_intervals:
        if b.start >= b.end:
            raise InfeasibleSchedule("Busy intervals must satisfy start < end.")

    if n == 0:
        return SuggestionResult(None, [])

    # ---------------- Effective Search Window ----------------

    effective_start = working_hours.start
    effective_end = working_hours.end

    if candidate_window:
        effective_start = max(effective_start, candidate_window.start)
        effective_end = min(effective_end, candidate_window.end)

        if effective_start >= effective_end:
            return SuggestionResult(
                suggested=None,
                alternatives=[],
                no_slot_explanation="C5: Preferred time window eliminates all availability."
            )

    window_start = datetime.combine(day, effective_start)
    window_end = datetime.combine(day, effective_end)

    # ---------------- Normalize Busy Intervals ----------------

    expanded_busy = []

    for b in busy_intervals:
        start = datetime.combine(day, b.start) - buffer
        end = datetime.combine(day, b.end) + buffer
        expanded_busy.append((start, end))

    expanded_busy.sort(key=lambda x: (x[0], x[1]))

    merged_busy = []

    for start, end in expanded_busy:
        if not merged_busy or start > merged_busy[-1][1]:
            merged_busy.append([start, end])
        else:
            merged_busy[-1][1] = max(merged_busy[-1][1], end)

    # ---------------- Slot Generation ----------------

    step = timedelta(minutes=1)
    slots: List[Slot] = []

    current = window_start

    while current + duration <= window_end and len(slots) < n:
        end = current + duration

        conflict = False

        for busy_start, busy_end in merged_busy:
            if current < busy_end and busy_start < end:
                conflict = True
                break

        if not conflict:
            slots.append(Slot(current.time(), end.time()))

        current += step

    # ---------------- Handle No Slot Case ----------------

    if not slots:
        return SuggestionResult(
            suggested=None,
            alternatives=[],
            no_slot_explanation="C3/C4: No available gap satisfies meeting duration and buffer constraints."
        )

    # ---------------- Partition Suggested / Alternatives ----------------

    suggested = slots[0]
    alternatives = slots[1:]

    explanations = None

    if provide_explanations:
        explanations = []

        for s in slots:
            explanations.append(
                SlotExplanation(
                    slot=s,
                    explanation="Slot satisfies C3 (no conflict with busy intervals), "
                                "C4 (buffer respected), and C5 (within preferred window if specified)."
                )
            )

    return SuggestionResult(
        suggested=suggested,
        alternatives=alternatives,
        explanations=explanations
    )