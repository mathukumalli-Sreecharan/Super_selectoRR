"""Source interpretation is restricted to the pre-labelled synthetic fixture."""
from models.source_facts import FixtureDeliveryFact
from services.authorization import PRODUCTION_GATE


def interpret_delivery(record: dict, *, mode: str) -> FixtureDeliveryFact:
    if mode != "SYNTHETIC":
        PRODUCTION_GATE.require_production_authorization("interpret delivery record")
    required = ("delivery_id", "match_id", "innings_id", "sequence", "batter_id", "bowler_id", "legal_ball", "batter_faced")
    missing = [name for name in required if name not in record or record[name] is None]
    if missing:
        raise ValueError("Synthetic event lacks explicit candidate fields: " + ", ".join(missing))
    if type(record["legal_ball"]) is not bool or type(record["batter_faced"]) is not bool:
        raise ValueError("Synthetic fixture eligibility flags must be explicit booleans.")
    return FixtureDeliveryFact(
        delivery_id=str(record["delivery_id"]), match_id=str(record["match_id"]),
        innings_id=str(record["innings_id"]), sequence=int(record["sequence"]),
        batter_id=str(record["batter_id"]), bowler_id=str(record["bowler_id"]),
        legal_ball=record["legal_ball"], batter_faced=record["batter_faced"],
        source_record_refs=tuple(record.get("source_record_refs", ())),
    )
