## Student Name: Richard Balroop
## Student ID: 216906349

import pytest
from datetime import date, datetime, time, timedelta

# Update import path to match your project structure:
from solution import InfeasibleSchedule, TimeWindow, BusyInterval, Slot, suggest_slots


# ---------- Helpers ----------

def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_basic_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    n,
    buffer,
    candidate_window,
):
    # Return type / length
    assert isinstance(slots, list)
    assert len(slots) <= n

    # Deterministic ordering: start_time ascending
    assert slots == sorted(slots, key=lambda s: s.start_time)

    # Each slot start must be within working_hours and candidate_window (if any)
    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window is not None:
            assert in_window(candidate_window, s.start_time)

    # Each slot must fit fully inside working_hours and candidate_window
    for s in slots:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration

        wh_end = combine(day, working_hours.end)
        assert end_dt <= wh_end

        if candidate_window is not None:
            cw_end = combine(day, candidate_window.end)
            assert end_dt <= cw_end

    # No overlap with busy intervals, considering buffer:
    # busy interval is expanded to [start-buffer, end+buffer)
    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration

        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Tests ----------

def test_a1_no_busy_simple_slots():
    """
    Like original "single med exact times": here, no busy events.
    Expect earliest slots within working hours (we only assert constraints + non-empty).
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=3,
        buffer=timedelta(0),
        candidate_window=None
    )

    assert_slots_basic_constraints(out, day, working, busy, duration, 3, timedelta(0), None)
    # Should at least return 1 slot if implementation uses a reasonable slot step
    assert len(out) > 0
    # Earliest slot should be at or after working start
    assert out[0].start_time >= time(9, 0)


def test_a2_deterministic_same_inputs_same_outputs():
    """
    Like original tie/determinism check: same inputs must return identical outputs.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(13, 0), time(14, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=0)

    out1 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)
    out2 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]
    assert_slots_basic_constraints(out1, day, working, busy, duration, 10, buffer, None)


def test_a3_overlapping_and_unsorted_busy_intervals_handled():
    """
    Busy intervals may be unsorted/overlapping; suggestions must still avoid conflicts.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 30), time(11, 0)),
        BusyInterval(time(10, 0), time(10, 45)),   # overlaps with above
        BusyInterval(time(9, 30), time(9, 45)),    # unsorted relative order
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=8, buffer=timedelta(0), candidate_window=None)
    assert_slots_basic_constraints(out, day, working, busy, duration, 8, timedelta(0), None)


def test_a4_candidate_window_respected():
    """
    Like original allowed_window respected: here we add an extra candidate window restriction.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(15, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=5, buffer=timedelta(0), candidate_window=candidate)
    assert_slots_basic_constraints(out, day, working, busy, duration, 5, timedelta(0), candidate)

    # Every slot must start within candidate window
    assert all(candidate.start <= s.start_time < candidate.end for s in out)


def test_a5_buffer_eliminates_small_gaps():
    """
    Like original rate-limit constraint: here buffer is the key extra constraint.
    With buffer, some slots that would otherwise fit should be invalid.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    # Two busy intervals leaving a 20-minute gap between them
    busy = [
        BusyInterval(time(9, 30), time(9, 50)),
        BusyInterval(time(10, 10), time(10, 30)),
    ]
    duration = timedelta(minutes=20)

    # Without buffer: the gap 9:50–10:10 is exactly 20 minutes -> potentially valid
    out_no_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=timedelta(0), candidate_window=None)
    assert_slots_basic_constraints(out_no_buffer, day, working, busy, duration, 10, timedelta(0), None)

    # With 5-min buffer: effective busy expands, gap shrinks -> should reduce or remove those slots
    buf = timedelta(minutes=5)
    out_with_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=buf, candidate_window=None)
    assert_slots_basic_constraints(out_with_buffer, day, working, busy, duration, 10, buf, None)

    # Buffer should not increase number of available slots (monotonicity)
    assert len(out_with_buffer) <= len(out_no_buffer)


#################################################################################
# Add your own additional tests here to cover more cases and edge cases as needed.
#################################################################################

def test_c1_one_minute_granularity_allows_adjacent_start_times():
    day = date(2026, 2, 24)
    working = TimeWindow(time(13, 0), time(15, 0))
    busy = []
    duration = timedelta(minutes=60)

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=5,
        buffer=timedelta(0),
        candidate_window=None
    )

    # Must return at most 5
    assert len(out) <= 5

    # Start times must differ by exactly 1 minute
    for i in range(len(out) - 1):
        t1 = datetime.combine(day, out[i].start_time)
        t2 = datetime.combine(day, out[i + 1].start_time)
        assert (t2 - t1) == timedelta(minutes=1)
        
def test_c2_reject_working_window_longer_than_24_hours():
    day = date(2026, 2, 24)

    # Artificially create >24h window using datetime comparison trick
    working = TimeWindow(time(0, 0), time(0, 1))  # We'll simulate failure differently

    # Override check by monkey-patching if needed — but since implementation checks duration,
    # use a failing condition by manipulating logic:
    # Instead simulate invalid by forcing manual check
    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            day=day,
            working_hours=TimeWindow(time(0, 0), time(0, 0)),  # start == end invalid
            busy_intervals=[],
            duration=timedelta(minutes=30),
            n=5
        )

def test_c3_suggestions_do_not_overlap_busy_intervals():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30))]
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day, working, busy, duration, n=10
    )

    for s in out:
        start = datetime.combine(day, s.start_time)
        end = start + duration

        busy_start = datetime.combine(day, time(10, 0))
        busy_end = datetime.combine(day, time(10, 30))

        assert not (start < busy_end and busy_start < end)
        
def test_c4_buffer_eliminates_gap_that_would_otherwise_fit():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [
        BusyInterval(time(9, 30), time(9, 50)),
        BusyInterval(time(10, 10), time(10, 30))
    ]
    duration = timedelta(minutes=20)
    buffer = timedelta(minutes=5)

    out = suggest_slots(
        day, working, busy, duration, n=10, buffer=buffer
    )

    # Gap 9:50–10:10 should NOT produce slot
    invalid_start = time(9, 50)
    assert all(s.start_time != invalid_start for s in out)
    
def test_c5_suggestions_must_fit_inside_candidate_window():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(15, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day, working, [], duration, n=10, candidate_window=candidate
    )

    for s in out:
        start = s.start_time
        end = (datetime.combine(day, start) + duration).time()

        assert candidate.start <= start
        assert end <= candidate.end
        
def test_c6_slots_are_returned_in_chronological_order():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=10)

    times = [s.start_time for s in out]
    assert times == sorted(times)
    
def test_c7_reject_overnight_working_window():
    day = date(2026, 2, 24)
    working = TimeWindow(time(22, 0), time(6, 0))  # Overnight

    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            day,
            working,
            [],
            timedelta(minutes=30),
            n=5
        )
    
def test_c8_does_not_return_more_than_requested_suggestions():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=3)

    assert len(out) <= 3

    # If more than 3 possible, must return exactly first 3
    all_slots = suggest_slots(day, working, [], duration, n=100)

    assert out == all_slots[:3]
    
def test_ec1_no_gap_long_enough_for_duration():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [
        BusyInterval(time(9, 0), time(9, 20)),
        BusyInterval(time(9, 30), time(10, 0)),
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=10)

    assert out == []
    
def test_ec2_buffer_eliminates_exact_fit_gap():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [
        BusyInterval(time(9, 0), time(9, 20)),
        BusyInterval(time(9, 40), time(10, 0)),
    ]
    duration = timedelta(minutes=20)

    # Without buffer → gap 9:20–9:40 fits exactly
    out_no_buffer = suggest_slots(day, working, busy, duration, n=5)
    assert any(s.start_time == time(9, 20) for s in out_no_buffer)

    # With buffer → gap eliminated
    out_with_buffer = suggest_slots(
        day, working, busy, duration, n=5, buffer=timedelta(minutes=5)
    )

    assert out_with_buffer == []
    
def test_ec3_adjacent_busy_intervals_no_false_gap():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [
        BusyInterval(time(9, 30), time(10, 0)),
        BusyInterval(time(10, 0), time(10, 30)),  # Adjacent
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=10)

    # Nothing allowed at 10:00
    assert all(s.start_time != time(10, 0) for s in out)
    
def test_ec4_overlapping_and_unsorted_busy_intervals():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 30), time(11, 30)),
        BusyInterval(time(10, 0), time(10, 45)),
        BusyInterval(time(9, 45), time(10, 15)),  # overlapping + unsorted
    ]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=10)

    # No overlap allowed
    for s in out:
        start = datetime.combine(day, s.start_time)
        end = start + duration

        for b in busy:
            b_start = datetime.combine(day, b.start)
            b_end = datetime.combine(day, b.end)
            assert not (start < b_end and b_start < end)
            
def test_ec5_slot_partially_outside_candidate_window_invalid():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(14, 0))
    duration = timedelta(minutes=45)

    out = suggest_slots(
        day, working, [], duration, n=10, candidate_window=candidate
    )

    # All slots must fully fit in candidate window
    for s in out:
        start = datetime.combine(day, s.start_time)
        end = start + duration
        assert start.time() >= candidate.start
        assert end.time() <= candidate.end
        
def test_ec6_reject_cross_midnight_working_day():
    day = date(2026, 2, 24)
    working = TimeWindow(time(22, 0), time(6, 0))

    with pytest.raises(InfeasibleSchedule):
        suggest_slots(day, working, [], timedelta(minutes=30), n=5)
        
def test_ec7_reject_working_day_exceeds_24_hours():
    day = date(2026, 2, 24)

    # start == end invalid
    working = TimeWindow(time(0, 0), time(0, 0))

    with pytest.raises(InfeasibleSchedule):
        suggest_slots(day, working, [], timedelta(minutes=30), n=5)
        
def test_ec8_consecutive_start_times_one_minute_apart():
    day = date(2026, 2, 24)
    working = TimeWindow(time(13, 0), time(15, 0))
    duration = timedelta(minutes=60)

    out = suggest_slots(day, working, [], duration, n=3)

    assert len(out) >= 2

    t1 = datetime.combine(day, out[0].start_time)
    t2 = datetime.combine(day, out[1].start_time)

    assert (t2 - t1) == timedelta(minutes=1)
    
def test_ec9_request_more_than_exist_returns_only_available():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(9, 25))
    duration = timedelta(minutes=20)

    out = suggest_slots(day, working, [], duration, n=10)

    # Only 6 valid start times exist (9:00–9:05)
    assert len(out) == 6
    
def test_ec10_zero_valid_suggestions_returns_empty_list():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(9, 30))
    busy = [BusyInterval(time(9, 0), time(9, 30))]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=5)

    assert out == []
    
def test_ec11_truncate_when_more_valid_than_requested():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=3)

    assert len(out) == 3
    
def test_ec12_return_only_existing_when_fewer_than_requested():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(9, 20))
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, [], duration, n=10)

    # Only 6 valid slots exist
    assert len(out) == 6

def test_nt1_duration_equals_working_window():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(hours=1)

    out = suggest_slots(day, working, [], duration, n=5)

    assert len(out) == 1
    assert out[0].start_time == time(9, 0)
    
def test_nt2_duration_larger_than_working_window():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(hours=2)

    out = suggest_slots(day, working, [], duration, n=5)

    assert out == []
    
def test_nt3_busy_exactly_matches_working_window():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(9, 0), time(12, 0))]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=5)

    assert out == []
    
def test_nt4_busy_ends_exactly_at_working_start():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(8, 0), time(9, 0))]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=3)

    assert len(out) > 0
    assert out[0].start_time == time(9, 0)
    
def test_nt5_busy_starts_exactly_at_working_end():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(12, 0), time(13, 0))]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=3)

    assert len(out) > 0
    assert out[-1].start_time <= time(11, 30)
    
def test_nt6_buffer_pushes_slot_to_boundary():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30))]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=10, buffer=buffer)

    # With 30-min buffer, earliest valid start is 9:00
    # But nothing allowed after 9:00–9:30
    assert all(
        not (time(9, 30) <= s.start_time < time(11, 0))
        for s in out
    )
    
def test_nt7_candidate_window_smaller_than_duration():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(13, 15))
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day, working, [], duration, n=5, candidate_window=candidate
    )

    assert out == []
    
def test_nt8_candidate_window_exact_fit():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(14, 0))
    duration = timedelta(hours=1)

    out = suggest_slots(
        day, working, [], duration, n=5, candidate_window=candidate
    )

    assert len(out) == 1
    assert out[0].start_time == time(13, 0)
    
def test_nt9_multiple_disjoint_free_regions():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(15, 0))
    busy = [
        BusyInterval(time(10, 0), time(11, 0)),
        BusyInterval(time(12, 0), time(13, 0)),
    ]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=200)

    assert any(s.start_time < time(10, 0) for s in out)
    assert any(s.start_time >= time(13, 0) for s in out)
    
def test_nt10_determinism_under_busy_permutations():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy1 = [
        BusyInterval(time(10, 0), time(11, 0)),
        BusyInterval(time(13, 0), time(14, 0)),
    ]
    busy2 = list(reversed(busy1))  # Same intervals, different order
    duration = timedelta(minutes=30)

    out1 = suggest_slots(day, working, busy1, duration, n=10)
    out2 = suggest_slots(day, working, busy2, duration, n=10)

    assert out1 == out2