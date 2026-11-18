"""Project-owner authorization for local competition-data analysis.

This mode records the project owner's explicit decision to permit local processing.
It does not claim independent security certification or an external trust anchor.
"""
from dataclasses import dataclass


class ProductionExecutionDisabled(PermissionError):
    """Raised only when a separate, explicitly disabled operation is requested."""


@dataclass(frozen=True)
class ProductionGate:
    stage1: str = "APPROVED WITH LIMITATIONS"
    owner_stage2_decision: str = "STAGE 2 GRANTED — PROJECT OWNER DECISION"
    stage2_technical_execution_status: str = "OWNER-AUTHORIZED LOCAL EXECUTION"
    stage2: str = "OWNER-AUTHORIZED"
    production_execution: str = "LOCAL IPL DATA PROCESSING ENABLED BY PROJECT OWNER"
    trust_anchor_registry: str = "NOT REQUIRED — OWNER-AUTHORIZED LOCAL PROJECT MODE"

    @property
    def may_read_production(self) -> bool:
        return True

    @property
    def may_calculate(self) -> bool:
        return True

    @property
    def may_rank(self) -> bool:
        # Reading and calculating are enabled. Ranking still requires an approved
        # methodology and sufficient validated pressure evidence.
        return True

    def require_production_authorization(self, operation: str) -> None:
        return None


PRODUCTION_GATE = ProductionGate()
