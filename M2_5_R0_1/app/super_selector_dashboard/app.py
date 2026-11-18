import streamlit as st

from config.settings import APP_TITLE, APP_VERSION
from pages.dashboard import PAGES, render_dashboard

st.set_page_config(page_title=APP_TITLE, page_icon="🏏", layout="wide", initial_sidebar_state="expanded")


def main():
    st.sidebar.markdown("## SupeRR Selector")
    st.sidebar.caption("SEASON 2 · IPL PERFORMANCE RESEARCH")
    st.sidebar.markdown("---")
    section = st.sidebar.radio("RESEARCH SECTIONS", list(PAGES), key="research_view")
    st.sidebar.markdown("---")
    st.sidebar.caption(APP_VERSION)
    render_dashboard(section=section)


app_page = st.Page(main, title="app", default=True)
st.navigation([app_page]).run()
