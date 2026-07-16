"""Architecture page."""

import streamlit as st
from dashboard.components.common import render_banner

render_banner(st)
st.title("Architecture")
st.markdown(
    """
```mermaid
flowchart LR
  A["Synthetic fixtures (implemented)"] --> B["Ingestion and preprocessing (implemented)"]
  B --> C["Extraction and retrieval (implemented)"]
  C --> D["Guarded RAG (implemented)"]
  D --> E["Shared application service (implemented)"]
  E --> F["FastAPI local read-only API (implemented)"]
  E --> G["Streamlit portfolio dashboard (implemented)"]
  E --> H["Local observability (implemented)"]
  C -. "contract only" .-> I["Snowflake / Databricks / MLflow target state"]
```
"""
)
st.write(
    "Implemented components are local and fixture-backed. Target-state cloud "
    "components are not deployed."
)
