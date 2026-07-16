"""Deterministic local contract inventory generation."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from healthcare_language_ai.api.app import create_app
from healthcare_language_ai.application import contracts as application_contracts
from healthcare_language_ai.assurance.contracts import ContractBaseline, ContractInventoryRecord
from healthcare_language_ai.config import AppSettings
from healthcare_language_ai.demonstration import contracts as demo_contracts
from healthcare_language_ai.observability import contracts as observability_contracts


def stable_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def checksum_data(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record(
    contract_id: str, contract_type: str, location: str, payload: Any
) -> ContractInventoryRecord:
    return ContractInventoryRecord(
        contract_id=contract_id,
        contract_type=contract_type,
        location=location,
        owner_module=location.split(":")[0],
        introduced_milestone="M11" if contract_type.startswith("assurance") else "M10",
        stability="stable",
        checksum=checksum_data(payload),
    )


def pydantic_models() -> list[type[BaseModel]]:
    modules = [application_contracts, observability_contracts, demo_contracts]
    models: list[type[BaseModel]] = []
    for module in modules:
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, BaseModel) and value is not BaseModel:
                models.append(value)
    return sorted(set(models), key=lambda model: f"{model.__module__}.{model.__name__}")


def cli_command_names(cli_path: Path = Path("src/healthcare_language_ai/cli.py")) -> list[str]:
    tree = ast.parse(cli_path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "command"
            ):
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    names.append(str(decorator.args[0].value))
                else:
                    names.append(node.name.replace("_", "-"))
    return sorted(set(names))


def generate_contract_inventory() -> list[ContractInventoryRecord]:
    app = create_app()
    records: list[ContractInventoryRecord] = []
    for model in pydantic_models():
        schema = model.model_json_schema()
        records.append(
            _record(
                f"pydantic:{model.__module__}.{model.__name__}",
                "pydantic_model",
                f"{model.__module__}:{model.__name__}",
                schema,
            )
        )
    for schema_path in sorted(Path("schemas").glob("**/*.schema.json")):
        records.append(
            _record(
                f"json_schema:{schema_path.as_posix()}",
                "json_schema",
                schema_path.as_posix(),
                json.loads(schema_path.read_text(encoding="utf-8")),
            )
        )
    for path, methods in sorted(
        (path, sorted(spec.keys())) for path, spec in app.openapi()["paths"].items()
    ):
        records.append(_record(f"api_route:{path}", "api_route", "api.openapi", {path: methods}))
    for command in cli_command_names():
        records.append(
            _record(
                f"cli:{command}",
                "cli_command",
                "src/healthcare_language_ai/cli.py",
                command,
            )
        )
    settings_schema = AppSettings.model_json_schema()
    for section in sorted(settings_schema.get("properties", {})):
        records.append(
            _record(f"config:{section}", "configuration_section", "AppSettings", section)
        )
    prompt_path = Path("tests/fixtures/rag/runs/RAG-515e2c68be10e720b613e874/prompt_records.jsonl")
    if prompt_path.exists():
        for line in prompt_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                prompt_checksum = checksum_data(data)
                records.append(
                    _record(
                        f"prompt:{data['prompt_id']}:{data['prompt_version']}:{prompt_checksum[:16]}",
                        "prompt_contract",
                        prompt_path.as_posix(),
                        data,
                    )
                )
    return sorted(records, key=lambda item: item.contract_id)


def build_baseline(records: list[ContractInventoryRecord]) -> ContractBaseline:
    payload = [record.model_dump(mode="json") for record in records]
    baseline_id = "CONTRACTBASE-" + checksum_data(payload)[:24]
    return ContractBaseline(
        baseline_id=baseline_id,
        contract_count=len(records),
        pydantic_contract_count=sum(item.contract_type == "pydantic_model" for item in records),
        json_schema_count=sum(item.contract_type == "json_schema" for item in records),
        api_route_count=sum(item.contract_type == "api_route" for item in records),
        cli_command_count=sum(item.contract_type == "cli_command" for item in records),
        prompt_contract_count=sum(item.contract_type == "prompt_contract" for item in records),
        configuration_section_count=sum(
            item.contract_type == "configuration_section" for item in records
        ),
        stable_contract_count=sum(item.stability == "stable" for item in records),
        experimental_contract_count=sum(item.stability == "experimental" for item in records),
        deprecated_contract_count=sum(item.deprecated for item in records),
        checksum=checksum_data(payload),
    )


def write_contract_inventory(output_dir: Path) -> ContractBaseline:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = generate_contract_inventory()
    baseline = build_baseline(records)
    (output_dir / "contract-inventory.json").write_text(
        json.dumps([record.model_dump(mode="json") for record in records], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "baseline-manifest.json").write_text(
        baseline.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    app = create_app()
    (output_dir / "openapi.json").write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    routes = [
        {"path": getattr(route, "path", ""), "methods": sorted(getattr(route, "methods", []))}
        for route in app.routes
        if getattr(route, "path", "")
    ]
    (output_dir / "routes.json").write_text(
        json.dumps(routes, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "cli-commands.json").write_text(
        json.dumps(cli_command_names(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "configuration-schema.json").write_text(
        json.dumps(AppSettings.model_json_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "pydantic-contracts.json").write_text(
        json.dumps(
            {
                f"{model.__module__}.{model.__name__}": model.model_json_schema()
                for model in pydantic_models()
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    schema_inventory = sorted(path.as_posix() for path in Path("schemas").glob("**/*.schema.json"))
    (output_dir / "json-schema-inventory.json").write_text(
        json.dumps(schema_inventory, indent=2) + "\n", encoding="utf-8"
    )
    prompt_records = [
        record.model_dump(mode="json")
        for record in records
        if record.contract_type == "prompt_contract"
    ]
    (output_dir / "prompt-contracts.json").write_text(
        json.dumps(prompt_records, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "# Contract Baseline\n\nDeterministic Milestone 11 local contract baseline.\n",
        encoding="utf-8",
    )
    return baseline
