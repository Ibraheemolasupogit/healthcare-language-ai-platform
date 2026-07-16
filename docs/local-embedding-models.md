# Local Embedding Models

Local dense embeddings are optional and excluded from default CI, Docker, fixture generation, and `make validate`.

Install only when needed:

```bash
cd /Users/privilege/Desktop/GitHub_repository/healthcare-language-ai-platform
python3 -m pip install ".[dense-local]"
```

Model inspection accepts only an explicit absolute local path. It rejects repository-style remote identifiers, does not download models, does not use `trust_remote_code`, and records offline environment controls such as `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `HF_DATASETS_OFFLINE=1`. These variables are documented safeguards, not a complete isolation proof.

Optional local model outputs belong under `outputs/` and are not checked in.
