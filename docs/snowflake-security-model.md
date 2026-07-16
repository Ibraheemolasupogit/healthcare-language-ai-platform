# Snowflake Security Model

The target-state role model is least-privilege and reference-only:

- `HLA_PLATFORM_ADMIN`: owns platform objects and delegates privileges.
- `HLA_INGESTION_ROLE`: loads local canonical files into raw/governance layers.
- `HLA_TRANSFORM_ROLE`: transforms raw records into staging assets.
- `HLA_ANALYST_ROLE`: reads curated staging and analytical views.
- `HLA_READONLY_ROLE`: minimal read-only access.

Routine ownership is not assigned to `ACCOUNTADMIN` in the documented design.
No secrets, private keys, OAuth tokens, storage integrations, users, or network
policies are deployed in Milestone 3.
