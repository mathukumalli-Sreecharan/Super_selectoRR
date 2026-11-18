from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

@dataclass(frozen=True)
class ReferenceResolution:
    state: str
    record: dict[str, Any] | None = None
