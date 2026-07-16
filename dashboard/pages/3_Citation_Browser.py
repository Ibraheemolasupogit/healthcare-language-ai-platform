"""Citation browser."""

import streamlit as st
from dashboard.components.common import get_services, render_banner

render_banner(st)
services = get_services()
st.title("Citation Browser")
citations = list(services.evidence.citation_by_id)
citation_id = st.selectbox("Citation", citations)
st.json(services.evidence.citation_response(citation_id).model_dump(mode="json"))
