import streamlit as st

BANNER = "SYNTHETIC \u2014 NOT PRODUCTION DATA · v0.1.3"

def render_shell(title: str) -> None:
    st.title(title)
    st.caption(BANNER + " \u00b7 Fixture values are fictional and do not represent project decisions or player evidence.")

def show_status(label: str, value: str) -> None:
    st.markdown(f"**{label}:** `{value}`")

def show_records(records: list[dict], empty_message: str = "No synthetic records in this fixture.") -> None:
    if records:
        st.dataframe(records, width="stretch", hide_index=True)
    else:
        st.info(empty_message)

