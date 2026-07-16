"""Streamlit home page for the local synthetic portfolio demonstration."""

import streamlit as st
from dashboard.components.common import get_services, render_banner

st.set_page_config(page_title="Healthcare Language AI Portfolio", layout="wide")
render_banner(st)

services = get_services()
system = services.health.system_status()
readiness = services.health.ready()
rag = services.evidence.manifest

st.title("Healthcare Language AI Platform")
st.caption("Local read-only portfolio demonstration")
col1, col2, col3 = st.columns(3)
col1.metric("Readiness", readiness.status)
col2.metric("RAG approval", system.rag_approval_status)
col3.metric("Generator", system.generator_mode)

st.subheader("Milestone 10")
st.write(
    "Implemented: shared services, local FastAPI, Streamlit demo, citation/trace browsing, "
    "approval summaries, local operational events, deterministic demo evidence."
)
st.subheader("Canonical RAG Snapshot")
st.json(
    {
        "rag_run_id": rag.rag_run_id,
        "query_count": rag.query_count,
        "grounded_answers": rag.grounded_answer_count,
        "refusals": rag.refusal_count,
        "citation_failures": rag.citation_validation_failure_count,
        "groundedness_failures": rag.groundedness_failure_count,
        "safety_failures": rag.safety_validation_failure_count,
    }
)
