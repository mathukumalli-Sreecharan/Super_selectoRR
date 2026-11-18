import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Scenario Explorer")
    st.caption("Scenario wording and dispositions below are copied from the TASK-DASH-001 traceability artifact, linked to the authoritative v0.2.2 registers.")
    ids=[r["Scenario ID"] for r in data["scenario_catalog"]]
    st.write(f"Scenario catalog coverage: {len(ids)} IDs (BAT-S01–BAT-S09 and BWL-S01–BWL-S09).")
    selected=st.selectbox("Scenario ID",ids,key="scenario_id")
    row=next(r for r in data["scenario_catalog"] if r["Scenario ID"]==selected)
    classes=[c for c in data["scenario_classifications"] if c["scenario_id"]==selected]
    status=classes[0]["classification_outcome"] if classes else "NO SYNTHETIC CLASSIFICATION RECORD"
    st.subheader(selected)
    st.markdown(f"**Fixture classification state:** `{status}`")
    st.caption("No synthetic classification is evidence about a real match or player.")
    for label,key in [("Scenario lineage","Scenario lineage"),("Match situation","Match situation"),("Team task","Team task"),("Individual responsibility","Individual responsibility"),("Why pressure may or may not exist","Why pressure may or may not exist"),("Relevant candidate observations","Relevant candidate observations"),("Unresolved data requirements","Unresolved data requirements"),("Authoritative disposition","Authoritative disposition"),("Dashboard handling","Dashboard handling")]:
        st.markdown(f"**{label}**")
        st.write(row[key])
    st.markdown(f"**Authoritative source:** `{row['Authoritative source path']}` · Methodology `{row['Methodology version']}`")
    if selected in {"BAT-S02","BWL-S02"}: st.info("Source-defined counterexample treatment. Late innings alone does not establish pressure.")
    if selected=="BAT-S08": st.info("Competition comparability, not an independent pressure state. IPL/T20I remain separate by default.")
    if selected=="BWL-S07": st.info("Containment and validated bowler-credit wickets remain separate.")
    if selected=="BWL-S08": st.warning("DEFERRED — excluded from operational scoring/comparison/ranking.")
    if selected in {"BAT-S09","BWL-S09"}: st.warning("Verified active revised target/resources immediately before the event are required; this synthetic fixture provides no real event evidence.")
    st.subheader("Synthetic classification records")
    show_records(classes)
