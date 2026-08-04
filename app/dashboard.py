try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit("Install the UI dependency during the dashboard unit.") from exc

st.title("MacroPulse")
st.info("Prepared starter: no live macroeconomic data has been fetched.")
