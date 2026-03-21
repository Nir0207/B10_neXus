from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from neo4j import AsyncSession

from auth import get_current_user
from database import get_postgres_connection, get_neo4j_session
from schemas import GeneResponse, GraphNode, GraphRelationship, GraphResponse, User

try:
    import asyncpg
except ImportError:  # pragma: no cover - environment-dependent fallback
    asyncpg = None  # type: ignore[assignment]

router = APIRouter(prefix="/api/v1")


def _to_properties(value: Any) -> dict[str, Any]:
    try:
        return dict(value)
    except Exception:
        return {}


def _serialize_node(node: Any) -> GraphNode:
    if isinstance(node, dict):
        return GraphNode(**node)

    node_id: str = str(getattr(node, "element_id", getattr(node, "id", "")))
    labels_raw: Any = getattr(node, "labels", [])
    labels: list[str] = list(labels_raw) if not isinstance(labels_raw, str) else [labels_raw]
    properties: dict[str, Any] = _to_properties(node)
    return GraphNode(id=node_id, labels=labels, properties=properties)


def _serialize_relationship(relationship: Any) -> GraphRelationship:
    if isinstance(relationship, dict):
        return GraphRelationship(**relationship)

    start_node: Any = getattr(relationship, "start_node", None)
    end_node: Any = getattr(relationship, "end_node", None)
    start_node_id: str = str(getattr(start_node, "element_id", getattr(relationship, "start_node_id", "")))
    end_node_id: str = str(getattr(end_node, "element_id", getattr(relationship, "end_node_id", "")))

    return GraphRelationship(
        id=str(getattr(relationship, "element_id", getattr(relationship, "id", ""))),
        type=str(getattr(relationship, "type", "")),
        start_node=start_node_id,
        end_node=end_node_id,
        properties=_to_properties(relationship),
    )


@router.get("/genes/{id}", response_model=GeneResponse)
async def get_gene(
    id: str = Path(
        ...,
        pattern=r"^[A-Z0-9-]{6,15}$",
        description="Primary key (UniProt ID).",
    ),
    current_user: User = Depends(get_current_user),
    pg_conn: Any | None = Depends(get_postgres_connection),
) -> GeneResponse:
    del current_user
    if pg_conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Postgres connection unavailable",
        )

    try:
        row: Any | None = await pg_conn.fetchrow(
            "SELECT uniprot_id, gene_symbol, name, description, data_source FROM genes WHERE uniprot_id = $1",
            id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Gene not found")
        return GeneResponse(**dict(row))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve gene from staging proxy",
        ) from exc


@router.get("/discovery/graph", response_model=GraphResponse)
async def get_discovery_graph(
    current_user: User = Depends(get_current_user),
    neo4j_session: AsyncSession | None = Depends(get_neo4j_session),
) -> GraphResponse:
    del current_user
    if neo4j_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j connection unavailable",
        )

    query = "MATCH (g:Gene)-[r1:ASSOCIATED_WITH]->(d:Disease)<-[r2:TREATS]-(m:Medicine) RETURN g, r1, d, r2, m LIMIT 10"
    try:
        result: Any = await neo4j_session.run(query)
        records: list[dict[str, Any]] = await result.data()

        node_map: dict[str, GraphNode] = {}
        relationship_map: dict[str, GraphRelationship] = {}
        for record in records:
            for key in ("g", "d", "m"):
                if key in record and record[key] is not None:
                    node = _serialize_node(record[key])
                    node_map[node.id] = node
            for key in ("r1", "r2"):
                if key in record and record[key] is not None:
                    relationship = _serialize_relationship(record[key])
                    relationship_map[relationship.id] = relationship

            # Supports mocked responses that already return serialized nodes/relationships.
            if "nodes" in record:
                for raw_node in record["nodes"]:
                    node = _serialize_node(raw_node)
                    node_map[node.id] = node
            if "relationships" in record:
                for raw_relationship in record["relationships"]:
                    relationship = _serialize_relationship(raw_relationship)
                    relationship_map[relationship.id] = relationship

        return GraphResponse(nodes=list(node_map.values()), relationships=list(relationship_map.values()))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve discovery graph from staging proxy",
        ) from exc
