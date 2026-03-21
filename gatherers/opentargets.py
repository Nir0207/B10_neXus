import json
import re
import httpx
from pathlib import Path


DEFAULT_BASE_DIR = (
    Path(__file__).resolve().parents[1] / "Lake" / "data_lake" / "raw" / "opentargets"
)


def _safe_file_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value.strip()).strip("._")
    return safe or "unknown"


class OpenTargetsGatherer:
    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir is not None else DEFAULT_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.api_url = "https://api.platform.opentargets.org/api/v4/graphql"

    async def fetch_liver_evidence(self, efo_id: str = "EFO_0000572"):
        print(f"[OpenTargets] Fetching Target-Disease Evidence for disease {efo_id} (Liver disease)...")
        # Query specifically for Target-Disease Evidence including overall score and sources
        query = """
        query liverDiseaseEvidence($efoId: String!) {
          disease(efoId: $efoId) {
            id
            name
            associatedTargets(page: {index: 0, size: 100}) {
              rows {
                target {
                  id
                  approvedSymbol
                }
                score
                datasourceScores {
                  id
                  score
                }
              }
            }
          }
        }
        """
        
        variables = {"efoId": efo_id}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.api_url,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("errors"):
                error_message = data["errors"][0].get("message", "Unknown GraphQL error")
                raise RuntimeError(f"[OpenTargets] GraphQL error for {efo_id}: {error_message}")
            
            output_file = self.base_dir / f"{_safe_file_stem(efo_id)}_evidence.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            print(f"[OpenTargets] Saved {efo_id} data to {output_file}")
            return data
