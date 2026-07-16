# Databricks Security Model

The target-state security design is reference-only. It assumes least privilege,
separation of duties, no public IP, restricted node types, required tags,
auto-termination, no unrestricted init scripts, and no embedded secrets.

No service principal, workspace URL, access token, cluster policy, Unity Catalog
grant, network control, or audit control is deployed by this repository.
