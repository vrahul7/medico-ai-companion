from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.rag import HybridRAGEngine

router = APIRouter()

# ── Request / Response schemas (inline to avoid circular imports) ──
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class SourceCitation(BaseModel):
    source_id: str
    exact_quote: str
    structural_context: str

class ChatResponse(BaseModel):
    clinical_answer: str
    citations: List[SourceCitation]
    confidence_score: float

# Singleton engine — initialised once on import
_engine = HybridRAGEngine()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Receives a clinical query and returns a zero-hallucination
    synthesized RAG response with inline textbook + PubMed citations.
    """
    try:
        result = _engine.synthesize(request.query)
        return ChatResponse(
            clinical_answer=result.get("clinical_answer", ""),
            citations=[
                SourceCitation(**c) for c in result.get("citations", [])
            ],
            confidence_score=result.get("confidence_score", 0.0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
