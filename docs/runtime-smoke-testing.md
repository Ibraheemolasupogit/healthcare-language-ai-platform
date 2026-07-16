# Runtime Smoke Testing

Runtime smoke tests start the local FastAPI or Streamlit process on localhost,
probe bounded endpoints, and terminate the process. They are intentionally
separate from `make validate` because they start long-running services.

Run:

```bash
python -m healthcare_language_ai runtime-smoke-api --host 127.0.0.1 --port 0 --timeout 30 --output-dir reports/runtime-smoke
python -m healthcare_language_ai runtime-smoke-dashboard --host 127.0.0.1 --port 0 --timeout 45 --output-dir reports/runtime-smoke
python -m healthcare_language_ai runtime-smoke-summary --smoke-dir reports/runtime-smoke
```
