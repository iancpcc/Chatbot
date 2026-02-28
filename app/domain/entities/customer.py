from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Customer:
    full_name: str
    contact: str  # teléfono o email
    id: UUID = field(default_factory=uuid4)
