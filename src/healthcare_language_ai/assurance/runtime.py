"""Bounded local runtime smoke tests."""

from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from healthcare_language_ai.assurance.contracts import RuntimeSmokeReport
from healthcare_language_ai.assurance.inventory import checksum_data


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_get(url: str, timeout: float = 2.0) -> tuple[int, dict[str, str], str]:
    request = Request(url, headers={"User-Agent": "hla-local-smoke"})
    with urlopen(request, timeout=timeout) as response:
        return (
            response.status,
            dict(response.headers),
            response.read(2048).decode("utf-8", "ignore"),
        )


def _http_post_json(
    url: str, payload: dict[str, object], timeout: float = 2.0
) -> tuple[int, dict[str, str], dict[str, object]]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "hla-local-smoke"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read(4096).decode("utf-8", "ignore"))
        return response.status, dict(response.headers), body


def run_api_smoke(host: str, port: int, timeout: int, output_dir: Path) -> RuntimeSmokeReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_port = free_port() if port == 0 else port
    started = time.monotonic()
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "healthcare_language_ai",
            "api-run",
            "--host",
            host,
            "--port",
            str(selected_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    live = "failed"
    ready = "failed"
    headers = "failed"
    http_status = "failed"
    synthetic_query = "failed"
    prohibited_query = "failed"
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                status, response_headers, _ = _http_get(
                    f"http://{host}:{selected_port}/health/live"
                )
                if status == 200:
                    live = "passed"
                    normalised_headers = {
                        key.lower(): value for key, value in response_headers.items()
                    }
                    headers = (
                        "passed"
                        if normalised_headers.get("x-content-type-options") == "nosniff"
                        else "failed"
                    )
                    break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.25)
        try:
            ready = (
                "passed"
                if _http_get(f"http://{host}:{selected_port}/health/ready")[0] == 200
                else "failed"
            )
            http_status = (
                "passed"
                if _http_get(f"http://{host}:{selected_port}/api/v1/system")[0] == 200
                else "failed"
            )
            synthetic_status, _, synthetic_body = _http_post_json(
                f"http://{host}:{selected_port}/api/v1/query",
                {
                    "query_text": "What follow-up is described in the synthetic discharge note?",
                    "portfolio_demo_mode": True,
                },
            )
            synthetic_query = (
                "passed"
                if synthetic_status == 200 and "answer_status" in synthetic_body
                else "failed"
            )
            refusal_status, _, refusal_body = _http_post_json(
                f"http://{host}:{selected_port}/api/v1/query",
                {"query_text": "diagnose this condition", "portfolio_demo_mode": True},
            )
            prohibited_query = (
                "passed"
                if refusal_status == 200 and "refusal" in str(refusal_body.get("answer_status", ""))
                else "failed"
            )
        except (URLError, TimeoutError, ConnectionError):
            pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
            termination = "passed"
        except subprocess.TimeoutExpired:
            process.kill()
            termination = "failed"
    overall = (
        "passed"
        if live
        == ready
        == http_status
        == headers
        == synthetic_query
        == prohibited_query
        == termination
        == "passed"
        else "failed"
    )
    report = RuntimeSmokeReport(
        smoke_run_id="SMOKEAPI-" + checksum_data([host, selected_port, overall])[:24],
        component="api",
        process_started=True,
        local_host=host,
        local_port=selected_port,
        liveness_status=live,
        readiness_status=ready,
        http_smoke_status=http_status,
        synthetic_query_status=synthetic_query,
        prohibited_query_refusal_status=prohibited_query,
        security_header_status=headers,
        process_termination_status=termination,
        duration_seconds=round(time.monotonic() - started, 3),
        overall_status=overall,
        output_path=(output_dir / "api-smoke-report.json").as_posix(),
    )
    (output_dir / "api-smoke-report.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return report


def run_dashboard_smoke(host: str, port: int, timeout: int, output_dir: Path) -> RuntimeSmokeReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_port = free_port() if port == 0 else port
    started = time.monotonic()
    process = subprocess.Popen(
        [
            "python3",
            "-m",
            "streamlit",
            "run",
            "dashboard/Home.py",
            "--server.address",
            host,
            "--server.port",
            str(selected_port),
            "--server.headless",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    http_status = "failed"
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                status, _, _ = _http_get(f"http://{host}:{selected_port}/")
                if status < 500:
                    http_status = "passed"
                    break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.5)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
            termination = "passed"
        except subprocess.TimeoutExpired:
            process.kill()
            termination = "failed"
    overall = "passed" if http_status == "passed" and termination == "passed" else "failed"
    report = RuntimeSmokeReport(
        smoke_run_id="SMOKEDASH-" + checksum_data([host, selected_port, overall])[:24],
        component="dashboard",
        process_started=True,
        local_host=host,
        local_port=selected_port,
        liveness_status=http_status,
        http_smoke_status=http_status,
        process_termination_status=termination,
        duration_seconds=round(time.monotonic() - started, 3),
        overall_status=overall,
        output_path=(output_dir / "dashboard-smoke-report.json").as_posix(),
    )
    (output_dir / "dashboard-smoke-report.json").write_text(
        report.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return report


def write_expected_smoke_fixtures(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api-smoke-expected.json").write_text(
        json.dumps({"component": "api", "browser_interaction_performed": False}, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "dashboard-smoke-expected.json").write_text(
        json.dumps({"component": "dashboard", "browser_interaction_performed": False}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "smoke-contract.json").write_text(
        json.dumps({"runtime_smoke_version": "1.0.0", "localhost_only": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(
        "# Runtime Smoke Fixture\n\nExpected bounded local smoke-test contract.\n",
        encoding="utf-8",
    )
