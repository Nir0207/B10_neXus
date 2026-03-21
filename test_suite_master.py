#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(slots=True)
class SuiteResult:
    name: str
    command: list[str]
    returncode: int
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def run_command(name: str, command: list[str], *, cwd: Path = ROOT) -> SuiteResult:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return SuiteResult(name=name, command=command, returncode=completed.returncode, output=output)


def run_structural_checks() -> SuiteResult:
    required_dirs = [
        ROOT / "gatherers",
        ROOT / "Lake",
        ROOT / "refineries",
        ROOT / "staging",
        ROOT / "intelligence",
        ROOT / "api-gateway",
        ROOT / "ui-portal",
    ]
    issues: list[str] = []
    for directory in required_dirs:
        if not (directory / "README.md").exists():
            issues.append(f"Missing README.md in {directory.name}")
        if not (directory / "tests").exists():
            issues.append(f"Missing tests/ in {directory.name}")

    return SuiteResult(
        name="Structural Checks",
        command=["internal"],
        returncode=0 if not issues else 1,
        output="\n".join(issues) if issues else "All required README.md and tests/ folders are present.",
    )


def print_result(result: SuiteResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"[{status}] {result.name}")
    if result.output:
        print(result.output)
    print()


def main() -> int:
    suites = [
        run_structural_checks(),
        run_command("Unit Tests: Gatherers", [sys.executable, "-m", "pytest", "gatherers/tests", "-q"]),
        run_command(
            "Integration Tests: Refinery -> Postgres -> Neo4j",
            [sys.executable, "-m", "pytest", "refineries/tests", "staging/tests", "-q"],
        ),
        run_command(
            "Support Services: Lake + Intelligence",
            [sys.executable, "-m", "pytest", "Lake/tests", "intelligence/tests", "-q"],
        ),
        run_command(
            "End-to-End Tests: API Gateway mocked frontend contract",
            [sys.executable, "-m", "pytest", "api-gateway/tests/test_api.py", "api-gateway/test_gateway.py", "-q"],
        ),
        run_command(
            "Frontend Contract Tests",
            ["npm", "test", "--", "--runInBand"],
            cwd=ROOT / "ui-portal",
        ),
    ]

    for result in suites:
        print_result(result)

    failed = [result.name for result in suites if not result.passed]
    if failed:
        print("Master suite failed:")
        for name in failed:
            print(f"- {name}")
        return 1

    print("Master suite passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
