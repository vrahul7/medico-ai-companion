"""
pdf_analyzer.py — Clinical PDF Analysis Route
===============================================
Downloads a medical PDF (guideline, paper, protocol), extracts text,
and synthesizes a structured clinical breakdown using the best available LLM.

Provider priority (from llm_provider.py):
  1. OpenAI gpt-4o   → superior instruction-following for structured Markdown
  2. Google Gemini   → fallback if OpenAI unavailable

Limits: First 8 pages, max 15MB download, 15,000 chars of text sent to LLM.
"""

import os
import io
import logging
import requests
import google.generativeai as genai

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pypdf import PdfReader
from dotenv import load_dotenv

from app.services.llm_provider import (
    GEMINI_API_KEY,
)

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

# Configure Gemini as fallback (always available)
genai.configure(api_key=GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", ""))
_gemini = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"temperature": 0.2, "max_output_tokens": 1024}
)

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class PdfAnalysisRequest(BaseModel):
    url: str
    source_type: str = "guideline"

class PdfAnalysisResponse(BaseModel):
    analysis_markdown: str
    pdf_url: str
    provider_used: str = "unknown"


# ─── Clinical Analysis Prompt ─────────────────────────────────────────────────
def _build_prompt(full_text: str, source_type: str) -> str:
    return f"""You are an expert clinical AI assistant. Analyze the following text extracted from a medical document ({source_type}).
Provide a highly structured, professional clinical breakdown formatted in Markdown to save the physician time.

Format strictly as:

### 📌 Document Purpose
What is the core intent of this document?

### ⚡ Key Findings / Core Rules
- Extract the 3-5 most important medical recommendations, thresholds, or findings. Be specific with numbers and dosages.

### 🏥 Clinical Relevance
Why and when should a physician apply this in practice? Any contraindications or patient population caveats?

### ⚠️ Important Caveats
Any limitations, evidence quality concerns, or situations where this guidance may not apply?

Document Text:
{full_text[:15000]}
"""


# ─── Route ────────────────────────────────────────────────────────────────────
@router.post("/research/analyze_pdf", response_model=PdfAnalysisResponse)
async def analyze_pdf(req: PdfAnalysisRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing PDF URL")

    # ── 1. Download PDF ───────────────────────────────────────────────────────
    try:
        resp = requests.get(req.url, timeout=15, verify=False, stream=True)
        resp.raise_for_status()

        pdf_bytes = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=8192):
            downloaded += len(chunk)
            if downloaded > 15 * 1024 * 1024:  # 15MB cap
                break
            pdf_bytes.write(chunk)
        pdf_bytes.seek(0)
    except Exception as e:
        logger.error(f"[PDFAnalyzer] Download failed for {req.url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch PDF: {str(e)}")

    # ── 2. Extract Text ───────────────────────────────────────────────────────
    try:
        reader = PdfReader(pdf_bytes)
        text_content = []
        for i, page in enumerate(reader.pages):
            if i >= 8:
                break
            text_content.append(page.extract_text() or "")

        full_text = "\n".join(text_content)
        if len(full_text.strip()) < 50:
            raise ValueError("No extractable text found in PDF.")
    except Exception as e:
        logger.error(f"[PDFAnalyzer] PDF read error: {e}")
        raise HTTPException(
            status_code=422,
            detail="Unable to extract text from the provided PDF. It may be scanned or secured."
        )

    prompt = _build_prompt(full_text, req.source_type)

    # ── 3. Run Gemini Analysis ────────────────────────────────────────────────
    try:
        response = _gemini.generate_content(prompt)
        analysis_markdown = response.text.strip()
        logger.info("[PDFAnalyzer] Analysis complete via Gemini gemini-1.5-flash")
        return PdfAnalysisResponse(
            analysis_markdown=analysis_markdown,
            pdf_url=req.url,
            provider_used="google/gemini-1.5-flash"
        )
    except Exception as e:
        logger.error(f"[PDFAnalyzer] Gemini AI analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="AI analysis engine is currently unavailable. Please try again later."
        )


# ─── PDF Proxy ────────────────────────────────────────────────────────────────
@router.get("/proxy_pdf")
async def proxy_pdf(url: str = Query(...)):
    """Proxies a PDF through the backend to bypass X-Frame-Options in the frontend iframe."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = requests.get(url, headers=headers, stream=True, timeout=15, verify=False)
        if req.status_code != 200:
            raise HTTPException(status_code=req.status_code, detail="Failed to fetch PDF")
        return StreamingResponse(
            req.iter_content(chunk_size=1024 * 1024),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
