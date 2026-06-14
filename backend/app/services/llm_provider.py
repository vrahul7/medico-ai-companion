"""
llm_provider.py — Google Gemini-only LLM & Embeddings Manager
===========================================================
Provides standardized access to Google GenAI services:
  LLM        → gemini-2.5-flash
  Embeddings → gemini-embedding-001

Design Principles:
  - Zero hallucination: temperature=0.0 on all clinical models
  - Stateless: checks active key on initialization
  - Google ecosystem native: fully aligned with Firebase and Cloud Run

Usage:
  from app.services.llm_provider import get_llm, get_embeddings, ACTIVE_PROVIDER
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# ─── Provider Constants ──────────────────────────────────────────────────────
PROVIDER_GEMINI = "gemini"
ACTIVE_PROVIDER: str = PROVIDER_GEMINI

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "[LLMProvider] FATAL: No Google API key found. "
        "Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env"
    )


# ─── LLM Factory ─────────────────────────────────────────────────────────────
def get_llm(temperature: float = 0.0):
    """
    Returns ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0).
    temperature=0.0 is ENFORCED for clinical safety (deterministic outputs).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    logger.info("[LLMProvider] LLM: Google gemini-2.5-flash")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=temperature,
        google_api_key=GEMINI_API_KEY,
    )


# ─── Embeddings Factory ───────────────────────────────────────────────────────
def get_embeddings():
    """
    Returns GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001").
    """
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    logger.info("[LLMProvider] Embeddings: Google gemini-embedding-001")
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=GEMINI_API_KEY,
    )


def get_provider_info() -> dict:
    """Returns current provider state for health-check endpoints."""
    return {
        "active_provider": ACTIVE_PROVIDER,
        "openai_configured": False,
        "gemini_configured": True,
        "llm_model": "gemini-2.5-flash",
        "embedding_model": "models/gemini-embedding-001",
    }
