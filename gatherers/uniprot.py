from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.ops_logger import gene_context

from base import BaseGatherer


class UniProtGatherer(BaseGatherer):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        super().__init__(source_name="uniprot", base_dir=base_dir)
        self.api_url = "https://rest.uniprot.org/uniprotkb/search"

    async def fetch(self, gene_symbol: str, *, organism: str = "human") -> dict[str, Any]:
        with gene_context(gene_symbol.upper()):
            payload = await self.request_json(
                method="GET",
                url=self.api_url,
                request_name=f"gene={gene_symbol}",
                params={
                    "query": f"gene_exact:{gene_symbol} AND reviewed:true",
                    "format": "json",
                },
            )
            self.save_json(stem=gene_symbol, organ=organism, payload=payload)
            return payload
