"""Player comparison contract; no equivalence is inferred from raw totals."""
from services.analysis_engines import not_ready


def compare_profiles(left: dict, right: dict, *, comparable_scenario: bool = False, metric_readiness: str = "NOT READY"):
    if left.get("discipline") != right.get("discipline"):
        return not_ready("comparison", "Cross-discipline comparison is prohibited.")
    if not comparable_scenario or metric_readiness not in {"READY", "READY WITH LIMITATIONS"}:
        return not_ready("comparison", "Same-discipline comparable scenario, eligible exposure, separate personal baselines and metric readiness are required.")
    return not_ready("comparison", "Comparison estimand, uncertainty method and separately bound production authorization remain unavailable.")
