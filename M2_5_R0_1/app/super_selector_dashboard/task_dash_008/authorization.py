"""Fail-closed Stage 2 gate. It does not alter or replace the v0.1.5 gate."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import hashlib
import json
import re
import sys

from pathlib import Path
import sys

_V015_ROOT = Path(__file__).resolve().parents[1] / "versions" / "TASK_DASH_002_implementation_v0_1_5"
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_TASK_ROOT = _WORKSPACE_ROOT / "governance" / "TASK_DASH_008_controlled_source_validation_v0_1"
if str(_V015_ROOT) not in sys.path:
    sys.path.insert(0, str(_V015_ROOT))
from services.authorization import PRODUCTION_GATE  # noqa: E402


TRUST_ANCHOR_REGISTRY_STATUS = "EMPTY"
IMPLEMENTATION_VERSION = "TASK-DASH-008-v0.1"
TRUST_ANCHOR_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / "versions" / "TASK_DASH_002_implementation_v0_1_5"
    / "data" / "governance_reference" / "STAGE2_TRUST_ANCHOR_REGISTRY.json"
)
REQUIRED_TOP_LEVEL = {
    "record_id", "stage2_status", "production_execution_status", "decision_authority",
    "methodology", "source", "implementation", "execution_environment",
    "permitted_operations", "output_contract", "acceptance_tests", "stop_conditions", "incident_handling",
    "evidence_retention", "approvals", "record_sha256",
}
REQUIRED_APPROVERS = {"project_owner", "security_authority", "independent_reviewer"}
ALLOWED_OPERATIONS = {
    "archive_integrity_verification", "source_row_read_only", "structural_validation",
    "semantic_validation", "VAL-01", "VAL-02", "VAL-03", "VAL-04", "VAL-05",
    "VAL-06", "VAL-07", "write_validation_outputs", "hash_and_preserve_evidence",
}


class Stage2AuthorizationError(PermissionError):
    """Raised before any production archive or CSV member is opened."""


def authorization_record_problems(record: Any) -> tuple[str, ...]:
    """Structural validation only; this function never grants execution permission."""
    if not isinstance(record, Mapping):
        return ("AUTHORIZATION_RECORD_MISSING_OR_NOT_OBJECT",)
    problems = [f"AUTH_FIELD_MISSING:{key}" for key in sorted(REQUIRED_TOP_LEVEL - set(record))]
    if problems:
        return tuple(problems)
    if record.get("stage2_status") != "APPROVED":
        problems.append("STAGE2_NOT_APPROVED")
    if record.get("production_execution_status") != "AUTHORIZED":
        problems.append("PRODUCTION_EXECUTION_NOT_AUTHORIZED")
    if record.get("decision_authority") != "Project Owner":
        problems.append("PROJECT_OWNER_DECISION_NOT_IDENTIFIED")
    for section, required in {
        "methodology": ("version", "sha256"),
        "source": ("archive_path", "archive_sha256", "archive_size_bytes", "members"),
        "implementation": ("version", "code_sha256", "dependency_lock_sha256", "source_contract_sha256"),
        "execution_environment": ("environment_id", "identity_sha256", "max_runtime_seconds", "max_memory_bytes", "max_input_bytes", "max_output_bytes"),
        "output_contract": ("directory", "schemas", "no_overwrite"),
        "evidence_retention": ("policy_id", "retention_period", "custodian"),
    }.items():
        value = record.get(section)
        if not isinstance(value, Mapping):
            problems.append(f"AUTH_SECTION_INVALID:{section}")
            continue
        for key in required:
            if value.get(key) in (None, "", []):
                problems.append(f"AUTH_SECTION_FIELD_MISSING:{section}.{key}")
        if section == "execution_environment":
            for key in ("max_runtime_seconds", "max_memory_bytes", "max_input_bytes", "max_output_bytes"):
                if type(value.get(key)) is not int or value[key] <= 0:
                    problems.append(f"AUTH_RESOURCE_LIMIT_INVALID:{key}")
        if section == "output_contract":
            if value.get("no_overwrite") is not True:
                problems.append("OUTPUT_NO_OVERWRITE_NOT_ENABLED")
            if not isinstance(value.get("directory"), str) or not Path(value["directory"]).is_absolute():
                problems.append("OUTPUT_DIRECTORY_NOT_ABSOLUTE")
    approvals = record.get("approvals")
    if not isinstance(approvals, Mapping):
        problems.append("AUTH_APPROVALS_INVALID")
    else:
        for role in sorted(REQUIRED_APPROVERS):
            approval = approvals.get(role)
            if not isinstance(approval, Mapping):
                problems.append(f"APPROVAL_MISSING:{role}")
            elif approval.get("status") != "APPROVED" or not approval.get("identity") or not approval.get("evidence_ref"):
                problems.append(f"APPROVAL_INCOMPLETE:{role}")
    if not isinstance(record.get("permitted_operations"), list) or not record["permitted_operations"]:
        problems.append("PERMITTED_OPERATIONS_MISSING")
    elif any(not isinstance(operation, str) or operation not in ALLOWED_OPERATIONS for operation in record["permitted_operations"]):
        problems.append("PERMITTED_OPERATION_OUT_OF_SCOPE")
    elif "source_row_read_only" not in record["permitted_operations"]:
        problems.append("SOURCE_ROW_READ_OPERATION_NOT_EXPLICIT")
    if not isinstance(record.get("acceptance_tests"), list) or not record["acceptance_tests"]:
        problems.append("ACCEPTANCE_TESTS_MISSING")
    if not isinstance(record.get("stop_conditions"), list) or not record["stop_conditions"]:
        problems.append("STOP_CONDITIONS_MISSING")
    if not isinstance(record.get("incident_handling"), Mapping) or not all(record["incident_handling"].get(k) for k in ("policy_id", "contact", "escalation_path")):
        problems.append("INCIDENT_HANDLING_INCOMPLETE")
    if not isinstance(record.get("record_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["record_sha256"]):
        problems.append("AUTH_RECORD_HASH_INVALID")
    elif canonical_record_sha256(record) != record["record_sha256"]:
        problems.append("AUTH_RECORD_HASH_MISMATCH")
    # Verify the authorization binds this exact working specification, selected
    # archive/member identities, validation code and locked dependencies.
    try:
        expected = current_authorization_bindings()
        method_record = record.get("methodology") if isinstance(record.get("methodology"), Mapping) else {}
        implementation_record = record.get("implementation") if isinstance(record.get("implementation"), Mapping) else {}
        supplied_source = record.get("source") if isinstance(record.get("source"), Mapping) else {}
        supplied_members = supplied_source.get("members", []) if isinstance(supplied_source, Mapping) else []
        supplied_members = sorted(
            ({"name": row.get("name"), "size_bytes": row.get("size_bytes"), "sha256": row.get("sha256")} for row in supplied_members if isinstance(row, Mapping)),
            key=lambda row: str(row["name"]),
        )
        if method_record.get("sha256") != expected["methodology_sha256"]:
            problems.append("METHODOLOGY_HASH_NOT_CURRENT")
        if method_record.get("version") != expected["methodology_version"]:
            problems.append("METHODOLOGY_VERSION_NOT_CURRENT")
        if (
            supplied_source.get("archive_path") != expected["source"]["archive_path"]
            or supplied_source.get("archive_size_bytes") != expected["source"]["archive_size_bytes"]
            or supplied_source.get("archive_sha256") != expected["source"]["archive_sha256"]
            or supplied_members != expected["source"]["members"]
        ):
            problems.append("SOURCE_IDENTITY_NOT_CURRENT")
        if implementation_record.get("code_sha256") != expected["code_sha256"]:
            problems.append("PRODUCTION_CODE_HASH_NOT_CURRENT")
        if implementation_record.get("version") != expected["implementation_version"]:
            problems.append("PRODUCTION_CODE_VERSION_NOT_CURRENT")
        if implementation_record.get("dependency_lock_sha256") != expected["dependency_lock_sha256"]:
            problems.append("DEPENDENCY_LOCK_HASH_NOT_CURRENT")
        if implementation_record.get("source_contract_sha256") != expected["source_contract_sha256"]:
            problems.append("SOURCE_CONTRACT_HASH_NOT_CURRENT")
        environment_record = record.get("execution_environment") if isinstance(record.get("execution_environment"), Mapping) else {}
        if environment_record.get("environment_id") != expected["environment"]["environment_id"] or environment_record.get("identity_sha256") != expected["environment"]["identity_sha256"]:
            problems.append("EXECUTION_ENVIRONMENT_IDENTITY_NOT_CURRENT")
        output_record = record.get("output_contract") if isinstance(record.get("output_contract"), Mapping) else {}
        supplied_schemas = output_record.get("schemas", [])
        if supplied_schemas != expected["schemas"]:
            problems.append("OUTPUT_SCHEMA_IDENTITY_NOT_CURRENT")
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        problems.append("BOUND_AUTHORIZATION_IDENTITIES_UNAVAILABLE")
    return tuple(problems)


def canonical_record_sha256(record: Mapping[str, Any]) -> str:
    """Hash canonical JSON without its self-referential record_sha256 field."""
    payload = {key: value for key, value in record.items() if key != "record_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def production_code_identity_sha256() -> str:
    """Digest over this code, acceptance tests and required shared contracts."""
    code_root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    files = {
        f"task_dash_008/{path.relative_to(code_root).as_posix()}": path
        for path in code_root.rglob("*.py") if path.is_file()
    }
    for relative in (
        "services/authorization.py", "services/scenario_registry.py", "models/analytics.py",
        "data/methodology/BATTING_SCENARIO_REVIEW_v0_2_2.csv",
        "data/methodology/BOWLING_SCENARIO_REVIEW_v0_2_2.csv",
    ):
        files[f"TASK_DASH_002_implementation_v0_1_5/{relative}"] = _V015_ROOT / relative
    for relative, path in sorted(files.items()):
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii") + b"\n")
    return digest.hexdigest()


def current_authorization_bindings() -> dict[str, Any]:
    """Return exact current identities expected in a formal record."""
    contract = json.loads((_TASK_ROOT / "SOURCE_FIELD_VALIDATION_CONTRACT.json").read_text(encoding="utf-8"))
    specification = contract["active_calculation_specification"]
    source = contract["source_identity"]
    schema_names = ("VALIDATION_OUTPUT_SCHEMA.md", "VALIDATION_EXCEPTION_SCHEMA.csv", "VALIDATION_MODULE_REGISTER.csv")
    schemas = [
        {"name": name, "sha256": hashlib.sha256((_TASK_ROOT / name).read_bytes()).hexdigest()}
        for name in schema_names
    ]
    dependency_lock_sha256 = hashlib.sha256((_TASK_ROOT / "requirements.lock").read_bytes()).hexdigest()
    source_contract_sha256 = hashlib.sha256((_TASK_ROOT / "SOURCE_FIELD_VALIDATION_CONTRACT.json").read_bytes()).hexdigest()
    environment_descriptor = {
        "python_version": sys.version.split()[0],
        "python_implementation": sys.implementation.name,
        "platform": sys.platform,
        "dependency_lock_sha256": dependency_lock_sha256,
        "source_contract_sha256": source_contract_sha256,
    }
    environment_identity = hashlib.sha256(
        json.dumps(environment_descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    members = sorted(
        ({"name": row["name"], "size_bytes": row["size_bytes"], "sha256": row["sha256"]} for row in source["members"]),
        key=lambda row: row["name"],
    )
    return {
        "methodology_version": specification["task"],
        "methodology_sha256": hashlib.sha256((_PROJECT_ROOT / specification["path"]).read_bytes()).hexdigest(),
        "implementation_version": IMPLEMENTATION_VERSION,
        "source": {
            "archive_path": source["archive_path"],
            "archive_size_bytes": source["archive_size_bytes"],
            "archive_sha256": source["archive_sha256"],
            "members": members,
        },
        "code_sha256": production_code_identity_sha256(),
        "dependency_lock_sha256": dependency_lock_sha256,
        "source_contract_sha256": source_contract_sha256,
        "environment": {
            "environment_id": f"python-{sys.version.split()[0]}-{sys.platform}",
            "identity_sha256": environment_identity,
        },
        "schemas": schemas,
    }


def authorize_stage2(record: Any = None) -> str:
    """Permit local execution under the project owner's recorded Stage 2 decision.

    No external authorization record, certificate, portal or trust-anchor registry
    is required for this local project mode. Source integrity and analytical
    methodology validation remain separate concerns.
    """
    return "OWNER-AUTHORIZED LOCAL EXECUTION"
