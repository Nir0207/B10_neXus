import json
import re
import httpx
from pathlib import Path


DEFAULT_BASE_DIR = (
    Path(__file__).resolve().parents[1] / "Lake" / "data_lake" / "raw" / "uniprot"
)


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip()).strip("._")
    return safe or "unknown"


class UniProtGatherer:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else DEFAULT_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = "https://rest.uniprot.org/uniprotkb/search"

    async def fetch(self, gene_symbol: str):
        print(f"[UniProt] Fetching data for {gene_symbol}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.api_url,
                params={"query": f"gene_exact:{gene_symbol} AND reviewed:true", "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            
            output_file = self.base_dir / f"{_safe_file_stem(gene_symbol)}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            print(f"[UniProt] Saved {gene_symbol} data to {output_file}")
            return data
