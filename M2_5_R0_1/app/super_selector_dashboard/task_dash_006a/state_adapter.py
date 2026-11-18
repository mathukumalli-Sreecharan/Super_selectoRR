"""Synthetic interface to the existing TASK-DASH-004B state constructor."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
from typing import Any, Mapping, Sequence


class StateReconstructionBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class SyntheticValidationEvidence:
    archive_status: str
    structural_status: str
    identity_status: str
    semantic_status: str
    sequence_status: str
    data_mode: str = "SYNTHETIC"


def reconstruct_synthetic_states(
    evidence: SyntheticValidationEvidence,
    match_context: Mapping[str, Any],
    normalized_deliveries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Call 004B only after every synthetic evidence gate passes.

    This is not a source adapter. No source header is mapped to normalized
    state input and the evidence object cannot authorize production access.
    """
    if not isinstance(evidence, SyntheticValidationEvidence) or evidence.data_mode != "SYNTHETIC":
        raise StateReconstructionBlocked("Only synthetic evidence can call this adapter.")
    gates = (evidence.archive_status, evidence.structural_status, evidence.identity_status, evidence.semantic_status, evidence.sequence_status)
    if any(value != "PASS" for value in gates):
        raise StateReconstructionBlocked("ARCHIVE_STRUCTURE_IDENTITY_SEMANTICS_OR_SEQUENCE_NOT_VALIDATED")
    task_root = Path(__file__).resolve().parents[3]
    module_path = task_root / "governance" / "TASK_DASH_004B_pressure_state_reconstruction" / "state_reconstruction.py"
    spec = importlib.util.spec_from_file_location("_task_dash_004b_state_reconstruction", module_path)
    if spec is None or spec.loader is None:
        raise StateReconstructionBlocked("EXISTING_STATE_RECONSTRUCTOR_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reconstruct_pre_delivery_states(match_context, normalized_deliveries)
