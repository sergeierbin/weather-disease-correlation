"""
Tests for fetch_weather.py — validates grouping logic and fallback radius behaviour.
No database or real Meteostat connection needed.
"""

import sys
import os
import time
import pandas as pd
from datetime import date, datetime, timedelta
from collections import defaultdict
from unittest.mock import MagicMock, patch

# Meteostat API classes differ across versions; mock before importing fetch_weather.
# Must set sys.modules BEFORE import so fetch_weather.__globals__ and fw.__dict__
# point to the same module dict (patch.dict removes module after block, causing split).
mock_meteostat = MagicMock()
sys.modules["meteostat"] = mock_meteostat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))
import fetch_weather as fw
from fetch_weather import group_dates_by_location, fetch_weather


def make_row(org_id, city, state, lat, lon, onset_date):
    return (org_id, city, state, lat, lon, onset_date)


def _make_df(rows):
    """Build a minimal Meteostat-like DataFrame for mocking."""
    if not rows:
        return pd.DataFrame()
    idx = pd.DatetimeIndex([r[0] for r in rows])
    data = {col: [r[i] for r in rows]
            for i, col in enumerate(["tavg", "tmin", "tmax", "prcp", "pres"], start=1)}
    return pd.DataFrame(data, index=idx)


import fetch_weather as fw


class SyncThread:
    """Thread'i asendaja mis jookseb sünkroonselt — mock'id töötavad korrektselt."""
    def __init__(self, target=None, daemon=False):
        self._target = target
        self._alive = False
    def start(self):
        self._target()
    def join(self, timeout=None):
        pass
    def is_alive(self):
        return self._alive


class TimeoutThread(SyncThread):
    """Simuleerib timeout'i — is_alive() tagastab alati True."""
    def start(self): pass
    def is_alive(self): return True


class TestFetchWeather:
    """Tests for fallback radius logic and timeout handling."""

    def _start(self): return date(2020, 1, 10)
    def _end(self):   return date(2020, 1, 11)

    def test_returns_rows_when_first_radius_has_data(self):
        good_df = _make_df([(datetime(2020, 1, 10), 5.0, 2.0, 8.0, 1.0, 1013.0)])

        with patch.object(fw.threading, "Thread", SyncThread):
            with patch("fetch_weather.Daily") as MockDaily:
                MockDaily.return_value.fetch.return_value = good_df
                with patch("fetch_weather.Point") as MockPoint:
                    MockPoint.radius = 35000
                    rows = fetch_weather(42.36, -71.06, self._start(), self._end())

        assert len(rows) == 1
        assert MockDaily.call_count == 1, "Ei tohi proovida teist raadiust kui esimene leidis andmeid"

    def test_falls_back_to_larger_radius_when_first_empty(self):
        good_df = _make_df([(datetime(2020, 1, 10), 5.0, 2.0, 8.0, 1.0, 1013.0)])

        m_empty = MagicMock()
        m_empty.fetch.return_value = pd.DataFrame()
        m_good  = MagicMock()
        m_good.fetch.return_value  = good_df

        with patch.object(fw.threading, "Thread", SyncThread):
            with patch("fetch_weather.Daily") as MockDaily:
                MockDaily.side_effect = [m_empty, m_good]
                with patch("fetch_weather.Point") as MockPoint:
                    MockPoint.radius = 35000
                    rows = fetch_weather(42.36, -71.06, self._start(), self._end())

        assert len(rows) == 1
        assert MockDaily.call_count == 2, "Peab proovima teist raadiust kui esimene on tühi"

    def test_returns_empty_when_all_radii_empty(self):
        with patch.object(fw.threading, "Thread", SyncThread):
            with patch("fetch_weather.Daily") as MockDaily:
                MockDaily.return_value.fetch.return_value = pd.DataFrame()
                with patch("fetch_weather.Point") as MockPoint:
                    MockPoint.radius = 35000
                    rows = fetch_weather(42.36, -71.06, self._start(), self._end())

        assert rows == []

    def test_timeout_returns_empty(self):
        with patch.object(fw.threading, "Thread", TimeoutThread):
            with patch("fetch_weather.Point") as MockPoint:
                MockPoint.radius = 35000
                rows = fetch_weather(42.36, -71.06, self._start(), self._end())

        assert rows == []

    def test_radius_restored_after_success(self):
        good_df = _make_df([(datetime(2020, 1, 10), 5.0, 2.0, 8.0, 1.0, 1013.0)])

        with patch.object(fw.threading, "Thread", SyncThread):
            with patch("fetch_weather.Daily") as MockDaily:
                MockDaily.return_value.fetch.return_value = good_df
                with patch("fetch_weather.Point") as MockPoint:
                    MockPoint.radius = 35000
                    fetch_weather(42.36, -71.06, self._start(), self._end())
                    assert MockPoint.radius == 35000

    def test_radius_restored_after_all_empty(self):
        with patch.object(fw.threading, "Thread", SyncThread):
            with patch("fetch_weather.Daily") as MockDaily:
                MockDaily.return_value.fetch.return_value = pd.DataFrame()
                with patch("fetch_weather.Point") as MockPoint:
                    MockPoint.radius = 35000
                    fetch_weather(42.36, -71.06, self._start(), self._end())
                    assert MockPoint.radius == 35000


class TestGroupDatesByLocation:

    def test_single_location_single_date(self):
        rows = [make_row("org1", "Boston", "MA", 42.36, -71.06, date(2020, 1, 15))]
        loc_dates, loc_meta = group_dates_by_location(rows)

        assert len(loc_dates) == 1
        assert (42.36, -71.06) in loc_dates
        assert loc_dates[(42.36, -71.06)] == {date(2020, 1, 15)}
        assert loc_meta[(42.36, -71.06)] == ("Boston", "MA")

    def test_same_location_many_dates_becomes_one_entry(self):
        """Key optimization: N rows with same (lat, lon) → 1 API call, not N."""
        dates = [date(2020, 1, d) for d in range(1, 11)]  # 10 different dates
        rows = [make_row("org1", "Boston", "MA", 42.36, -71.06, d) for d in dates]
        loc_dates, _ = group_dates_by_location(rows)

        assert len(loc_dates) == 1, "10 rows with same location must collapse to 1 entry"
        assert loc_dates[(42.36, -71.06)] == set(dates)

    def test_two_different_locations(self):
        rows = [
            make_row("org1", "Boston", "MA", 42.36, -71.06, date(2020, 1, 1)),
            make_row("org2", "Honolulu", "HI", 21.31, -157.86, date(2020, 6, 1)),
        ]
        loc_dates, loc_meta = group_dates_by_location(rows)

        assert len(loc_dates) == 2
        assert loc_meta[(42.36, -71.06)] == ("Boston", "MA")
        assert loc_meta[(21.31, -157.86)] == ("Honolulu", "HI")

    def test_mixed_locations_and_dates(self):
        rows = [
            make_row("org1", "Boston", "MA", 42.36, -71.06, date(2020, 1, 1)),
            make_row("org1", "Boston", "MA", 42.36, -71.06, date(2020, 1, 5)),
            make_row("org1", "Boston", "MA", 42.36, -71.06, date(2020, 2, 1)),
            make_row("org2", "Honolulu", "HI", 21.31, -157.86, date(2020, 3, 10)),
            make_row("org2", "Honolulu", "HI", 21.31, -157.86, date(2020, 3, 11)),
        ]
        loc_dates, _ = group_dates_by_location(rows)

        assert len(loc_dates) == 2
        assert len(loc_dates[(42.36, -71.06)]) == 3
        assert len(loc_dates[(21.31, -157.86)]) == 2

    def test_empty_input(self):
        loc_dates, loc_meta = group_dates_by_location([])
        assert loc_dates == defaultdict(set)
        assert loc_meta == {}

    def test_date_range_covers_prev_day(self):
        """min(dates)-1 through max(dates) must cover the previous-day weather rows."""
        dates = [date(2020, 3, 5), date(2020, 3, 10), date(2020, 3, 1)]
        rows = [make_row("org1", "Boston", "MA", 42.36, -71.06, d) for d in dates]
        loc_dates, _ = group_dates_by_location(rows)

        collected = loc_dates[(42.36, -71.06)]
        start = min(collected) - timedelta(days=1)
        end   = max(collected)

        assert start == date(2020, 2, 29)   # day before earliest onset
        assert end   == date(2020, 3, 10)   # latest onset
