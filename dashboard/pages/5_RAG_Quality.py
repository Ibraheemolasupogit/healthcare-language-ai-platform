"""RAG quality view."""

import streamlit as st
from dashboard.components.common import get_services, render_banner

render_banner(st)
services = get_services()
st.title("RAG Quality")
st.json(services.approval.rag_approval().model_dump(mode="json"))
st.dataframe(services.approval.rag_gates().gates)
