from datetime import datetime, timezone
from decimal import Decimal

import pytest

from planner.contracts import Location, LogMetadata, TripRequest


@pytest.fixture
def trip_request():
    locations = [Location(label, label, lon, 40, "America/New_York")
                 for label, lon in (("origin", -80), ("pickup", -79), ("dropoff", -78))]
    return TripRequest(*locations, Decimal("0"), datetime(2026, 10, 2, 12, tzinfo=timezone.utc),
                       "America/New_York", LogMetadata())
