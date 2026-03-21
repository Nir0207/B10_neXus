import json
import re
import httpx
from pathlib import Path


DEFAULT_BASE_DIR = (
    Path(__file__).resolve().parents[1] / "Lake" / "data_lake" / "raw" / "ncbi"
)


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip()).strip("._")
    return safe or "unknown"


class NCBIGatherer:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else DEFAULT_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    async def fetch_geo_studies(self, gene_symbol: str):
        print(f"[NCBI] Fetching study metadata for {gene_symbol}...")
        
        # We will query the gds (GEO DataSets) database
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Search for IDs
            search_url = f"{self.base_url}/esearch.fcgi"
            search_params = {
                "db": "gds",
                "term": f"{gene_symbol}[Gene Name]",
                "retmode": "json",
                "retmax": 20
            }
            
            search_resp = await client.get(search_url, params=search_params)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                print(f"[NCBI] No GEO studies found for {gene_symbol}")
                # Save empty array
                self._save_data(gene_symbol, [])
                return []
            
            print(f"[NCBI] Found {len(id_list)} studies for {gene_symbol}. Fetching summaries...")
            
            # Step 2: Fetch summaries for IDs
            summary_url = f"{self.base_url}/esummary.fcgi"
            summary_params = {
                "db": "gds",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            
            summary_resp = await client.get(summary_url, params=summary_params)
            summary_resp.raise_for_status()
            summary_data = summary_resp.json()
            
            self._save_data(gene_symbol, summary_data)
            return summary_data
            
    def _save_data(self, gene_symbol: str, data: dict | list):
        safe_gene_symbol = _safe_file_stem(gene_symbol)
        output_file = self.base_dir / f"{safe_gene_symbol}_studies.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[NCBI] Saved GEO studies for {gene_symbol} to {output_file}")
