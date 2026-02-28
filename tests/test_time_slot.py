from datetime import datetime, timezone

import pytest

from app.domain.exceptions import ValidationError
from app.domain.value_objects.time_slot import TimeSlot


def test_time_slot_requires_timezone_aware_datetimes() -> None:
    with pytest.raises(ValidationError):
        TimeSlot(
            start=datetime(2026, 1, 1, 10, 0, 0),
            end=datetime(2026, 1, 1, 11, 0, 0),
        )


def test_time_slot_requires_start_before_end() -> None:
    with pytest.raises(ValidationError):
        TimeSlot(
            start=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            end=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )


def test_time_slot_overlaps_for_intersecting_ranges() -> None:
    first = TimeSlot(
        start=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
    )
    second = TimeSlot(
        start=datetime(2026, 1, 1, 10, 30, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 11, 30, 0, tzinfo=timezone.utc),
    )

    assert first.overlaps(second) is True
