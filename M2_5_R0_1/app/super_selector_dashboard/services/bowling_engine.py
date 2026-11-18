"""Independent bowling opportunity and metric interfaces; unresolved math is blocked."""
from services.analysis_engines import AnalysisDisposition, not_ready
from services.metric_components import BOWLER_METRICS, bowling_component, effect_consistency_reliability
from services.opportunity_engine import eligible_fixture_opportunities


def analyze_bowling(_records) -> AnalysisDisposition:
    return not_ready("bowling", "Real source access and calculation are disabled until the Stage 2 authorization gate is separately satisfied.", "Full-population bowler-conceded runs remain NOT FEASIBLE under current evidence.", "No pressure classification or player metric was calculated.")


def bowling_fixture_opportunities(rows: list[dict], *, event_records: list[dict] | None = None):
    return eligible_fixture_opportunities(rows, discipline="BWL", event_records=event_records)


def bowling_dimensions(rows=()):
    result = {metric: bowling_component(metric, rows) for metric in BOWLER_METRICS}
    result.update(effect_consistency_reliability(discipline="bowling"))
    return result
