# Contract Evolution

Milestone 11 treats local APIs, CLI commands, configuration sections, Pydantic
models, JSON schemas, and prompt records as explicit contracts.

`contracts-baseline` writes the deterministic baseline in
`tests/fixtures/assurance/contracts/baseline`. `contracts-compare` compares the
current inventory to that baseline and writes compatibility evidence. Removed
or changed API, CLI, or configuration contracts are treated as breaking until
reviewed.

The baseline is intentionally local. It does not publish schemas to a registry
and does not imply production API stability beyond the portfolio demonstration.
