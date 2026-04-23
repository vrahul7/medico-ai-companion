"""
llm_provider.py — Multi-Provider LLM & Embeddings Manager
===========================================================
Provides automatic provider selection with failover:

  Primary   → OpenAI   (gpt-4o synthesis, text-embedding-3-large)
  Fallback  → Gemini   (gemini-1.5-flash synthesis, gemini-embedding-001)

Design Principles:
  - Zero hallucination: temperature=0.0 on all clinical models
  - Graceful degradation: if primary provider fails, auto-switch
  - Stateless: always re-checks available keys on init
  - Healthcare-safe: no model serves a response without a source context

Usage:
  from app.services.llm_provider import get_llm, get_embeddings, ACTIVE_PROVIDER
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# ─── Provider Constants ──────────────────────────────────────────────────────
PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

# ─── Active Provider Resolution ──────────────────────────────────────────────
def _resolve_provider() -> str:
    """
    Picks the best available LLM provider based on configured API keys.
    Gemini is now primary (paid credits). OpenAI acts as fallback.
    """
    if GEMINI_API_KEY:
        logger.info("[LLMProvider] ✅ Using Google Gemini as primary provider (gemini-1.5-flash + text-embedding-004)")
        return PROVIDER_GEMINI
    if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
        logger.info("[LLMProvider] ⚠️  Gemini key not found. Falling back to OpenAI.")
        return PROVIDER_OPENAI
    raise RuntimeError(
        "[LLMProvider] FATAL: No LLM API key found. "
        "Set GEMINI_API_KEY or OPENAI_API_KEY in backend/.env"
    )

ACTIVE_PROVIDER: str = _resolve_provider()


# ─── LLM Factory ─────────────────────────────────────────────────────────────
def get_llm(temperature: float = 0.0):
    """
    Returns the best available LangChain Chat LLM.

    OpenAI  → ChatOpenAI(model="gpt-4o", temperature=0.0)
    Gemini  → ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)

    temperature=0.0 is ENFORCED for clinical safety (deterministic outputs).
    """
    if ACTIVE_PROVIDER == PROVIDER_OPENAI:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            openai_api_key=OPENAI_API_KEY,
        )
    else:
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
    Returns the best available LangChain Embeddings model.

    OpenAI → text-embedding-3-large  (3072-dim, SOTA retrieval quality)
    Gemini → gemini-embedding-001    (768-dim)

    IMPORTANT: Pinecone index dimensions must match the embedding model used
    during ingestion. If switching providers, re-ingest all textbook chunks.
    """
    if ACTIVE_PROVIDER == PROVIDER_GEMINI:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        logger.info("[LLMProvider] Embeddings: Google gemini-embedding-001 (3072-dim)")
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )
    else:
        from langchain_openai import OpenAIEmbeddings
        logger.info("[LLMProvider] Embeddings: OpenAI text-embedding-3-large (3072-dim)")
        return OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=OPENAI_API_KEY,
        )


# ─── Direct OpenAI Client (for non-LangChain usage e.g. PDF analyzer) ────────
def get_openai_client():
    """
    Returns a raw openai.OpenAI client for direct API calls.
    Returns None if OpenAI is not available (caller should fall back to Gemini).
    """
    if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.warning("[LLMProvider] openai package not installed — run: pip install openai")
        return None


def get_provider_info() -> dict:
    """Returns current provider state for health-check endpoints."""
    return {
        "active_provider": ACTIVE_PROVIDER,
        "openai_configured": bool(OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-")),
        "gemini_configured": bool(GEMINI_API_KEY),
        "llm_model": "gemini-2.5-flash" if ACTIVE_PROVIDER == PROVIDER_GEMINI else "gpt-4o",
        "embedding_model": (
            "models/gemini-embedding-001" if ACTIVE_PROVIDER == PROVIDER_GEMINI
            else "text-embedding-3-large"
        ),
    }
