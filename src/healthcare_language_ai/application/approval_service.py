"""Approval and gate summaries for retrieval and RAG evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from healthcare_language_ai.application.contracts import ApprovalResponse, QualityGateResponse


class ApprovalService:
    def __init__(self, retrieval_comparison_dir: Path, rag_evaluation_dir: Path) -> None:
        self.retrieval_comparison_dir = retrieval_comparison_dir
        self.rag_evaluation_dir = rag_evaluation_dir

    def retrieval_approval(self) -> ApprovalResponse:
        path = self.retrieval_comparison_dir / "retrieval_approval_decision.json"
        data = json.loads(path.read_text())
        return ApprovalResponse(
            approval_type="retrieval",
            approval_id=self.retrieval_comparison_dir.name,
            approval_status=str(data["approval_status"]),
            approved_for_local_synthetic_demo=bool(data["approved_for_future_rag_prototype"]),
            required_gate_count=int(data["required_gate_count"]),
            passed_required_gates=int(data["passed_required_gates"]),
            failed_required_gates=int(data["failed_required_gates"]),
            configuration=str(data["selected_configuration_id"]),
            known_failures=list(data.get("known_failures", [])),
        )

    def rag_approval(self) -> ApprovalResponse:
        data = json.loads((self.rag_evaluation_dir / "rag_approval_decision.json").read_text())
        return ApprovalResponse(
            approval_type="rag",
            approval_id=str(data["rag_evaluation_id"]),
            approval_status=str(data["approval_status"]),
            approved_for_local_synthetic_demo=bool(data["approved_for_local_synthetic_demo"]),
            required_gate_count=int(data["required_gate_count"]),
            passed_required_gates=int(data["passed_required_gates"]),
            failed_required_gates=int(data["failed_required_gates"]),
            configuration=str(data["rag_configuration"]),
            known_failures=list(data.get("known_failures", [])),
        )

    def retrieval_gates(self) -> QualityGateResponse:
        with (self.retrieval_comparison_dir / "quality_gate_matrix.csv").open(
            "r", encoding="utf-8", newline=""
        ) as stream:
            gates = [
                {
                    "configuration_id": row["configuration_id"],
                    "gate_name": row["gate"],
                    "passed": row["passed"] == "True",
                    "required": True,
                }
                for row in csv.DictReader(stream)
                if row["configuration_id"] == "REMEXP-41fd5fa127ab616f7f74cc9b"
            ]
        required = [gate for gate in gates if gate.get("required", True)]
        passed = [gate for gate in required if gate.get("passed") is True]
        return QualityGateResponse(
            gate_set="retrieval",
            required_gate_count=len(required),
            passed_required_gates=len(passed),
            failed_required_gates=len(required) - len(passed),
            gates=gates,
        )

    def rag_gates(self) -> QualityGateResponse:
        data: Any = json.loads((self.rag_evaluation_dir / "quality_gate_results.json").read_text())
        gates = data.get("gates", data if isinstance(data, list) else [])
        required = [gate for gate in gates if gate.get("required", True)]
        passed = [gate for gate in required if gate.get("passed") is True]
        return QualityGateResponse(
            gate_set="rag",
            required_gate_count=len(required),
            passed_required_gates=len(passed),
            failed_required_gates=len(required) - len(passed),
            gates=gates,
        )
