# Security Assurance

Security assurance performs local static checks only. It scans configured
source, docs, dashboard, fixtures, and container files for common secret
patterns and unexpected sensitive-content patterns. Synthetic fixture content
is excluded where appropriate.

Run:

```bash
python -m healthcare_language_ai security-assurance --output-dir reports/assurance
```

This does not replace professional penetration testing, dependency
vulnerability scanning with live feeds, or production security review.
