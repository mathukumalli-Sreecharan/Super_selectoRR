import streamlit as st
from collections import Counter
from components.ui import render_shell, show_records
from services.fixture_store import load_fixture

def render():
    data=load_fixture(); render_shell("Overview")
    st.info("This is a synthetic evidence workflow demonstration. It is not a production dataset or project selection result.")
    release=data["release"]
    left,right=st.columns(2)
    left.metric("Synthetic players",len(data["players"]))
    right.metric("Scenario IDs",len(data["scenario_catalog"]))
    st.subheader("Fixture status")
    show_records([{"Release ID":release["release_id"],"Version":release["release_version"],"Status":release["approval_status"],"Manifest":"Not applicable to an approved release"}])
    counts=Counter(x["status"] for x in data["readiness_records"])
    st.subheader("Synthetic readiness coverage")
    show_records([{"Readiness status":k,"Fixture records":v} for k,v in sorted(counts.items())])
    st.subheader("Open limitations shown in this demo")
    show_records([{"Area":"Approval","State":"No real owner approval is represented"},{"Area":"Metrics","State":"Values are fixture display values; no formulas run"},{"Area":"Source data","State":"Synthetic references only; production mode is unavailable"}])
