import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Shortlist Evidence")
    st.info("These are fictional state-rendering examples. They are not project shortlist decisions or recommendations.")
    states=sorted({d["decision_status"] for d in data["decisions"]})
    filt=st.selectbox("Decision state",["All states"]+states,key="decision_filter")
    records=data["decisions"] if filt=="All states" else [d for d in data["decisions"] if d["decision_status"]==filt]
    show_records([{"Decision ID":d["decision_id"],"Player ID":d["player_id"],"State":d["decision_status"],"Version":d["decision_version"],"Supersedes":d.get("supersedes_decision_id") or "None"} for d in records])
    if not records: st.info("No recorded synthetic decision in this state.")
    selected=st.selectbox("Synthetic decision record",[d["decision_id"] for d in records],key="decision_id") if records else None
    if selected:
        d=next(x for x in records if x["decision_id"]==selected)
        st.subheader(d["decision_id"]); st.markdown(f"**State:** `{d['decision_status']}` · **Discipline:** `{d['discipline']}`")
        st.write(d["rationale"])
        st.markdown("**Supporting metric evidence**"); show_records([m for m in data["metrics"] if m["metric_evidence_id"] in d["supporting_metric_refs"]])
        st.markdown("**Supporting scenario evidence**"); show_records([c for c in data["scenario_classifications"] if c["classification_id"] in d["supporting_scenario_refs"]])
        st.markdown("**Counter-evidence**"); show_records([c for c in data["evidence_conflicts"] if c["conflict_id"] in d["counter_evidence_refs"]])
        st.markdown("**Reviewer / owner fields**")
        show_records([{"Preparer":d.get("preparer_id") or "Not recorded","Reviewer":d.get("reviewer_id") or "Not recorded","Owner decision reference":d.get("owner_decision_ref") or "Not recorded — no approval is fabricated","Decision timestamp":d.get("decision_timestamp") or "Not recorded"}])
        st.caption("The application reads fixture records only; it does not create or rank decisions.")
