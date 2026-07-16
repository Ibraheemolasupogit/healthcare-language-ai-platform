# Dependency And SBOM Assurance

Dependency assurance builds an offline inventory from the installed Python
environment and checks direct runtime dependencies against the local prohibited
package list. SBOM generation writes a local CycloneDX-style evidence document
with vulnerability status marked as not evaluated offline.

Run:

```bash
python -m healthcare_language_ai dependency-inventory --output-dir reports/assurance
python -m healthcare_language_ai sbom-generate --output-dir reports/assurance
```
