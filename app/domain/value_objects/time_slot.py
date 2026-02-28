from dataclasses import dataclass
from datetime import datetime
from app.domain.exceptions import ValidationError


@dataclass(frozen=True)
class TimeSlot:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValidationError("Start and end must be timezone-aware datetimes")
        if self.start >= self.end:
            raise ValidationError("Start must be before end")

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.start < other.end and other.start < self.end
