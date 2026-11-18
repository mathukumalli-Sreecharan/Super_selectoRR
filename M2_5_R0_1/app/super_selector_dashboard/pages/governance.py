import streamlit as st
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Data and Governance Status")
    st.warning("Application data mode is synthetic. No production artifact path, database, external source, or trust anchor is configured.")
    st.subheader("Synthetic release metadata")
    release=data["release"]
    show_records([{"Release":release["release_id"],"Version":release["release_version"],"Status":release["approval_status"],"Manifest digest":release["manifest_sha256"] or "Not applicable to fixture"}])
    st.subheader("Static governance reference")
    st.caption("Copied status labels are reference metadata, not a live governance lookup and not changed by this demo.")
    show_records([{"Status":k.replace("_"," ").upper(),"Recorded value":v} for k,v in data["governance_reference"].items()])
    st.subheader("Synthetic coverage and quality cases")
    show_records([{"Case":"Missing baseline","Display behavior":"Unavailable, not zero"},{"Case":"Unclassified / deferred","Display behavior":"Exact state and reason remain visible"},{"Case":"IPL and T20I","Display behavior":"Separate synthetic scopes"},{"Case":"Missing/ambiguous reference","Display behavior":"Fail closed; dependent evidence is blocked"}])
