from pydantic import BaseModel
from typing import List, Optional

class SourceCitation(BaseModel):
    title: str
    url: Optional[str] = None
    type: str # "pubmed" or "offline_book"
    snippet: str

class ChatRequest(BaseModel):
    session_id: str
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
