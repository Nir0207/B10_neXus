from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


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


class IntelligenceQueryResponse(BaseModel):
    reply: str
    mode: str
    resolved_entity: str | None = None
    sources: list[str] = Field(default_factory=list)
