# Portfolio Assurance

Portfolio assurance combines Milestone 11 evidence into required and
conditional gates. Required gates cover contract compatibility, configuration
safety, operational integrity, backup recovery, security assurance, dependency
policy, SBOM generation, and static container assurance. Runtime smoke is
conditional because it starts local services and remains separate from default
validation.

Run:

```bash
python -m healthcare_language_ai portfolio-assurance --output-dir reports/assurance
python -m healthcare_language_ai portfolio-assurance-validate --assurance-dir reports/assurance
python -m healthcare_language_ai portfolio-assurance-summary --assurance-dir reports/assurance
```
