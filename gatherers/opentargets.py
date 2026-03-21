from __future__ import annotations

from pathlib import Path
from typing import Any

from base import BaseGatherer


class OpenTargetsGatherer(BaseGatherer):
    def __init__(self, base_dir: str | Path | None = None) -> None:
        super().__init__(source_name="opentargets", base_dir=base_dir)
        self.api_url = "https://api.platform.opentargets.org/api/v4/graphql"

    async def search_disease(self, query_string: str, *, size: int = 5) -> dict[str, Any]:
        query = """
        query SearchDiseases($queryString: String!, $size: Int!) {
          search(queryString: $queryString, entityNames: ["disease"], page: {index: 0, size: $size}) {
            hits {
              id
              entity
              name
              description
            }
          }
        }
        """
        payload = await self.request_json(
            method="POST",
            url=self.api_url,
            request_name=f"search={query_string}",
            json={"query": query, "variables": {"queryString": query_string, "size": size}},
        )
        errors = payload.get("errors", [])
        if errors:
            message = errors[0].get("message", "Unknown GraphQL error")
            raise RuntimeError(f"[OpenTargets] GraphQL error during search for {query_string}: {message}")
        return payload

    async def resolve_disease_id(self, query_string: str) -> tuple[str, str]:
        payload = await self.search_disease(query_string)
        hits = payload.get("data", {}).get("search", {}).get("hits", [])
        if not isinstance(hits, list) or not hits:
            raise RuntimeError(f"[OpenTargets] No disease hits found for {query_string}")

        top_hit = hits[0]
        disease_id = str(top_hit.get("id") or "").strip()
        disease_name = str(top_hit.get("name") or query_string).strip()
        if not disease_id:
            raise RuntimeError(f"[OpenTargets] Search response missing disease id for {query_string}")
        return disease_id, disease_name

    async def fetch_disease_evidence(
        self,
        disease_id: str,
        *,
        organ: str,
        stem: str | None = None,
        size: int = 100,
    ) -> dict[str, Any]:
        query = """
        query diseaseEvidence($diseaseId: String!, $size: Int!) {
          disease(efoId: $diseaseId) {
            id
            name
            associatedTargets(page: {index: 0, size: $size}) {
              rows {
                target {
                  id
                  approvedSymbol
                  proteinIds {
                    id
                    source
                  }
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
            request_name=f"disease={disease_id}",
            json={"query": query, "variables": {"diseaseId": disease_id, "size": size}},
        )
        errors = payload.get("errors", [])
        if errors:
            message = errors[0].get("message", "Unknown GraphQL error")
            raise RuntimeError(f"[OpenTargets] GraphQL error for {disease_id}: {message}")
        if payload.get("data", {}).get("disease") is None:
            raise RuntimeError(f"[OpenTargets] Disease payload was null for {disease_id}")
        self.save_json(stem=stem or f"{disease_id}_evidence", organ=organ, payload=payload)
        return payload

    async def fetch_disease_evidence_by_query(
        self,
        query_string: str,
        *,
        organ: str,
        size: int = 100,
    ) -> dict[str, Any]:
        disease_id, _disease_name = await self.resolve_disease_id(query_string)
        return await self.fetch_disease_evidence(
            disease_id,
            organ=organ,
            stem=f"{disease_id}_evidence",
            size=size,
        )

    @staticmethod
    def extract_top_target_genes(payload: dict[str, Any], *, limit: int) -> list[str]:
        rows = payload.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", [])
        if not isinstance(rows, list):
            return []

        gene_symbols: list[str] = []
        seen: set[str] = set()
        for row in rows:
            symbol = str((row.get("target") or {}).get("approvedSymbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            gene_symbols.append(symbol)
            if len(gene_symbols) >= limit:
                break
        return gene_symbols

    async def fetch_liver_evidence(self, efo_id: str = "EFO_0000572") -> dict[str, Any]:
        return await self.fetch_disease_evidence(efo_id, organ="liver")
