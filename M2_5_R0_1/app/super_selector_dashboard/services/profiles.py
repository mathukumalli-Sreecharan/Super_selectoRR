"""Evidence profiles are assembled from linked evidence, never from name similarity."""
from services.opportunity_engine import validate_opportunities


def synthetic_profile(data: dict, player_id: str) -> dict:
    player = next((p for p in data.get("players", []) if p.get("player_id") == player_id), None)
    if player is None:
        raise KeyError(f"Unknown player identity: {player_id}")
    opportunities = [o for o in data.get("opportunities", []) if o.get("player_id") == player_id]
    parsed = validate_opportunities(opportunities, event_records=data.get("events", []))
    return {
        "identity": player,
        "opportunities": parsed,
        "metrics": [m for m in data.get("metrics", []) if m.get("player_id") == player_id],
        "limitations": "Synthetic fixture profile only; not a production player assessment.",
    }
