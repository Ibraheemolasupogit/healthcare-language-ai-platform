"""Offline dependency inventory and SBOM evidence."""

from __future__ import annotations

import importlib.metadata
import json
import tomllib
from pathlib import Path

from healthcare_language_ai.assurance.contracts import (
    DependencyInventory,
    DependencyRecord,
    SbomDocument,
)
from healthcare_language_ai.assurance.inventory import checksum_data

PROHIBITED_RUNTIME = {
    "snowflake-connector-python",
    "databricks-sdk",
    "pyspark",
    "torch",
    "sentence-transformers",
}


def direct_dependencies() -> set[str]:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"].get("dependencies", [])
    names = {dep.split("<")[0].split(">")[0].split("=")[0].strip().lower() for dep in deps}
    return names


def build_dependency_inventory() -> DependencyInventory:
    direct = direct_dependencies()
    records: list[DependencyRecord] = []
    for dist in sorted(
        importlib.metadata.distributions(), key=lambda item: item.metadata["Name"].lower()
    ):
        name = dist.metadata["Name"]
        normalized = name.lower()
        records.append(
            DependencyRecord(
                package_name=name,
                installed_version=dist.version,
                dependency_group="runtime" if normalized in direct else "transitive",
                direct=normalized in direct,
                runtime=True,
                license_metadata=dist.metadata.get("License", ""),
                source_metadata=dist.metadata.get("Home-page", ""),
            )
        )
    violations = sorted(PROHIBITED_RUNTIME.intersection(direct))
    return DependencyInventory(
        dependency_inventory_id="DEPINV-"
        + checksum_data([record.model_dump() for record in records])[:24],
        records=records,
        dependency_count=len(records),
        direct_dependency_count=sum(record.direct for record in records),
        development_dependency_count=0,
        policy_violations=violations,
    )


def write_dependency_inventory(output_dir: Path) -> DependencyInventory:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_dependency_inventory()
    (output_dir / "dependency-inventory.json").write_text(
        inventory.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "dependency-policy-results.json").write_text(
        json.dumps(
            {
                "policy_violations": inventory.policy_violations,
                "status": "passed" if not inventory.policy_violations else "failed",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return inventory


def write_sbom(output_dir: Path) -> SbomDocument:
    inventory = build_dependency_inventory()
    sbom = SbomDocument(
        sbom_id="SBOM-" + checksum_data([record.model_dump() for record in inventory.records])[:24],
        components=inventory.records,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sbom.json").write_text(sbom.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return sbom
