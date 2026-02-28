from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Service:
    name: str
    duration_minutes: int
    price: float
    id: UUID = field(default_factory=uuid4)
