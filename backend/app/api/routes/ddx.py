from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class DDxRequest(BaseModel):
    age: int
    sex: str
    primary_symptom: str
    comorbidities: List[str]
    vitals: str

class Citation(BaseModel):
    source_id: str
    exact_quote: str
    structural_context: str

class DDxCondition(BaseModel):
    condition: str
    probability: str
    why: str
    citations: List[Citation]

class DDxResponse(BaseModel):
    results: List[DDxCondition]
    confidence_score: float

@router.post("/generate", response_model=DDxResponse)
async def generate_ddx(request: DDxRequest):
    # Mocking the Synthesis Engine response for now to unblock Frontend UI layout
    # In production, this would call the HybridRAGEngine in rag.py.
    if request.age < 0 or request.age > 120:
        raise HTTPException(status_code=400, detail="Invalid age")

    return DDxResponse(
        results=[
            DDxCondition(
                condition="Acute Asthma Exacerbation",
                probability="High (85%)",
                why="Classic presentation of wheezing in a young patient with a history of atopy.",
                citations=[
                    Citation(
                        source_id="Nelson's Pediatrics, 21st Ed.",
                        exact_quote="Wheezing and dyspnea are the hallmark signs of asthma exacerbation in pediatric patients...",
                        structural_context="Chapter 142, Section 3"
                    )
                ]
            ),
            DDxCondition(
                condition="Viral Bronchiolitis",
                probability="Medium (40%)",
                why="Common in early childhood, presents with similar wheezing but usually preceded by URI symptoms.",
                citations=[
                    Citation(
                        source_id="Nelson's Pediatrics, 21st Ed.",
                        exact_quote="Bronchiolitis typically affects infants and presents with a prodrome of rhinorrhea followed by wheezing.",
                        structural_context="Chapter 144, Section 1"
                    )
                ]
            )
        ],
        confidence_score=0.92
    )
