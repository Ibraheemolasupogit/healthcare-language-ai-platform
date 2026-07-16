"""Validate generated demo reports."""

from pathlib import Path

from healthcare_language_ai.demonstration.contracts import DemoSession


def validate_demo_dir(demo_dir: Path) -> list[str]:
    failures: list[str] = []
    required = [
        "demo-session.json",
        "demo-results.csv",
        "demo-summary.md",
        "demo-trace-index.json",
        "README.md",
    ]
    for name in required:
        if not (demo_dir / name).exists():
            failures.append(f"missing {name}")
    if not failures:
        session = DemoSession.model_validate_json((demo_dir / "demo-session.json").read_text())
        if session.failed_scenarios:
            failures.append("demo session contains failed scenarios")
    return failures
