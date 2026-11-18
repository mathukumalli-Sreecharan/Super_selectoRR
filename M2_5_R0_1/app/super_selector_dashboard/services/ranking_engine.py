"""Ranking contracts for direct local IPL analysis.

Local source access is enabled by the project owner's Stage 2 decision.
Pressure rankings remain unavailable until the pressure methodology and its
metric/evidence requirements are implemented and validated.
"""
from services.analysis_engines import AnalysisDisposition, not_ready


def select_candidates(_candidates, *, discipline: str, mode: str = "REAL") -> AnalysisDisposition:
    if discipline not in {"batting", "bowling"}:
        raise ValueError("discipline must be batting or bowling")
    return not_ready(
        discipline,
        "Local IPL data processing is enabled by the project owner; pressure ranking is pending implementation and empirical validation of scenario rules, opportunity definitions, metric estimands, uncertainty and deterministic selection methodology.",
        status="PRESSURE METHODOLOGY NOT YET VALIDATED",
    )


def compare_candidates(_left, _right) -> AnalysisDisposition:
    return not_ready("comparison", "Pressure comparison requires implemented scenario metrics, comparable exposure, prior-only baselines and validated uncertainty.")
