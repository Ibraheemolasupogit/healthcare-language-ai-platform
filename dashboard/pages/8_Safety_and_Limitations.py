"""Safety and limitations page."""

import streamlit as st
from dashboard.components.common import render_banner

render_banner(st)
st.title("Safety and Limitations")
st.write("No clinical validation has been performed.")
st.write("No real patient data is used.")
st.write(
    "No hosted models, model downloads, cloud telemetry, or production "
    "authentication are implemented."
)
st.write(
    "The system is a local synthetic portfolio demonstration and must not be used for patient care."
)
