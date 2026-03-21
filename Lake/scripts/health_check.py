#!/usr/bin/env python3
"""
Quick health check and diagnostic tool for BioNexus infrastructure.
"""

import subprocess
import sys
from pathlib import Path


class BioNexusHealthCheck:
    def __init__(self):
        self.workspace = Path(__file__).resolve().parent.parent
        self.project_root = self.workspace.parent
        self.compose_cmd = self._detect_compose_cmd()
        self.passed = 0
        self.failed = 0

    def _detect_compose_cmd(self):
        """Return a working Docker Compose command."""
        checks = ["docker-compose version", "docker compose version"]
        for cmd in checks:
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
            if result.returncode == 0:
                return cmd.replace(" version", "")
        return None

    def run_check(self, name, command, description=""):
        """Run a health check."""
        print(f"\n🔍 {name}")
        if description:
            print(f"   {description}")

        try:
            result = subprocess.run(command, shell=True, capture_output=True, timeout=8, text=True)
            if result.returncode == 0:
                print("   ✓ OK")
                self.passed += 1
                return True

            print("   ✗ FAILED")
            if result.stderr:
                print(f"      Error: {result.stderr[:160].strip()}")
            self.failed += 1
            return False
        except subprocess.TimeoutExpired:
            print("   ✗ TIMEOUT")
            self.failed += 1
            return False
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            self.failed += 1
            return False

    def check_docker(self):
        """Check Docker tooling availability."""
        print("\n🐳 Docker Runtime")

        self.run_check(
            "Docker CLI",
            "docker --version",
            "Checking Docker CLI installation",
        )

        self.run_check(
            "Docker Daemon",
            "docker info > /dev/null 2>&1",
            "Checking Docker daemon connectivity",
        )

        if self.compose_cmd:
            self.run_check(
                "Docker Compose",
                f"{self.compose_cmd} version",
                "Checking compose command",
            )
        else:
            print("\n🔍 Docker Compose")
            print("   ✗ FAILED")
            print("      Error: neither 'docker-compose' nor 'docker compose' was found")
            self.failed += 1

    def _run_compose_check(self, name, compose_subcommand, description=""):
        if not self.compose_cmd:
            print(f"\n🔍 {name}")
            print("   ✗ FAILED")
            print("      Error: compose command is unavailable")
            self.failed += 1
            return False
        return self.run_check(name, f"{self.compose_cmd} {compose_subcommand}", description)

    def check_files(self):
        """Check required files exist."""
        print("\n📋 File Structure")
        file_checks = {
            "docker-compose.yml": [self.workspace / "docker-compose.yml"],
            ".env": [self.workspace / ".env", self.project_root / ".env"],
            "Makefile": [self.workspace / "Makefile"],
            "requirements.txt": [self.workspace / "requirements.txt"],
            "scripts/duckdb_lake_init.py": [self.workspace / "scripts" / "duckdb_lake_init.py"],
            "init-scripts/postgres-init.sql": [self.workspace / "init-scripts" / "postgres-init.sql"],
            "init-scripts/neo4j-init.cypher": [self.workspace / "init-scripts" / "neo4j-init.cypher"],
            "init-scripts/mongodb-init.js": [self.workspace / "init-scripts" / "mongodb-init.js"],
        }

        for label, candidates in file_checks.items():
            found = next((candidate for candidate in candidates if candidate.exists()), None)
            if found:
                print(f"   ✓ {label} ({found})")
                self.passed += 1
            else:
                print(f"   ✗ {label} MISSING")
                self.failed += 1

    def check_services(self):
        """Check Docker services status."""
        print("\n🐳 Docker Services")
        self._run_compose_check(
            "Docker Compose Services",
            "ps",
            "Checking service status",
        )

    def check_databases(self):
        """Check database connectivity."""
        print("\n🗄️  Database Connectivity")

        self._run_compose_check(
            "Postgres",
            "exec -T postgres pg_isready -U bionexus_user",
            "PostgreSQL with pgvector",
        )

        self.run_check(
            "Neo4j",
            "curl -s http://localhost:7474/db/neo4j/label/ > /dev/null",
            "Neo4j Knowledge Graph",
        )

        self._run_compose_check(
            "MongoDB",
            "exec -T mongodb mongosh --authenticationDatabase admin -u bionexus_admin -p bionexus_dev_password --eval 'db.adminCommand(\"ping\")' > /dev/null 2>&1",
            "MongoDB Document Store",
        )

    def check_duckdb(self):
        """Check DuckDB lake."""
        print("\n🦆 DuckDB Lake")
        db_path = self.workspace / "data_lake" / "bionexus.duckdb"

        if db_path.exists():
            print(f"   ✓ DuckDB initialized: {db_path}")
            self.passed += 1
        else:
            print("   ! DuckDB not initialized yet")
            print("      Run: python scripts/duckdb_lake_init.py")

    def check_python(self):
        """Check Python environment."""
        print("\n🐍 Python Environment")

        self.run_check(
            "Python 3.9+",
            "python3 -c 'import sys; assert sys.version_info >= (3, 9), \"Python 3.9+ required\"'",
            "Python version check",
        )

        packages = ["duckdb", "polars", "pandas", "pydantic", "requests"]
        for pkg in packages:
            self.run_check(
                f"Package: {pkg}",
                f"python3 -c 'import {pkg}'",
                f"Checking {pkg} installation",
            )

    def summary(self):
        """Print summary."""
        print("\n" + "=" * 60)
        print("📊 Health Check Summary")
        print("=" * 60)
        print(f"✓ Passed: {self.passed}")
        print(f"✗ Failed: {self.failed}")
        print("=" * 60)

        if self.failed == 0:
            print("\n✅ All systems operational!")
            return 0

        print(f"\n⚠️  {self.failed} issue(s) detected. See above for details.")
        return 1

    def run_all(self):
        """Run all checks."""
        print("🧬 BioNexus Infrastructure Health Check")
        print("=" * 60)

        self.check_files()
        self.check_docker()
        self.check_services()
        self.check_databases()
        self.check_duckdb()
        self.check_python()

        return self.summary()


if __name__ == "__main__":
    checker = BioNexusHealthCheck()
    sys.exit(checker.run_all())
