from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    is_admin: bool = False
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


class UserRegistrationRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(..., min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class GeneResponse(BaseModel):
    uniprot_id: str = Field(..., description="Primary Key: UniProt ID for cross-database mapping")
    gene_symbol: str
    name: str
    description: str | None = None
    data_source: str = Field(..., description="Source of the data, e.g., NCBI, Open Targets, UniProt")


class GraphNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict[str, Any]


class GraphRelationship(BaseModel):
    id: str
    type: str
    start_node: str
    end_node: str
    properties: dict[str, Any]


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    relationships: list[GraphRelationship]


class TripletNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class TripletEdge(BaseModel):
    source: str
    target: str
    relationship: str
    properties: dict[str, Any] = Field(default_factory=dict)


class TripletResponse(BaseModel):
    nodes: list[TripletNode]
    edges: list[TripletEdge]


class IntelligenceQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    organ: str | None = Field(default=None, max_length=32)
    gene: str | None = Field(default=None, max_length=64)
    uniprot_id: str | None = Field(default=None, max_length=15)
    disease: str | None = Field(default=None, max_length=128)
    medicine: str | None = Field(default=None, max_length=128)
    study_id: str | None = Field(default=None, max_length=32)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class IntelligenceQueryResponse(BaseModel):
    reply: str
    mode: str
    resolved_entity: str | None = None
    sources: list[str] = Field(default_factory=list)
    visual_payload: VisualPayload | None = None


class VisualPayload(BaseModel):
    chart_type: Literal["line", "bar", "radar"]
    title: str
    disease_id: str
    disease_name: str
    x_key: str
    y_key: str
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    clinical_summary: str


class FrequencyTimelinePoint(BaseModel):
    year: int
    study_count: int


class GeneDistributionPoint(BaseModel):
    uniprot_id: str = Field(..., description="Primary Key: UniProt ID for cross-database mapping")
    gene_symbol: str
    association_score: float
    association_source: str | None = None


class OrganAffinityPoint(BaseModel):
    organ: str
    value: int


class TherapeuticLandscapePoint(BaseModel):
    chembl_id: str
    molecule_name: str
    uniprot_id: str = Field(..., description="Primary Key: UniProt ID for cross-database mapping")
    gene_symbol: str
    bioactivity_status: str
    evidence_source: str | None = None
    affinity: float | None = None


class TrendAnalyticsResponse(BaseModel):
    disease_id: str
    disease_name: str
    clinical_summary: str
    frequency_timeline: list[FrequencyTimelinePoint] = Field(default_factory=list)
    gene_distribution: list[GeneDistributionPoint] = Field(default_factory=list)
    organ_affinity: list[OrganAffinityPoint] = Field(default_factory=list)
    therapeutic_landscape: list[TherapeuticLandscapePoint] = Field(default_factory=list)
    updated_at: datetime | None = None


class ExportChartRequest(BaseModel):
    chart_type: Literal["line", "bar", "radar"]
    title: str = Field(..., min_length=1, max_length=200)
    datasets: list[dict[str, Any]] = Field(default_factory=list)
    clinical_summary: str = Field(default="", max_length=4000)
    disease_id: str | None = Field(default=None, max_length=128)
    disease_name: str | None = Field(default=None, max_length=256)
    x_key: str = Field(..., min_length=1, max_length=64)
    y_key: str = Field(..., min_length=1, max_length=64)
    report_id: str | None = Field(default=None, max_length=64)
    model_name: str = Field(default="BioMistral-7B-Instruct", max_length=128)


class ExportHtmlResponse(BaseModel):
    filename: str
    html: str


class RumMetricRequest(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9_.-]+$")
    route: str = Field(..., min_length=1, max_length=256)
    session_id: str = Field(..., min_length=1, max_length=128)
    value_ms: float | None = Field(default=None, ge=0, le=300000)
    rating: Literal["good", "needs-improvement", "poor", "info"] | None = None
    navigation_type: str | None = Field(default=None, max_length=64)
    browser_name: str | None = Field(default=None, max_length=64)
    os_name: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=32)
    language: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)
    screen_width: int | None = Field(default=None, ge=0, le=20000)
    screen_height: int | None = Field(default=None, ge=0, le=20000)
    metadata: dict[str, Any] = Field(default_factory=dict)
