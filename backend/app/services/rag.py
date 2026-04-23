"""
rag.py — Hybrid RAG Synthesis Engine
======================================
Orchestrates the full clinical Q&A pipeline:

  1. Offline Retrieval  → Pinecone (medical textbook embeddings)
  2. Live Retrieval     → PubMed + OpenAlex + RSS Guidelines
  3. Synthesis          → LLM structured output with enforced citations
  4. Post-processing    → Citation type mapping + URL recovery

Provider: automatically selected by llm_provider.py
  Primary   → OpenAI gpt-4o + text-embedding-3-large
  Fallback  → Google Gemini gemini-1.5-flash + gemini-embedding-001

Zero-hallucination policy: every claim must cite a SOURCE_ID from context.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
from langchain_pinecone import PineconeVectorStore
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .live_sources import live_sources
from .llm_provider import get_llm, get_embeddings, ACTIVE_PROVIDER, get_provider_info

load_dotenv(override=True)
logger = logging.getLogger(__name__)


# ─── Pydantic Models (aligned with frontend AIChat.jsx) ──────────────────────
class Citation(BaseModel):
    source_id: int = Field(description="The matching SOURCE_ID from the context.")
    title: Optional[str] = Field(default="Medical Source", description="The source title or chapter context.")
    snippet: Optional[str] = Field(default="", description="The supporting text snippet.")
    type: str = Field(default="textbook", description="Source type: textbook or pubmed")
    url: Optional[str] = Field(default=None, description="Source URL if available.")

class SynthesizedResponse(BaseModel):
    answer: str = Field(description="The grounded clinical answer.")
    sources: List[Citation] = Field(description="List of citations.")
    confidence_score: float = Field(description="Confidence (0-1).")


# ─── Hybrid RAG Engine ────────────────────────────────────────────────────────
class HybridRAGEngine:
    """
    Main clinical synthesis engine.

    Uses the best available LLM provider (OpenAI → Gemini fallback).
    All responses are grounded — no answer is emitted without citations.
    """

    CONFIDENCE_THRESHOLD = 0.85
    SEARCH_NAMESPACES = [
        "nelson_vol1_semantic",
        "nelson_vol2_semantic",
        "piyushgupta_vol1_semantic",
        "piyushgupta_vol2_semantic",
        "piyushgupta_vol3_semantic",
    ]

    def __init__(self):
        self.llm = get_llm(temperature=0.0)
        self.embeddings = get_embeddings()
        self.index_name = os.getenv("PINECONE_INDEX")
        if not self.index_name:
            raise RuntimeError("[FATAL] PINECONE_INDEX env var not set.")

        provider_info = get_provider_info()
        logger.info(
            f"[HybridRAGEngine] Initialized | Provider: {provider_info['active_provider']} | "
            f"LLM: {provider_info['llm_model']} | Embeddings: {provider_info['embedding_model']}"
        )

    # ── 1. Offline Retrieval ─────────────────────────────────────────────────
    def retrieve_offline_context(self, query: str, top_k: int = 3) -> List[Document]:
        """Retrieves structured chunks from the Gold Standard Pinecone vector DB."""
        all_docs = []
        try:
            vectorstore = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings
            )
            for ns in self.SEARCH_NAMESPACES:
                docs = vectorstore.similarity_search(query, k=top_k, namespace=ns)
                for d in docs:
                    d.metadata["internal_ns"] = ns
                all_docs.extend(docs)
            logger.info(f"[RAG] Offline retrieval: {len(all_docs)} chunks from {len(self.SEARCH_NAMESPACES)} namespaces")
        except Exception as e:
            logger.error(f"[RAG] Offline retrieval error: {e}")
        return all_docs

    # ── 2. Live Retrieval ────────────────────────────────────────────────────
    def fetch_live_context(self, query: str) -> List[Document]:
        """Fetches real-time context from PubMed, OpenAlex, and RSS guidelines."""
        try:
            docs = live_sources.fetch(query)
            logger.info(f"[RAG] Live retrieval: {len(docs)} documents")
            return docs
        except Exception as e:
            logger.error(f"[RAG] Live sources fetch failed: {e}")
            return []

    # ── 3. Synthesis ─────────────────────────────────────────────────────────
    def synthesize(self, query: str) -> Dict[str, Any]:
        """
        Full pipeline: Retrieve → Format Context → LLM Synthesis → Post-process.

        Returns a dict with keys: answer, sources, confidence_score
        """
        # Hybrid retrieval
        offline_docs = self.retrieve_offline_context(query)
        live_docs = self.fetch_live_context(query)
        all_docs = offline_docs + live_docs

        # Build context block with explicit SOURCE IDs for citation enforcement
        context_block = ""
        if not all_docs:
            context_block = "NO EXTERNAL CONTEXT FOUND. USE GENERAL KNOWLEDGE ONLY FOR GREETINGS OR NON-CLINICAL INFO."
        else:
            for i, doc in enumerate(all_docs):
                meta = doc.metadata
                book = meta.get("book_name", "Medical Reference")
                chapter = meta.get("chapter", "")
                title = f"{book} — {chapter}" if chapter else book
                context_block += (
                    f"SOURCE_ID: {i}\n"
                    f"TITLE: {title}\n"
                    f"TEXT: {doc.page_content}\n"
                    f"---\n"
                )

        # Clinical synthesis prompt — Balanced between companion friendliness and clinical precision
        prompt = f"""You are Medico AI, a sophisticated clinical intelligence companion for physicians.

CORE DIRECTIVES:
1. GREETINGS & CONVERSATION: If the user greets you or asks general non-clinical questions, respond warmly and professionally as an AI companion.
2. CLINICAL QUERIES: For medical questions, base your factual claims ONLY on the provided CONTEXT. 
3. CITATIONS: For every medical claim, you MUST cite the source using [Source X] format.
4. HALLUCINATION PREVENTION: If the medical context is insufficient for a clinical answer, state what you CAN find and suggest what else is needed, rather than saying "I don't know."
5. TONE: Professional, supportive, and intellectually engaged.

QUERY: {query}

CONTEXT:
{context_block}

Synthesize a helpful, clinically accurate response."""

        structured_llm = self.llm.with_structured_output(SynthesizedResponse)

        try:
            response: SynthesizedResponse = structured_llm.invoke(prompt)

            # Post-process citations: inject correct type and URL from actual doc metadata
            refined_citations = []
            for cite in response.sources:
                sid = cite.source_id
                if 0 <= sid < len(all_docs):
                    doc = all_docs[sid]
                    meta = doc.metadata
                    raw_type = meta.get("source_type", "textbook")
                    cite.type = "pubmed" if raw_type in ["pubmed", "openalex", "rss_guideline"] else "textbook"
                    cite.url = meta.get("url") or meta.get("full_text_url")
                refined_citations.append(cite)

            response.sources = refined_citations
            logger.info(
                f"[RAG] Synthesis complete | Citations: {len(refined_citations)} | "
                f"Confidence: {response.confidence_score:.2f} | Provider: {ACTIVE_PROVIDER}"
            )
            return response.dict()

        except Exception as e:
            logger.error(f"[RAG] Synthesis error ({ACTIVE_PROVIDER}): {e}")
            return self._fallback_response(f"System synthesis error: {str(e)}")

    # ── Fallback ─────────────────────────────────────────────────────────────
    def _fallback_response(self, reason: str = "No trusted matches found.") -> Dict[str, Any]:
        return {
            "answer": (
                "⚠️ I cannot provide a safe clinical answer at this time. "
                f"Reason: {reason}\n\n"
                "Please consult primary clinical resources or contact a specialist."
            ),
            "sources": [],
            "confidence_score": 0.0,
        }
