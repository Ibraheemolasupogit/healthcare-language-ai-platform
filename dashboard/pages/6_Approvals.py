"""Approval evidence view."""

import streamlit as st
from dashboard.components.common import get_services, render_banner

render_banner(st)
services = get_services()
st.title("Approvals")
st.subheader("Retrieval")
st.json(services.approval.retrieval_approval().model_dump(mode="json"))
st.subheader("RAG")
st.json(services.approval.rag_approval().model_dump(mode="json"))
