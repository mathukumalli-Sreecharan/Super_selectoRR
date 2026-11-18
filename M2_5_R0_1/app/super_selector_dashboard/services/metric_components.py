"""Metric component boundaries; unresolved estimands return NOT READY."""
from models.analytics import AnalysisResult


BATTER_METRICS = ("scoring_contribution", "batter_attributed_dismissals")
BOWLER_METRICS = ("run_containment", "bowler_credit_wickets", "dot_ball_performance")


def batting_component(metric_id: str, _opportunities=()) -> AnalysisResult:
    if metric_id not in BATTER_METRICS:
        raise ValueError(f"Unknown batting component: {metric_id}")
    return AnalysisResult("NOT READY", "batting", (
        "No approved operational estimand/denominator and source attribution semantics are available.",
        "No metric value was calculated.",
    ))


def bowling_component(metric_id: str, _opportunities=()) -> AnalysisResult:
    if metric_id not in BOWLER_METRICS:
        raise ValueError(f"Unknown bowling component: {metric_id}")
    reason = "Full-population bowler-conceded runs are NOT FEASIBLE: no provider-certified bowler-run allocation is available; source `runs` and extras fields lack approved semantics. No substitute is calculated." if metric_id == "run_containment" else "Legal-ball, run allocation, wicket-credit or dot-ball definitions are not validated; no metric value was calculated."
    return AnalysisResult("NOT READY", "bowling", (reason,))


def effect_consistency_reliability(*, discipline: str) -> dict[str, AnalysisResult]:
    if discipline not in {"batting", "bowling"}:
        raise ValueError("discipline must be batting or bowling")
    return {
        name: AnalysisResult("NOT READY", discipline, (reason,))
        for name, reason in {
            "effectiveness": "Approved personal expectation and estimand are required.",
            "consistency": "Conceptual only; no approved estimable definition or uncertainty treatment.",
            "reliability": "Evidence dimensions must be reported separately; no validated confidence score exists.",
        }.items()
    }
