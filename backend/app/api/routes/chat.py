from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.rag import HybridRAGEngine

router = APIRouter()

# Requests ALIGNED WITH FRONTEND (AIChat.jsx)
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class SourceCitation(BaseModel):
    title: str
    snippet: str
    type: str = "textbook"

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    confidence_score: float

# Singleton engine
_engine = HybridRAGEngine()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Synthesized RAG response with textbook + PubMed citations.
    """
    try:
        result = _engine.synthesize(request.query)
        # Ensure mapping matches the AIChat.jsx expectation
        return ChatResponse(
            answer=result.get("answer", ""),
            sources=[
                SourceCitation(**c) for c in result.get("sources", [])
            ],
            confidence_score=result.get("confidence_score", 0.0),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
