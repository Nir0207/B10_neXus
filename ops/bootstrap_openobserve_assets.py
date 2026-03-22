#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://localhost:5080"
DEFAULT_ORG = "default"
DEFAULT_USERNAME = "root@bionexus.local"
DEFAULT_PASSWORD = "BioNexusOps123!"
DEFAULT_STREAM = "bionexus_app"
DEFAULT_DASHBOARD_TITLE = "BioNexus Ops"


@dataclass(frozen=True, slots=True)
class BootstrapSettings:
    base_url: str
    org_id: str
    username: str
    password: str
    stream_name: str
    dashboard_title: str

    @classmethod
    def from_env(cls) -> "BootstrapSettings":
        return cls(
            base_url=os.getenv("OPENOBSERVE_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            org_id=os.getenv("OPENOBSERVE_ORG", DEFAULT_ORG),
            username=os.getenv("OPENOBSERVE_USERNAME", DEFAULT_USERNAME),
            password=os.getenv("OPENOBSERVE_PASSWORD", DEFAULT_PASSWORD),
            stream_name=os.getenv("OPENOBSERVE_LOG_STREAM", DEFAULT_STREAM),
            dashboard_title=os.getenv("OPENOBSERVE_DASHBOARD_TITLE", DEFAULT_DASHBOARD_TITLE),
        )

    def authorization_header(self) -> str:
        token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def logs_url(self) -> str:
        params = {
            "stream_type": "logs",
            "stream": self.stream_name,
            "period": "15m",
            "refresh": "0",
            "fn_editor": "false",
            "defined_schemas": "user_defined_schema",
            "org_identifier": self.org_id,
            "quick_mode": "false",
            "show_histogram": "true",
            "logs_visualize_toggle": "logs",
        }
        return (
            f"{self.base_url}/web/logs?"
            f"{urlencode(params)}"
        )

    def rum_url(self) -> str:
        return f"{self.base_url}/web/rum?org_identifier={quote(self.org_id)}"

    def dashboards_url(self) -> str:
        return (
            f"{self.base_url}/web/dashboards?"
            f"{urlencode({'org_identifier': self.org_id, 'folder': 'default'})}"
        )

    def dashboard_view_url(self, dashboard_id: str) -> str:
        params = {
            "org_identifier": self.org_id,
            "dashboard": dashboard_id,
            "folder": "default",
            "tab": "overview",
            "refresh": "Off",
            "period": "15m",
            "print": "false",
        }
        return (
            f"{self.base_url}/web/dashboards/view?"
            f"{urlencode(params)}"
        )


class OpenObserveBootstrapClient:
    def __init__(self, settings: BootstrapSettings) -> None:
        self.settings = settings

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Authorization": self.settings.authorization_header()}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            url=f"{self.settings.base_url}{path}",
            method=method,
            headers=headers,
            data=body,
        )
        with urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8")
        return json.loads(content) if content else {}

    def wait_until_ready(self, *, timeout_seconds: float = 60.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                self._request("GET", f"/api/{self.settings.org_id}/users")
                return
            except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(1.0)
        raise RuntimeError("OpenObserve did not become ready in time") from last_error

    def list_dashboards(self) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            f"/api/{self.settings.org_id}/dashboards?title={quote(self.settings.dashboard_title)}",
        )
        dashboards = response.get("dashboards", [])
        return dashboards if isinstance(dashboards, list) else []

    def create_dashboard(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/api/{self.settings.org_id}/dashboards", payload)

    def update_dashboard(
        self,
        *,
        dashboard_id: str,
        folder_id: str,
        dashboard_hash: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        query = urlencode(
            {
                "folder": folder_id,
                **({"hash": dashboard_hash} if dashboard_hash else {}),
            }
        )
        return self._request(
            "PUT",
            f"/api/{self.settings.org_id}/dashboards/{dashboard_id}?{query}",
            payload,
        )

    def ensure_dashboard(self) -> tuple[str, bool]:
        payload = build_dashboard_payload(self.settings)
        existing = next(
            (
                item
                for item in self.list_dashboards()
                if item.get("title") == self.settings.dashboard_title
            ),
            None,
        )
        if existing is None:
            response = self.create_dashboard(payload)
            dashboard = response.get("v8") or response
            dashboard_id = str(dashboard.get("dashboardId", ""))
            return dashboard_id, True

        dashboard_id = str(existing.get("dashboard_id") or existing.get("dashboardId") or "")
        folder_id = str(existing.get("folder_id") or "default")
        dashboard_hash = existing.get("hash")
        self.update_dashboard(
            dashboard_id=dashboard_id,
            folder_id=folder_id,
            dashboard_hash=str(dashboard_hash) if dashboard_hash is not None else None,
            payload=payload,
        )
        return dashboard_id, False


def build_dashboard_payload(settings: BootstrapSettings) -> dict[str, Any]:
    markdown = "\n".join(
        [
            "# BioNexus Ops",
            "",
            "Direct links:",
            f'- [Open BioNexus logs]({settings.logs_url()})',
            f'- [Open BioNexus RUM]({settings.rum_url()})',
            f'- [Open dashboards list]({settings.dashboards_url()})',
            "",
            f"Default stream: `{settings.stream_name}`",
            "",
            "Quick SQL:",
            "```sql",
            f'SELECT * FROM "{settings.stream_name}" ORDER BY _timestamp DESC LIMIT 20',
            "```",
            "",
            "Errors only:",
            "```sql",
            f'SELECT * FROM "{settings.stream_name}" WHERE severity = \'ERROR\' ORDER BY _timestamp DESC LIMIT 20',
            "```",
            "",
            "RUM only:",
            "```sql",
            f'SELECT * FROM "{settings.stream_name}" WHERE rum_metric_name IS NOT NULL ORDER BY _timestamp DESC LIMIT 20',
            "```",
        ]
    )
    return {
        "title": settings.dashboard_title,
        "description": "Local observability entrypoint for BioNexus.",
        "defaultDatetimeDuration": {
            "type": "relative",
            "relativeTimePeriod": "15m",
        },
        "tabs": [
            {
                "tabId": "overview",
                "name": "Overview",
                "panels": [
                    {
                        "id": "overview-md",
                        "type": "markdown",
                        "title": "BioNexus Ops Guide",
                        "description": "Quick portal usage guide",
                        "layout": {"x": 0, "y": 0, "w": 96, "h": 16, "i": 1},
                        "config": {"show_legends": False},
                        "queries": [],
                        "markdownContent": markdown,
                    }
                ],
            }
        ],
    }


def main() -> int:
    settings = BootstrapSettings.from_env()
    client = OpenObserveBootstrapClient(settings)
    try:
        client.wait_until_ready()
        dashboard_id, created = client.ensure_dashboard()
    except Exception as exc:
        print(f"failed to bootstrap OpenObserve assets: {exc}", file=sys.stderr)
        return 1

    action = "created" if created else "updated"
    print(f"{action} dashboard: {settings.dashboard_title}")
    print(f"dashboard_url={settings.dashboard_view_url(dashboard_id)}")
    print(f"logs_url={settings.logs_url()}")
    print(f"rum_url={settings.rum_url()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
