import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Decision Audit")
    st.caption("Synthetic append-only history examples; no actual decision records or owner approvals.")
    decisions=data["decisions"]
    show_records([{"Decision ID":d["decision_id"],"Version":d["decision_version"],"State":d["decision_status"],"Supersedes":d.get("supersedes_decision_id") or "\u2014","Superseded by":d.get("superseded_by_decision_id") or "\u2014","Rationale":d["rationale"]} for d in decisions])
    st.subheader("Synthetic audit events")
    show_records(data["audit_events"])
    st.info("Prior versions remain visible. Reviewer and owner approvals are not fabricated.")
