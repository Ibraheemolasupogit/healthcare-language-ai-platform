# Configuration Hardening

Configuration assurance checks preserve local-safe defaults:

- API and dashboard bind to localhost unless an explicit unsafe override is set.
- Wildcard CORS is rejected.
- Runtime timeout, concurrency, and rate-limit settings must be positive.
- Operational event roots remain repository-relative.
- Unsafe local binding remains disabled by default.

Run:

```bash
python -m healthcare_language_ai configuration-assurance --output-dir reports/assurance
```
