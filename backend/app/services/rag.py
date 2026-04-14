import os
import logging
from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .live_sources import live_sources

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Pydantic models for structured output enforcement (Zero-Hallucination JSON)
class Citation(BaseModel):
    source_id: str = Field(description="The unique identifier or title of the source document used.")
    exact_quote: str = Field(description="The exact snippet of text from the source that supports this claim.")
    structural_context: str = Field(description="The chapter and section context of the quote (e.g. Chapter 4, Section 2).")

class SynthesizedResponse(BaseModel):
    clinical_answer: str = Field(description="The evidence-based answer to the clinical query. Must strictly reflect the provided context.")
    citations: List[Citation] = Field(description="List of explicit citations grounding every sentence in the clinical_answer.")
    confidence_score: float = Field(description="Internal model confidence (0.0 to 1.0) that the provided context fully answers the query.")

class HybridRAGEngine:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.0
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        # Always read from env — no hardcoded fallback allowed
        self.index_name = os.getenv("PINECONE_INDEX")
        if not self.index_name:
            raise RuntimeError("[FATAL] PINECONE_INDEX env var not set. Check backend/.env")
        self.CONFIDENCE_THRESHOLD = 0.85

    def retrieve_offline_context(self, query: str, top_k: int = 5) -> List[Document]:
        """Retrieves structured chunks from the Gold Standard vector DB."""
        try:
            vectorstore = PineconeVectorStore(index_name=self.index_name, embedding=self.embeddings)
            docs = vectorstore.similarity_search(query, k=top_k)
            return docs
        except Exception as e:
            print(f"Retrieval Error: {e}")
            return []

    def fetch_live_context(self, query: str) -> List[Document]:
        """Calls the LiveSourcesManager to fetch PubMed + OpenAlex + Unpaywall results."""
        try:
            return live_sources.fetch(query)
        except Exception as e:
            logger.error(f"Live sources fetch failed: {e}")
            return []

    def synthesize(self, query: str) -> Dict[str, Any]:
        """
        The Zero-Hallucination Synthesis Pipeline.
        Retrieves, formats structural metadata, and forces strict JSON citation mapping.
        """
        # 1. Retrieve Hybrid Context (Offline + Live in parallel)
        offline_docs = self.retrieve_offline_context(query)
        live_docs = self.fetch_live_context(query)
        logger.info(f"RAG retrieved: {len(offline_docs)} offline + {len(live_docs)} live docs")
        
        all_docs = offline_docs + live_docs
        
        if not all_docs:
            return self._fallback_response("No relevant medical context found in our trusted databases.")

        # 2. Format context with structural markers for the Prompt
        context_block = ""
        for i, doc in enumerate(all_docs):
            meta = doc.metadata
            book = meta.get("book_name", "Unknown Source")
            chapter = meta.get("chapter", "")
            section = meta.get("section", "")
            structure = f"[{book} - {chapter} - {section}]"
            context_block += f"\nSOURCE_ID: {i}\nCONTEXT_STRUCTURE: {structure}\nEXACT_TEXT: {doc.page_content}\n---\n"

        # 3. Prompt Engineering for strict JSON structural citations
        prompt = f"""
        You are an expert clinical decision support AI answering a query from a physician.
        Your ONLY source of truth is the CONTEXT provided below. 
        
        CRITICAL RULES (ZERO HALLUCINATION POLICY):
        1. If the context does not explicitly contain the answer, you must output a confidence_score below {self.CONFIDENCE_THRESHOLD}.
        2. Every single claim in your 'clinical_answer' MUST be backed by a Citation pointing to the specific SOURCE_ID and exact_quote.
        3. Do not synthesize external knowledge.

        QUERY: {query}
        
        CONTEXT:
        {context_block}
        """

        # Enforce JSON output via Langchain's structural formatting
        structured_llm = self.llm.with_structured_output(SynthesizedResponse)
        
        try:
            response: SynthesizedResponse = structured_llm.invoke(prompt)
            
            # The Compliance & Trust Moat: Fallback Trigger
            if response.confidence_score < self.CONFIDENCE_THRESHOLD:
                return self._fallback_response()
                
            return response.dict()
            
        except Exception as e:
            print(f"Synthesis Error: {e}")
            return self._fallback_response("System error during synthesis.")

    def _fallback_response(self, reason="Insufficient confidence based on the retrieved 'Gold Standard' medical literature.") -> Dict[str, Any]:
        return {
            "clinical_answer": "I cannot provide a safe clinical answer for this query based on current data. " + reason,
            "citations": [],
            "confidence_score": 0.0
        }
