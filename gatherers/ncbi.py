from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.ops_logger import gene_context

from base import BaseGatherer


class NCBIGatherer(BaseGatherer):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        super().__init__(source_name="ncbi", base_dir=base_dir)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def fetch_geo_studies(
        self,
        gene_symbol: str,
        *,
        organ: str = "systemic",
        max_records: int = 20,
    ) -> dict[str, Any] | list[Any]:
        with gene_context(gene_symbol.upper()):
            search_data = await self.request_json(
                method="GET",
                url=f"{self.base_url}/esearch.fcgi",
                request_name=f"esearch:{gene_symbol}",
                params={
                    "db": "gds",
                    "term": f"{gene_symbol}[Gene Name]",
                    "retmode": "json",
                    "retmax": max_records,
                },
            )
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not isinstance(id_list, list) or not id_list:
                self.save_json(stem=f"{gene_symbol}_studies", organ=organ, payload=[])
                return []

            summary_data = await self.request_json(
                method="GET",
                url=f"{self.base_url}/esummary.fcgi",
                request_name=f"esummary:{gene_symbol}",
                params={
                    "db": "gds",
                    "id": ",".join(str(item) for item in id_list),
                    "retmode": "json",
                },
                expected_record_count=len(id_list),
            )
            self.save_json(stem=f"{gene_symbol}_studies", organ=organ, payload=summary_data)
            return summary_data
