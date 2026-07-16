# Dense Embedding Adapters

The default dense baseline is deterministic feature hashing with SHA-256. It is an
engineering baseline, not a semantic language model.

The optional sentence-transformer adapter is isolated. It requires an existing
local model path and never downloads a model automatically. CI and fixture
generation do not require sentence-transformers.
## Optional Local Adapter

Milestone 7 completes an optional local sentence-transformer inspection and injected-encoder test path. Default validation does not install `sentence-transformers` or `torch`, does not download models, and does not check in local-model benchmark outputs.

