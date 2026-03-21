from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class GeneResponse(BaseModel):
    uniprot_id: str = Field(..., description="Primary Key: UniProt ID for cross-database mapping")
    gene_symbol: str
    name: str
    description: Optional[str] = None
    data_source: str = Field(..., description="Source of the data, e.g., NCBI, Open Targets, UniProt")

class GraphNode(BaseModel):
    id: str
    labels: List[str]
    properties: Dict[str, Any]

class GraphRelationship(BaseModel):
    id: str
    type: str
    start_node: str
    end_node: str
    properties: Dict[str, Any]

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
