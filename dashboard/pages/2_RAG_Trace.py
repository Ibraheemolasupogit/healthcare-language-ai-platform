"""RAG trace explorer."""

import streamlit as st
from dashboard.components.common import get_services, render_banner

render_banner(st)
services = get_services()
st.title("RAG Trace")
answer = st.selectbox("Answer", services.evidence.answers, format_func=lambda item: item.answer_id)
st.json(services.trace.get_trace(answer.answer_id).model_dump(mode="json"))
