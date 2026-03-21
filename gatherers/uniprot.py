from __future__ import annotations

from pathlib import Path
from typing import Any

from base import BaseGatherer


class UniProtGatherer(BaseGatherer):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        super().__init__(source_name="uniprot", base_dir=base_dir)
        self.api_url = "https://rest.uniprot.org/uniprotkb/search"

    async def fetch(self, gene_symbol: str, *, organism: str = "human") -> dict[str, Any]:
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
