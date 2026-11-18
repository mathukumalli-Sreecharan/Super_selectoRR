"""Independent batting opportunity and metric interfaces; unresolved math is blocked."""
from services.analysis_engines import AnalysisDisposition, not_ready
from services.metric_components import BATTER_METRICS, batting_component, effect_consistency_reliability
from services.opportunity_engine import eligible_fixture_opportunities


def analyze_batting(_records) -> AnalysisDisposition:
    return not_ready("batting", "Real source access and calculation are disabled until the Stage 2 authorization gate is separately satisfied.", "No pressure classification or player metric was calculated.")


def batting_fixture_opportunities(rows: list[dict], *, event_records: list[dict] | None = None):
    return eligible_fixture_opportunities(rows, discipline="BAT", event_records=event_records)


def batting_dimensions(rows=()):
    result = {metric: batting_component(metric, rows) for metric in BATTER_METRICS}
    result.update(effect_consistency_reliability(discipline="batting"))
    return result
