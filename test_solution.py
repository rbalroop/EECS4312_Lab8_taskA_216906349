## Student Name: Richard Balroop
## Student ID: 216906349

import pytest
from datetime import date, datetime, time, timedelta

from solution import (
    InfeasibleSchedule,
    TimeWindow,
    BusyInterval,
    suggest_slots,
)


# =========================================================
# Helpers
# =========================================================

def combine(d, t):
    return datetime.combine(d, t)


def overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def extract_all_slots(result):
    slots = []
    if result.suggested:
        slots.append(result.suggested)
    slots.extend(result.alternatives)
    return slots


# =========================================================
# A-Series General Behaviour Tests
# =========================================================

# Covers C11, AC11
def test_a1_no_busy_simple_slots():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(12,0)),
        [],
        timedelta(minutes=30),
        n=3
    )

    slots = extract_all_slots(res)

    assert len(slots) > 0
    assert slots[0].start_time >= time(9,0)


# Covers C9, AC9
def test_a2_deterministic_same_inputs_same_outputs():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(10,0),time(10,30)),
        BusyInterval(time(13,0),time(14,0))
    ]

    r1 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), busy, timedelta(minutes=30), n=10)
    r2 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), busy, timedelta(minutes=30), n=10)

    assert extract_all_slots(r1) == extract_all_slots(r2)


# Covers C3, AC3; C11, AC11
def test_a3_overlapping_and_unsorted_busy_intervals_handled():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(10,30),time(11,0)),
        BusyInterval(time(10,0),time(10,45)),
        BusyInterval(time(9,30),time(9,45))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=15),
        n=8
    )

    slots = extract_all_slots(res)

    for s in slots:
        start = combine(day,s.start_time)
        end = combine(day,s.end_time)

        for b in busy:
            b_start = combine(day,b.start)
            b_end = combine(day,b.end)

            assert not overlaps(start,end,b_start,b_end)


# Covers C5, AC5
def test_a4_candidate_window_respected():
    day = date(2026,2,24)

    candidate = TimeWindow(time(13,0),time(15,0))

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=30),
        n=5,
        candidate_window=candidate
    )

    for s in extract_all_slots(res):
        assert candidate.start <= s.start_time


# Covers C4, AC4
def test_a5_buffer_eliminates_small_gaps():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,30),time(9,50)),
        BusyInterval(time(10,10),time(10,30))
    ]

    r1 = suggest_slots(
        day,
        TimeWindow(time(9,0),time(11,0)),
        busy,
        timedelta(minutes=20),
        n=10
    )

    r2 = suggest_slots(
        day,
        TimeWindow(time(9,0),time(11,0)),
        busy,
        timedelta(minutes=20),
        n=10,
        buffer=timedelta(minutes=5)
    )

    assert len(extract_all_slots(r2)) <= len(extract_all_slots(r1))


# =========================================================
# Constraint Tests C1–C17
# =========================================================

# Covers C1, AC1
def test_c1_one_minute_granularity_returns_consecutive_valid_slots():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(13,0),time(15,0)),
        [],
        timedelta(hours=1),
        n=5
    )

    slots = extract_all_slots(res)

    for i in range(len(slots)-1):
        t1 = combine(day,slots[i].start_time)
        t2 = combine(day,slots[i+1].start_time)
        assert (t2 - t1) == timedelta(minutes=1)


# Covers C2, AC2
def test_c2_reject_working_window_longer_than_24_hours():
    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            date(2026,2,24),
            TimeWindow(time(0,0),time(0,0)),
            [],
            timedelta(minutes=30),
            n=5
        )


# Covers C3, AC3
def test_c3_returned_slots_do_not_overlap_unavailable_intervals():
    day = date(2026,2,24)

    busy = [BusyInterval(time(10,0),time(10,30))]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=10
    )

    for s in extract_all_slots(res):
        start = combine(day,s.start_time)
        end = combine(day,s.end_time)

        for b in busy:
            assert not overlaps(start,end,combine(day,b.start),combine(day,b.end))


# Covers C4, AC4
def test_c4_buffer_eliminates_slots_in_too_small_gap():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,30),time(9,50)),
        BusyInterval(time(10,10),time(10,30))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(11,0)),
        busy,
        timedelta(minutes=20),
        n=10,
        buffer=timedelta(minutes=5)
    )

    assert all(s.start_time != time(9,50) for s in extract_all_slots(res))


# Covers C5, AC5
def test_c5_returned_slots_fit_inside_preferred_time_window():
    day = date(2026,2,24)

    candidate = TimeWindow(time(13,0),time(15,0))

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=30),
        n=10,
        candidate_window=candidate
    )

    for s in extract_all_slots(res):
        start = s.start_time
        end = (combine(day,start)+timedelta(minutes=30)).time()

        assert start >= candidate.start
        assert end <= candidate.end


# Covers C6, AC6
def test_c6_returned_slots_are_chronological():
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(12,0)),
        [],
        timedelta(minutes=30),
        n=10
    )

    starts = [s.start_time for s in extract_all_slots(res)]

    assert starts == sorted(starts)


# Covers C6, AC6; C8, AC8
def test_c6_first_n_returned_slots_preserve_chronological_order():
    day = date(2026,2,24)

    r1 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), [], timedelta(minutes=30), n=3)
    r2 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), [], timedelta(minutes=30), n=100)

    assert extract_all_slots(r1) == extract_all_slots(r2)[:3]


# Covers C7, AC7
def test_c7_reject_overnight_working_window():
    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            date(2026,2,24),
            TimeWindow(time(22,0),time(6,0)),
            [],
            timedelta(minutes=30),
            n=5
        )


# Covers C8, AC8
def test_c8_total_returned_slots_do_not_exceed_requested_n():
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=30),
        n=3
    )

    assert len(extract_all_slots(res)) <= 3


# Covers C9, AC9
def test_c9_identical_inputs_produce_same_valid_slots_and_order():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(10,0),time(11,0)),
        BusyInterval(time(13,0),time(14,0))
    ]

    r1 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), busy, timedelta(minutes=30), n=10)
    r2 = suggest_slots(day, TimeWindow(time(9,0),time(17,0)), list(reversed(busy)), timedelta(minutes=30), n=10)

    assert extract_all_slots(r1) == extract_all_slots(r2)


# Covers C10, AC10
def test_c10_returned_valid_slots_are_unique():
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=30),
        n=50
    )

    starts = [s.start_time for s in extract_all_slots(res)]

    assert len(starts) == len(set(starts))


# Covers C11, AC11
def test_c11_all_returned_slots_satisfy_validity_constraints():
    day = date(2026,2,24)

    busy = [BusyInterval(time(10,0),time(10,30))]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=10
    )

    for s in extract_all_slots(res):
        start = combine(day,s.start_time)
        end = combine(day,s.end_time)

        for b in busy:
            assert not overlaps(start,end,combine(day,b.start),combine(day,b.end))


# =========================================================
# Edge Cases EC1–EC21
# =========================================================

# Covers C4, AC4
def test_ec1_no_gap_long_enough_for_duration():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,0),time(9,20)),
        BusyInterval(time(9,30),time(10,0))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(10,0)),
        busy,
        timedelta(minutes=15),
        n=10
    )

    assert extract_all_slots(res) == []


# Covers C4, AC4
def test_ec2_buffer_eliminates_exact_fit_gap():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,0),time(9,20)),
        BusyInterval(time(9,40),time(10,0))
    ]

    r1 = suggest_slots(day, TimeWindow(time(9,0),time(10,0)), busy, timedelta(minutes=20), n=5)
    assert any(s.start_time == time(9,20) for s in extract_all_slots(r1))

    r2 = suggest_slots(
        day,
        TimeWindow(time(9,0),time(10,0)),
        busy,
        timedelta(minutes=20),
        n=5,
        buffer=timedelta(minutes=5)
    )

    assert extract_all_slots(r2) == []


# Covers C3, AC3; C4, AC4
def test_ec3_adjacent_busy_intervals_no_false_gap():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,30),time(10,0)),
        BusyInterval(time(10,0),time(10,30))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(11,0)),
        busy,
        timedelta(minutes=15),
        n=10
    )

    assert all(s.start_time != time(10,0) for s in extract_all_slots(res))


# Covers C3, AC3; C6, AC6
def test_ec4_overlapping_and_unsorted_busy_intervals():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(10,30),time(11,30)),
        BusyInterval(time(10,0),time(10,45)),
        BusyInterval(time(9,45),time(10,15))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=10
    )

    for s in extract_all_slots(res):
        start = combine(day,s.start_time)
        end = combine(day,s.end_time)

        for b in busy:
            assert not overlaps(start,end,combine(day,b.start),combine(day,b.end))


# Covers C5, AC5
def test_ec5_slot_partially_outside_candidate_window_invalid():
    day = date(2026,2,24)

    candidate = TimeWindow(time(13,0),time(14,0))

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=45),
        n=10,
        candidate_window=candidate
    )

    for s in extract_all_slots(res):
        end = (combine(day,s.start_time)+timedelta(minutes=45)).time()
        assert end <= candidate.end


# Covers C7, AC7
def test_ec6_reject_cross_midnight_working_day():
    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            date(2026,2,24),
            TimeWindow(time(22,0),time(6,0)),
            [],
            timedelta(minutes=30),
            n=5
        )


# Covers C2, AC2
def test_ec7_reject_working_day_exceeds_24_hours():
    with pytest.raises(InfeasibleSchedule):
        suggest_slots(
            date(2026,2,24),
            TimeWindow(time(0,0),time(0,0)),
            [],
            timedelta(minutes=30),
            n=5
        )


# Covers C1, AC1
def test_ec8_consecutive_start_times_one_minute_apart():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(13,0),time(15,0)),
        [],
        timedelta(hours=1),
        n=3
    )

    slots = extract_all_slots(res)

    assert len(slots) >= 2

    t1 = combine(day,slots[0].start_time)
    t2 = combine(day,slots[1].start_time)

    assert (t2 - t1) == timedelta(minutes=1)


# Covers C8, AC8
def test_ec9_request_more_than_exist_returns_only_available():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(9,25)),
        [],
        timedelta(minutes=20),
        n=10
    )

    assert len(extract_all_slots(res)) == 6


# Covers C12, partial AC12
def test_ec10_zero_valid_suggestions_returns_empty():
    day = date(2026,2,24)

    busy = [BusyInterval(time(9,0),time(9,30))]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(9,30)),
        busy,
        timedelta(minutes=15),
        n=5
    )

    assert extract_all_slots(res) == []


# Covers C8, AC8
def test_ec11_truncate_when_more_valid_than_requested():
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(12,0)),
        [],
        timedelta(minutes=30),
        n=3
    )

    assert len(extract_all_slots(res)) == 3


# Covers C8, AC8
def test_ec12_return_only_existing_when_fewer_than_requested():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(9,20)),
        [],
        timedelta(minutes=15),
        n=10
    )

    assert len(extract_all_slots(res)) == 6


# =========================================================
# Normal Tests NT1–NT10
# =========================================================

# Covers C11, AC11
def test_nt1_duration_equals_working_window():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0),time(10,0)),
        [],
        timedelta(hours=1),
        n=5
    )

    slots = extract_all_slots(res)

    assert len(slots) == 1
    assert slots[0].start_time == time(9,0)


# Covers C17, partial AC19
def test_nt2_duration_larger_than_working_window():
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(10,0)),
        [],
        timedelta(hours=2),
        n=5
    )

    assert extract_all_slots(res) == []


# Covers C17, partial AC19
def test_nt3_busy_exactly_matches_working_window():
    busy = [BusyInterval(time(9,0),time(12,0))]

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=5
    )

    assert extract_all_slots(res) == []


# Covers C3, AC3; C11, AC11
def test_nt4_busy_ends_exactly_at_working_start():
    busy = [BusyInterval(time(8,0),time(9,0))]

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=3
    )

    assert extract_all_slots(res)[0].start_time == time(9,0)


# Covers C3, AC3; C11, AC11
def test_nt5_busy_starts_exactly_at_working_end():
    busy = [BusyInterval(time(12,0),time(13,0))]

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(12,0)),
        busy,
        timedelta(minutes=30),
        n=3
    )

    assert extract_all_slots(res)[-1].start_time <= time(11,30)


# Covers C4, AC4
def test_nt6_buffer_pushes_slot_to_boundary():
    busy = [BusyInterval(time(10,0),time(10,30))]

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(11,0)),
        busy,
        timedelta(minutes=30),
        n=10,
        buffer=timedelta(minutes=30)
    )

    assert all(
        not (time(9,30) <= s.start_time < time(11,0))
        for s in extract_all_slots(res)
    )


# Covers C5, partial AC5
def test_nt7_candidate_window_smaller_than_duration():
    candidate = TimeWindow(time(13,0),time(13,15))

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(minutes=30),
        n=5,
        candidate_window=candidate
    )

    assert extract_all_slots(res) == []


# Covers C5, AC5
def test_nt8_candidate_window_exact_fit():
    candidate = TimeWindow(time(13,0),time(14,0))

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        [],
        timedelta(hours=1),
        n=5,
        candidate_window=candidate
    )

    slots = extract_all_slots(res)

    assert len(slots) == 1
    assert slots[0].start_time == time(13,0)


# Covers C11, AC11
def test_nt9_multiple_disjoint_free_regions():
    busy = [
        BusyInterval(time(10,0),time(11,0)),
        BusyInterval(time(12,0),time(13,0))
    ]

    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(15,0)),
        busy,
        timedelta(minutes=30),
        n=200
    )

    slots = extract_all_slots(res)

    assert any(s.start_time < time(10,0) for s in slots)
    assert any(s.start_time >= time(13,0) for s in slots)


# Covers C9, AC9
def test_nt10_determinism_under_busy_permutations():
    busy1 = [
        BusyInterval(time(10,0),time(11,0)),
        BusyInterval(time(13,0),time(14,0))
    ]

    busy2 = list(reversed(busy1))

    r1 = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        busy1,
        timedelta(minutes=30),
        n=10
    )

    r2 = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0),time(17,0)),
        busy2,
        timedelta(minutes=30),
        n=10
    )

    assert extract_all_slots(r1) == extract_all_slots(r2)


# Covers C11, AC11
def test_ec13_single_minute_working_window():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(9,1)),
        [],
        timedelta(minutes=1),
        n=5
    )

    slots = extract_all_slots(res)

    assert len(slots) == 1
    assert slots[0].start_time == time(9,0)


# Covers C11, AC11
def test_ec14_busy_interval_outside_working_hours():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(7,0), time(8,0)),
        BusyInterval(time(18,0), time(19,0))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(12,0)),
        busy,
        timedelta(minutes=30),
        n=5
    )

    slots = extract_all_slots(res)

    assert slots[0].start_time == time(9,0)


# Covers C3, AC3; C11, AC11
def test_ec15_busy_interval_partially_overlaps_working_start():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(8,30), time(9,15))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(10,0)),
        busy,
        timedelta(minutes=15),
        n=5
    )

    slots = extract_all_slots(res)

    assert all(s.start_time >= time(9,15) for s in slots)


# Covers C3, AC3; C11, AC11
def test_ec16_busy_interval_partially_overlaps_working_end():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(9,45), time(10,30))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(10,0)),
        busy,
        timedelta(minutes=15),
        n=10
    )

    slots = extract_all_slots(res)

    assert all(s.start_time < time(9,45) for s in slots)


# Covers C4, AC4
def test_ec17_busy_intervals_merge_after_buffer():
    day = date(2026,2,24)

    busy = [
        BusyInterval(time(10,0), time(10,30)),
        BusyInterval(time(10,35), time(11,0))
    ]

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(12,0)),
        busy,
        timedelta(minutes=20),
        n=10,
        buffer=timedelta(minutes=10)
    )

    slots = extract_all_slots(res)

    assert all(not (time(10,0) <= s.start_time < time(11,0)) for s in slots)


# Covers C8, AC8
def test_ec18_large_n_does_not_break_algorithm():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(17,0)),
        [],
        timedelta(minutes=30),
        n=1000
    )

    slots = extract_all_slots(res)

    assert len(slots) <= 1000


# Covers C1, AC1; C11, AC11
def test_ec19_duration_equals_one_minute():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(9,10)),
        [],
        timedelta(minutes=1),
        n=20
    )

    slots = extract_all_slots(res)

    assert len(slots) == 10


# Covers C5, AC5
def test_ec20_candidate_window_equal_to_working_window():
    day = date(2026,2,24)

    working = TimeWindow(time(9,0), time(12,0))

    res = suggest_slots(
        day,
        working,
        [],
        timedelta(minutes=30),
        n=10,
        candidate_window=working
    )

    slots = extract_all_slots(res)

    assert slots[0].start_time == time(9,0)


# Covers C11, AC11
def test_ec21_empty_busy_list_and_large_duration():
    day = date(2026,2,24)

    res = suggest_slots(
        day,
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(hours=2),
        n=10
    )

    slots = extract_all_slots(res)

    assert slots[0].start_time == time(9,0)


# Covers C14, AC14
def test_persona_suggested_not_in_alternatives():
    """Suggested slot should not appear in alternatives."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=5
    )

    assert res.suggested not in res.alternatives


# Covers C14, AC14; C8, AC8
def test_persona_n_equals_one_returns_only_suggested():
    """When n=1 only the suggested slot should be returned."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=1
    )

    assert res.suggested is not None
    assert res.alternatives == []


# Covers C13, AC13
def test_persona_explanations_enabled_returns_explanations():
    """Explanations should be returned when requested."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=3,
        provide_explanations=True
    )

    assert res.explanations is not None


# Covers C15, AC17
def test_persona_explanations_disabled_returns_none():
    """Explanations should be suppressed when disabled."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=3,
        provide_explanations=False
    )

    assert res.explanations is None


# Covers C13, AC13
def test_persona_explanations_match_number_of_slots():
    """Each slot should have a corresponding explanation."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=4,
        provide_explanations=True
    )

    slots = extract_all_slots(res)

    assert len(res.explanations) == len(slots) # type: ignore


# Covers C13, AC13
def test_persona_suggested_slot_has_explanation():
    """Suggested slot should have an explanation when explanations enabled."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=3,
        provide_explanations=True
    )

    assert res.explanations[0] is not None # type: ignore


# Covers C13, AC13
def test_persona_explanations_preserve_slot_order():
    """Explanation order should correspond to slot order."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(11,0)),
        [],
        timedelta(minutes=30),
        n=4,
        provide_explanations=True
    )

    slots = extract_all_slots(res)

    for slot, explanation in zip(slots, res.explanations): # type: ignore
        assert explanation is not None


# Covers C13, AC17; C15, AC17
def test_persona_explanation_toggle_does_not_change_slots():
    """Turning explanations on/off should not change slot results."""
    r1 = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=5,
        provide_explanations=False
    )

    r2 = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(12,0)),
        [],
        timedelta(minutes=30),
        n=5,
        provide_explanations=True
    )

    assert extract_all_slots(r1) == extract_all_slots(r2)


# Covers C12, AC16
def test_persona_no_slot_explanation_when_no_slots_exist():
    """System should explain why no slots exist."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(9,30)),
        [BusyInterval(time(9,0), time(9,30))],
        timedelta(minutes=15),
        n=5,
        provide_explanations=True
    )

    assert res.suggested is None
    assert res.no_slot_explanation is not None


# Covers C12, AC12
def test_persona_no_slot_explanation_exists_even_without_explanations():
    """Failure explanation should still exist even if explanations disabled."""
    res = suggest_slots(
        date(2026,2,24),
        TimeWindow(time(9,0), time(9,30)),
        [BusyInterval(time(9,0), time(9,30))],
        timedelta(minutes=15),
        n=5,
        provide_explanations=False
    )

    assert res.suggested is None
    assert res.no_slot_explanation is not None
