import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Player Evidence Profiles")
    st.caption("Synthetic IDs only. Values below are supplied fixture fields; this page calculates no metrics.")
    ids=[p["player_id"] for p in data["players"]]
    player_id=st.selectbox("Synthetic player ID",ids,key="profile_player")
    player=next(p for p in data["players"] if p["player_id"]==player_id)
    st.subheader(player["player_id"])
    show_records([{"Discipline":player["discipline"],"Competitions (separate)":", ".join(player["competition_history"]),"Identity state":player["identity_status"],"Role context":player["role_context"]}])
    opps=[o for o in data["opportunities"] if o["player_id"]==player_id]
    metrics=[m for m in data["metrics"] if m["player_id"]==player_id]
    metric_ids={m["metric_evidence_id"] for m in metrics}
    baselines=[b for b in data["baselines"] if b["player_id"]==player_id]
    st.subheader("Responsibility and opportunity")
    show_records([{**o,"Scenario state":next((c["classification_outcome"] for c in data["scenario_classifications"] if c["classification_id"]==o["scenario_classification_id"]),"MISSING_REFERENCE")} for o in opps])
    st.subheader("Historical baseline")
    if baselines:
        show_records([{"Baseline ID":b["baseline_version_id"],"Scope":b["competition_scope"],"Cutoff":b["cutoff_time"] or "UNRESOLVED","Observation count (synthetic)":b["observation_count"],"Synthetic display value":b["display_value"] if b["display_value"] is not None else "Unavailable — missing baseline evidence","Status":b["status"]} for b in baselines])
    else: st.info("No synthetic baseline record for this profile.")
    st.subheader("Supplied synthetic evidence values")
    if metrics:
        show_records([{"Evidence ID":m["metric_evidence_id"],"Synthetic display value":m["display_value"] if m["display_value"] is not None else "Unavailable — not zero","Unit":m["display_unit"],"Calculated":m["calculated"],"Label":m["label"]} for m in metrics])
    else: st.info("No synthetic evidence value for this profile.")
    st.subheader("Uncertainty and limitations")
    reliabilities=[r for r in data["reliability_assessments"] if any(ref in metric_ids for ref in r["metric_evidence_refs"])]
    show_records(reliabilities)
    st.subheader("Scenario and source traceability")
    class_ids={c["classification_id"] for c in data["scenario_classifications"] if c.get("opportunity_id") in {o["opportunity_id"] for o in opps}}
    show_records([c for c in data["scenario_classifications"] if c["classification_id"] in class_ids])
    source_ids={r for m in metrics for r in m["source_record_refs"]}|{r for o in opps for r in o["source_record_refs"]}
    show_records([r for r in data["source_records"] if r["source_record_id"] in source_ids])
    st.subheader("Recorded decision history")
    show_records([d for d in data["decisions"] if d["player_id"]==player_id])
    st.caption("No recommendation is generated. Missing or conflicting evidence remains visible.")
