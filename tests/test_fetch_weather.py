"""
Tests for fetch_weather.py — validates grouping logic that reduces API calls.
No database or Meteostat connection needed.
"""

import sys
import os
from datetime import date, timedelta
from collections import defaultdict
from unittest.mock import MagicMock, patch

# Meteostat API classes differ across versions; mock before importing fetch_weather
mock_meteostat = MagicMock()
sys.modules.setdefault("meteostat", mock_meteostat)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ingestion"))
with patch.dict("sys.modules", {"meteostat": mock_meteostat}):
    from fetch_weather import group_dates_by_location


def make_row(org_id, city, state, lat, lon, onset_date):
    return (org_id, city, state, lat, lon, onset_date)


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
