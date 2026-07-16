# Container Assurance

Container assurance statically checks the Dockerfile for the expected slim
Python base image, non-root runtime user, writable local output directories,
model-free defaults, and absence of obvious embedded credential tokens.

Run:

```bash
python -m healthcare_language_ai container-assurance --dockerfile Dockerfile --output-dir reports/assurance
```

This is static assurance. A Docker build remains a separate validation step.
