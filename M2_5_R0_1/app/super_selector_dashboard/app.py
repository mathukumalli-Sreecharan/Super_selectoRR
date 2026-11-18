import streamlit as st

from config.settings import APP_TITLE, APP_VERSION
from pages.dashboard import render_dashboard, PAGES

st.set_page_config(page_title=APP_TITLE, page_icon="🏏", layout="wide")
st.sidebar.title("SupeRR Selector")
st.sidebar.caption(APP_VERSION)
st.sidebar.success("REAL IPL DATA · DIRECT SOURCE MODE")
section = st.sidebar.radio("Research view", list(PAGES), key="research_view")
render_dashboard(section=section)
