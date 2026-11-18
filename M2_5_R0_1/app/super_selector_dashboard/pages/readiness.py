import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Metric Readiness")
    st.caption("All records are synthetic display fixtures. No actual metric readiness state is changed.")
    choices=data["readiness_records"]
    selected=st.selectbox("Metric readiness example",[r["readiness_record_id"] for r in choices],key="readiness_id")
    record=next(r for r in choices if r["readiness_record_id"]==selected)
    st.subheader(record["metric_id"]+" / "+record["metric_version"])
    st.markdown(f"**Synthetic readiness state:** `{record['status']}`")
    st.write(record["scope"])
    st.subheader("Eleven evidence elements")
    show_records(record["elements"])
    st.subheader("Seven Stage 1 gates")
    show_records(record["stage1_gates"])
    st.warning("Synthetic element text does not establish readiness. Missing gate evidence is never inferred as passed.")
