from day1_bdc_reporting_order import (
    classify_exhibit_text,
    previous_quarter_end,
    timestamp_et,
)


def test_obdc_2025q2_scheduling_release_is_not_results():
    text = """
    Blue Owl Capital Corporation Schedules Earnings Release and Quarterly
    Earnings Call to Discuss its Second Quarter Ended June 30, 2025 Financial
    Results. OBDC will release its financial results on August 6, 2025.
    """
    accepted, _, reason = classify_exhibit_text(text)
    assert not accepted
    assert "scheduling" in reason


def test_gbdc_2025q2_scheduling_release_is_not_results():
    text = """
    Golub Capital BDC, Inc. Schedules Release of Fiscal Year 2025 Third Quarter
    Results. The company will report its financial results on August 4, 2025.
    """
    accepted, _, reason = classify_exhibit_text(text)
    assert not accepted
    assert "scheduling" in reason


def test_actual_results_release_is_accepted():
    text = """
    Example BDC reports financial results for the quarter ended June 30, 2025.
    Net investment income was $0.41 per share and net asset value per share was
    $15.20. See the financial highlights below.
    """
    accepted, event_type, reason = classify_exhibit_text(text)
    assert accepted
    assert event_type == "8-K_EX-99_RESULTS"
    assert not reason


def test_result_season_maps_to_previous_completed_quarter():
    assert previous_quarter_end("2025-08-06T10:20:27.000Z") == "2025-06-30"
    assert previous_quarter_end("2026-02-04T21:01:08.000Z") == "2025-12-31"


def test_exact_timestamp_has_eastern_timezone():
    assert timestamp_et("2025-08-04T20:02:24.000Z") == "2025-08-04T16:02:24-04:00"
