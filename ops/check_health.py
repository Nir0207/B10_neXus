from __future__ import annotations

import socket
import sys
from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True, slots=True)
class CollectorEndpoint:
    host: str
    port: int


def _can_connect(endpoint: CollectorEndpoint, timeout_seconds: float = 1.5) -> bool:
    try:
        with socket.create_connection((endpoint.host, endpoint.port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def main() -> int:
    grpc_endpoint = CollectorEndpoint(
        host=getenv("OTEL_COLLECTOR_HOST", "127.0.0.1"),
        port=int(getenv("OTEL_COLLECTOR_GRPC_PORT", "4317")),
    )
    http_endpoint = CollectorEndpoint(
        host=getenv("OTEL_COLLECTOR_HOST", "127.0.0.1"),
        port=int(getenv("OTEL_COLLECTOR_HTTP_PORT", "4318")),
    )
    grpc_ready = _can_connect(grpc_endpoint)
    http_ready = _can_connect(http_endpoint)

    print(
        f"collector grpc={grpc_endpoint.host}:{grpc_endpoint.port} ready={grpc_ready} "
        f"http={http_endpoint.host}:{http_endpoint.port} ready={http_ready}"
    )
    return 0 if grpc_ready and http_ready else 1


if __name__ == "__main__":
    sys.exit(main())
