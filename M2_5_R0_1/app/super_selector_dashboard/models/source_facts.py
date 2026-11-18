"""Normalized event evidence types. Synthetic origin is mandatory for this build."""
from dataclasses import dataclass


@dataclass(frozen=True)
class FixtureDeliveryFact:
    delivery_id: str
    match_id: str
    innings_id: str
    sequence: int
    batter_id: str
    bowler_id: str
    legal_ball: bool
    batter_faced: bool
    source_record_refs: tuple[str, ...]
    validation_label: str = "SYNTHETIC FIXTURE ONLY — NOT SOURCE SEMANTICS"
