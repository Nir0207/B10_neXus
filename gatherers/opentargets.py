from __future__ import annotations

from pathlib import Path
from typing import Any

from base import BaseGatherer


class OpenTargetsGatherer(BaseGatherer):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        super().__init__(source_name="opentargets", base_dir=base_dir)
        self.api_url = "https://api.platform.opentargets.org/api/v4/graphql"

    async def fetch_liver_evidence(self, efo_id: str = "EFO_0000572") -> dict[str, Any]:
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
        payload = await self.request_json(
            method="POST",
            url=self.api_url,
            request_name=f"disease={efo_id}",
            json={"query": query, "variables": {"efoId": efo_id}},
        )
        errors = payload.get("errors", [])
        if errors:
            message = errors[0].get("message", "Unknown GraphQL error")
            raise RuntimeError(f"[OpenTargets] GraphQL error for {efo_id}: {message}")
        self.save_json(stem=f"{efo_id}_evidence", organ="liver", payload=payload)
        return payload
