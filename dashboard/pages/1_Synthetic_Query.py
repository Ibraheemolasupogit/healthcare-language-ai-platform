"""Synthetic query page."""

import streamlit as st
from dashboard.components.common import acknowledgement_required, get_services, render_banner

from healthcare_language_ai.application.contracts import QueryRequest

render_banner(st)
services = get_services()
queries = services.evidence.queries

st.title("Synthetic Query")
ack = st.checkbox("I understand this is synthetic and not for clinical use.")
selected = st.selectbox("Fixture query", queries, format_func=lambda row: row["query_id"])
query_text = st.text_area("Synthetic demo query", value=selected["query_text"], height=100)
metadata_filter = st.text_input("Metadata filter key=value (optional)")
filters = {}
if metadata_filter and "=" in metadata_filter:
    key, value = metadata_filter.split("=", 1)
    filters[key.strip()] = value.strip()

st.caption(
    "Allowed: fixture-backed synthetic portfolio queries. Prohibited: diagnosis, "
    "treatment, medication, real-patient, emergency requests."
)
if st.button("Run query", disabled=not acknowledgement_required(ack)):
    response = services.query.run_synthetic_query(
        QueryRequest(
            query_text=query_text,
            query_id=selected["query_id"],
            metadata_filters=filters,
            portfolio_demo_mode=True,
            include_trace=True,
        )
    )
    st.subheader(response.answer_status)
    st.write(response.answer_text)
    st.json(response.model_dump(mode="json"))
