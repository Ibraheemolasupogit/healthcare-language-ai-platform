"""Compatibility comparison for local contract inventories."""

from __future__ import annotations

import json
from pathlib import Path

from healthcare_language_ai.assurance.contracts import CompatibilityReport, ContractChange
from healthcare_language_ai.assurance.inventory import (
    build_baseline,
    checksum_data,
    generate_contract_inventory,
)


def _load_records(path: Path) -> dict[str, dict[str, object]]:
    return {row["contract_id"]: row for row in json.loads(path.read_text(encoding="utf-8"))}


def compare_contracts(baseline_dir: Path, output_dir: Path) -> CompatibilityReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_records = _load_records(baseline_dir / "contract-inventory.json")
    current = generate_contract_inventory()
    current_records = {record.contract_id: record.model_dump(mode="json") for record in current}
    baseline = json.loads((baseline_dir / "baseline-manifest.json").read_text(encoding="utf-8"))
    current_baseline = build_baseline(current)
    changes: list[ContractChange] = []
    for contract_id in sorted(current_records.keys() - baseline_records.keys()):
        changes.append(
            ContractChange(
                change_id="CHG-" + checksum_data({"add": contract_id})[:16],
                contract_id=contract_id,
                change_type="added",
                after_value=str(current_records[contract_id].get("checksum", "")),
                compatibility="backward_compatible",
                reason=(
                    "Adding a contract is backward compatible unless it replaces a stable contract."
                ),
            )
        )
    for contract_id in sorted(baseline_records.keys() - current_records.keys()):
        compatibility = (
            "breaking"
            if str(contract_id).startswith(("api_route:", "cli:", "config:"))
            else "unknown"
        )
        changes.append(
            ContractChange(
                change_id="CHG-" + checksum_data({"remove": contract_id})[:16],
                contract_id=contract_id,
                change_type="removed",
                before_value=str(baseline_records[contract_id].get("checksum", "")),
                compatibility=compatibility,
                reason="Removing an existing stable contract is breaking for API, CLI and config.",
            )
        )
    for contract_id in sorted(set(current_records).intersection(baseline_records)):
        before = str(baseline_records[contract_id].get("checksum", ""))
        after = str(current_records[contract_id].get("checksum", ""))
        if before == after:
            continue
        compatibility = "unknown"
        if contract_id.startswith("json_schema:") or contract_id.startswith("pydantic:"):
            compatibility = "unknown"
        if contract_id.startswith(("api_route:", "cli:", "config:")):
            compatibility = "breaking"
        changes.append(
            ContractChange(
                change_id="CHG-" + checksum_data({"change": contract_id, "after": after})[:16],
                contract_id=contract_id,
                change_type="changed",
                before_value=before,
                after_value=after,
                compatibility=compatibility,
                reason=(
                    "Stable contract checksum changed; detailed field diff is "
                    "required for release approval."
                ),
            )
        )
    breaking = [change for change in changes if change.compatibility == "breaking"]
    report = CompatibilityReport(
        compatibility_run_id="COMPAT-"
        + checksum_data([item.model_dump() for item in changes])[:24],
        baseline_id=str(baseline["baseline_id"]),
        current_inventory_id=current_baseline.baseline_id,
        added_contract_count=sum(change.change_type == "added" for change in changes),
        removed_contract_count=sum(change.change_type == "removed" for change in changes),
        changed_contract_count=sum(change.change_type == "changed" for change in changes),
        backward_compatible_change_count=sum(
            change.compatibility == "backward_compatible" for change in changes
        ),
        conditionally_compatible_change_count=sum(
            change.compatibility == "conditionally_compatible" for change in changes
        ),
        breaking_change_count=len(breaking),
        unknown_change_count=sum(change.compatibility == "unknown" for change in changes),
        api_breaking_change_count=sum(
            change.compatibility == "breaking" and change.contract_id.startswith("api_route:")
            for change in changes
        ),
        cli_breaking_change_count=sum(
            change.compatibility == "breaking" and change.contract_id.startswith("cli:")
            for change in changes
        ),
        configuration_breaking_change_count=sum(
            change.compatibility == "breaking" and change.contract_id.startswith("config:")
            for change in changes
        ),
        overall_compatibility_status="failed" if breaking else "passed",
        changes=changes,
    )
    (output_dir / "contract-changes.json").write_text(
        json.dumps([change.model_dump(mode="json") for change in changes], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "compatibility-report.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "contract-compatibility-report.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "compatibility-manifest.json").write_text(
        json.dumps(
            {
                "compatibility_run_id": report.compatibility_run_id,
                "status": report.overall_compatibility_status,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "compatibility-report.md").write_text(
        "\n".join(
            [
                "# Contract Compatibility Report",
                "",
                f"Run ID: {report.compatibility_run_id}",
                f"Baseline ID: {report.baseline_id}",
                f"Breaking changes: {report.breaking_change_count}",
                f"Status: {report.overall_compatibility_status}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "contract-compatibility-report.md").write_text(
        "\n".join(
            [
                "# Contract Compatibility Report",
                "",
                f"Run ID: {report.compatibility_run_id}",
                f"Baseline ID: {report.baseline_id}",
                f"Breaking changes: {report.breaking_change_count}",
                f"Status: {report.overall_compatibility_status}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "# Compatibility Fixture\n\n"
        "No breaking changes are expected against the checked-in baseline.\n",
        encoding="utf-8",
    )
    return report
