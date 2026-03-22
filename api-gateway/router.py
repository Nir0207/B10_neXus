from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
import httpx
from neo4j import AsyncSession

from auth import decode_token_user, get_current_user
from database import get_postgres_connection, get_neo4j_session
from html_export import build_export_html
from schemas import (
    ExportChartRequest,
    ExportHtmlResponse,
    FrequencyTimelinePoint,
    GeneResponse,
    GeneDistributionPoint,
    GraphNode,
    GraphRelationship,
    GraphResponse,
    IntelligenceQueryRequest,
    IntelligenceQueryResponse,
    OrganAffinityPoint,
    RumMetricRequest,
    TherapeuticLandscapePoint,
    TrendAnalyticsResponse,
    TripletEdge,
    TripletNode,
    TripletResponse,
    User,
)
from settings import get_intelligence_api_url

try:
    import asyncpg
except ImportError:  # pragma: no cover - environment-dependent fallback
    asyncpg = None  # type: ignore[assignment]

router = APIRouter(prefix="/api/v1")
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
logger = logging.getLogger(__name__)


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


def _json_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return []


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


def _serialize_graph_records(records: list[dict[str, Any]]) -> GraphResponse:
    node_map: dict[str, GraphNode] = {}
    relationship_map: dict[str, GraphRelationship] = {}

    for record in records:
        for key in ("g", "d", "m"):
            if key in record and record[key] is not None:
                node = _serialize_node(record[key])
                node_map[node.id] = node
        for key in ("r1", "r2", "r3"):
            if key in record and record[key] is not None:
                relationship = _serialize_relationship(record[key])
                relationship_map[relationship.id] = relationship

        if "nodes" in record:
            for raw_node in record["nodes"]:
                node = _serialize_node(raw_node)
                node_map[node.id] = node
        if "relationships" in record:
            for raw_relationship in record["relationships"]:
                relationship = _serialize_relationship(raw_relationship)
                relationship_map[relationship.id] = relationship

    return GraphResponse(nodes=list(node_map.values()), relationships=list(relationship_map.values()))


def _to_triplet_response(graph: GraphResponse) -> TripletResponse:
    nodes = [
        TripletNode(
            id=node.id,
            label=str(
                node.properties.get("symbol")
                or node.properties.get("name")
                or node.properties.get("uniprot_id")
                or node.id
            ),
            type=node.labels[0] if node.labels else "Unknown",
            properties=node.properties,
        )
        for node in graph.nodes
    ]
    edges = [
        TripletEdge(
            source=edge.start_node,
            target=edge.end_node,
            relationship=edge.type,
            properties=edge.properties,
        )
        for edge in graph.relationships
    ]
    return TripletResponse(nodes=nodes, edges=edges)


async def _run_graph_query(
    neo4j_session: AsyncSession,
    *,
    organ: str | None,
    limit: int,
) -> GraphResponse:
    query = """
    MATCH (g:Gene)-[r1:ASSOCIATED_WITH]->(d:Disease)<-[r2:TREATS]-(m:Medicine)
    WHERE $organ = '' OR toLower(coalesce(d.organ, '')) = $organ
    OPTIONAL MATCH (m)-[r3:BINDS_TO]->(g)
    RETURN
        {id: elementId(g), labels: labels(g), properties: properties(g)} AS g,
        {
            id: elementId(r1),
            type: type(r1),
            start_node: elementId(startNode(r1)),
            end_node: elementId(endNode(r1)),
            properties: properties(r1)
        } AS r1,
        {id: elementId(d), labels: labels(d), properties: properties(d)} AS d,
        {
            id: elementId(r2),
            type: type(r2),
            start_node: elementId(startNode(r2)),
            end_node: elementId(endNode(r2)),
            properties: properties(r2)
        } AS r2,
        {id: elementId(m), labels: labels(m), properties: properties(m)} AS m,
        CASE
            WHEN r3 IS NULL THEN NULL
            ELSE {
                id: elementId(r3),
                type: type(r3),
                start_node: elementId(startNode(r3)),
                end_node: elementId(endNode(r3)),
                properties: properties(r3)
            }
        END AS r3
    LIMIT $limit
    """
    result: Any = await neo4j_session.run(query, organ=(organ or "").strip().lower(), limit=limit)
    records: list[dict[str, Any]] = await result.data()
    return _serialize_graph_records(records)


async def _query_intelligence_service(payload: IntelligenceQueryRequest) -> IntelligenceQueryResponse:
    intelligence_url = get_intelligence_api_url().rstrip("/")
    timeout = httpx.Timeout(45.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{intelligence_url}/api/v1/intelligence/query",
                json=payload.model_dump(exclude_none=True),
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Intelligence service returned {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence service unavailable",
        ) from exc

    return IntelligenceQueryResponse(**response.json())


def _canonical_disease_id(value: str) -> str:
    return _NON_ALNUM_PATTERN.sub("-", value.strip().lower()).strip("-")


def _sanitize_rum_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
    sanitized: dict[str, str | int | float | bool | None] = {}
    for key, value in metadata.items():
        safe_key = _NON_ALNUM_PATTERN.sub("_", key.strip().lower()).strip("_")
        if not safe_key:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[safe_key[:48]] = value
        else:
            sanitized[safe_key[:48]] = json.dumps(value, sort_keys=True, default=str)[:512]
        if len(sanitized) >= 16:
            break
    return sanitized


def _authenticated_user_from_request(request: Request) -> User | None:
    authorization = request.headers.get("Authorization")
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    return decode_token_user(authorization.removeprefix("Bearer ").strip())


@router.post("/ops/rum", status_code=status.HTTP_202_ACCEPTED)
async def record_rum_metric(
    payload: RumMetricRequest,
    request: Request,
) -> dict[str, str]:
    current_user = _authenticated_user_from_request(request)
    logger.info(
        "RUM metric received name=%s route=%s value_ms=%s rating=%s nav=%s",
        payload.metric_name,
        payload.route,
        payload.value_ms,
        payload.rating,
        payload.navigation_type,
        extra={
            "rum_metric_name": payload.metric_name,
            "rum_route": payload.route,
            "rum_session_id": payload.session_id,
            "rum_value_ms": payload.value_ms,
            "rum_rating": payload.rating,
            "rum_navigation_type": payload.navigation_type,
            "rum_browser_name": payload.browser_name,
            "rum_os_name": payload.os_name,
            "rum_device_type": payload.device_type,
            "rum_language": payload.language,
            "rum_timezone": payload.timezone,
            "rum_screen_width": payload.screen_width,
            "rum_screen_height": payload.screen_height,
            "rum_user": current_user.username if current_user is not None else "anonymous",
            "rum_is_admin": current_user.is_admin if current_user is not None else False,
            "rum_client_ip": request.client.host if request.client is not None else "unknown",
            **_sanitize_rum_metadata(payload.metadata),
        },
    )
    return {"status": "accepted"}


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
            """
            SELECT
                g.uniprot_id,
                g.hgnc_symbol AS gene_symbol,
                COALESCE(p.protein_name, g.hgnc_symbol) AS name,
                NULL::TEXT AS description,
                g.data_source
            FROM silver.genes AS g
            LEFT JOIN silver.proteins AS p
                ON p.uniprot_accession = g.uniprot_id
            WHERE g.uniprot_id = $1
            """,
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
    organ: str | None = Query(default=None, pattern=r"^[A-Za-z-]{1,32}$"),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    neo4j_session: AsyncSession | None = Depends(get_neo4j_session),
) -> GraphResponse:
    del current_user
    if neo4j_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j connection unavailable",
        )

    try:
        return await _run_graph_query(neo4j_session, organ=organ, limit=limit)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve discovery graph from staging proxy",
        ) from exc


@router.get("/discovery/triplets", response_model=TripletResponse)
async def get_discovery_triplets(
    organ: str | None = Query(default=None, pattern=r"^[A-Za-z-]{1,32}$"),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    neo4j_session: AsyncSession | None = Depends(get_neo4j_session),
) -> TripletResponse:
    del current_user
    if neo4j_session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j connection unavailable",
        )

    try:
        graph = await _run_graph_query(neo4j_session, organ=organ, limit=limit)
        return _to_triplet_response(graph)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve discovery triplets from staging proxy",
        ) from exc


@router.post("/intelligence/query", response_model=IntelligenceQueryResponse)
async def query_intelligence(
    payload: IntelligenceQueryRequest,
    current_user: User = Depends(get_current_user),
) -> IntelligenceQueryResponse:
    del current_user
    return await _query_intelligence_service(payload)


@router.get("/analytics/trends/{disease_id}", response_model=TrendAnalyticsResponse)
async def get_disease_trends(
    disease_id: str = Path(..., min_length=1, max_length=128),
    current_user: User = Depends(get_current_user),
    pg_conn: Any | None = Depends(get_postgres_connection),
) -> TrendAnalyticsResponse:
    del current_user
    if pg_conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Postgres connection unavailable",
        )

    normalized = _canonical_disease_id(disease_id)
    lowered = disease_id.strip().lower()

    try:
        row: Any | None = await pg_conn.fetchrow(
            """
            SELECT
                disease_id,
                disease_name,
                clinical_summary,
                frequency_timeline,
                gene_distribution,
                organ_affinity,
                therapeutic_landscape,
                updated_at
            FROM disease_intelligence
            WHERE LOWER(disease_id) = $1
               OR LOWER(disease_name) = $2
               OR REPLACE(LOWER(disease_name), ' ', '-') = $1
            LIMIT 1
            """,
            normalized,
            lowered,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve disease trends from staging proxy",
        ) from exc

    if row is None:
        raise HTTPException(status_code=404, detail="Disease trend not found")

    payload = dict(row)
    payload["frequency_timeline"] = [FrequencyTimelinePoint(**item) for item in _json_list(payload.get("frequency_timeline"))]
    payload["gene_distribution"] = [GeneDistributionPoint(**item) for item in _json_list(payload.get("gene_distribution"))]
    payload["organ_affinity"] = [OrganAffinityPoint(**item) for item in _json_list(payload.get("organ_affinity"))]
    payload["therapeutic_landscape"] = [
        TherapeuticLandscapePoint(**item)
        for item in _json_list(payload.get("therapeutic_landscape"))
    ]
    return TrendAnalyticsResponse(**payload)


@router.post("/analytics/export", response_model=ExportHtmlResponse)
async def export_analytics_chart(
    payload: ExportChartRequest,
    current_user: User = Depends(get_current_user),
) -> ExportHtmlResponse:
    del current_user
    html = build_export_html(payload)
    slug = _canonical_disease_id(payload.disease_name or payload.disease_id or payload.title or "report")
    return ExportHtmlResponse(
        filename=f"bionexus-{slug or 'report'}.html",
        html=html,
    )
