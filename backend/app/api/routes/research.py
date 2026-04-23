"""
research.py — Live Medical Research & Guidelines Feeds
======================================================
Provides structural feeds:
  1. GET /api/research/scholarly : PubMed articles + AI Summaries
  2. GET /api/research/guidelines: Curated RSS Feeds (WHO, CDC, etc)

Summary provider: OpenAI gpt-4o-mini (primary) → Gemini (fallback)
"""

import os
import time
import logging
import re
from typing import List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import hashlib
from Bio import Entrez
import google.generativeai as genai
from app.services.llm_provider import get_openai_client, ACTIVE_PROVIDER, PROVIDER_OPENAI, GEMINI_API_KEY
from app.services.supabase_client import get_cached_summary, cache_summary

from app.services.rss_fetcher import fetch_rss_guidelines, RSSItem

load_dotenv(override=True)
logger = logging.getLogger(__name__)

router = APIRouter()

# ── Entrez Setup ──
Entrez.email   = os.getenv("ENTREZ_EMAIL", "medico@example.com")
Entrez.api_key = os.getenv("NCBI_API_KEY")

# ── Gemini Setup (fallback) ──
genai.configure(api_key=GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", ""))
_gemini = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={"temperature": 0.2, "max_output_tokens": 200}
)
# ── OpenAI client (primary) ──
_openai_client = get_openai_client()

class ResearchArticle(BaseModel):
    pmid: str
    title: str
    journal: str
    year: str
    authors: str
    summary: str
    abstract: str
    pubmed_url: str
    pdf_url: str | None = None

class ScholarlyFeedResponse(BaseModel):
    articles: List[ResearchArticle]
    page: int
    total_found: int
    has_more: bool

class GuidelinesFeedResponse(BaseModel):
    guidelines: List[RSSItem]

TOPIC_QUERIES = {
    "general":     "medicine[MeSH Major Topic] AND clinical trial[pt]",
    "pediatrics":  "pediatrics[MeSH Major Topic] AND clinical trial[pt]",
    "cardiology":  "cardiology[MeSH Major Topic] AND clinical trial[pt]",
    "neurology":   "neurology[MeSH Major Topic] AND clinical trial[pt]",
}

PAGE_SIZE = 5

@router.get("/research/scholarly", response_model=ScholarlyFeedResponse)
async def get_scholarly_feed(
    page: int = Query(default=1, ge=1),
    topic: str = Query(default="general"),
):
    query = TOPIC_QUERIES.get(topic, TOPIC_QUERIES["general"])
    retstart = (page - 1) * PAGE_SIZE

    try:
        search_handle = Entrez.esearch(
            db="pubmed", term=query, retmax=PAGE_SIZE, retstart=retstart, 
            sort="pub+date", usehistory="y"
        )
        search_results = Entrez.read(search_handle)
        search_handle.close()
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=502, detail="PubMed unavailable")

    ids = search_results.get("IdList", [])
    total_found = int(search_results.get("Count", 0))

    if not ids:
        return ScholarlyFeedResponse(articles=[], page=page, total_found=0, has_more=False)

    # Fetch batch
    fetch_handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="xml")
    records = Entrez.read(fetch_handle)
    fetch_handle.close()

    articles = []
    for art_rec in records.get("PubmedArticle", []):
        try:
            medline = art_rec["MedlineCitation"]
            art = medline["Article"]
            pmid = str(medline["PMID"])
            title = str(art.get("ArticleTitle", "Untitled")).strip()
            
            abs_parts = art.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(str(p) for p in abs_parts).strip() if isinstance(abs_parts, list) else str(abs_parts).strip()
            if len(abstract) < 60: continue

            journal = str(art.get("Journal", {}).get("Title", "Unknown"))
            pub_date = art.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = str(pub_date.get("Year", pub_date.get("MedlineDate", "2024")))
            
            summary = _generate_summary(title, abstract)

            articles.append(ResearchArticle(
                pmid=pmid, title=title, journal=journal, year=year,
                authors="Et al.", summary=summary, abstract=abstract,
                pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            ))
        except Exception as e:
            continue

    # Fetch and merge OpenAlex
    from app.services.live_sources import live_sources
    try:
        # We fetch OpenAlex and just grab the top 2 highly cited OA articles for the UI feed
        oa_docs = live_sources.openalex.search(query)[:2]
        for doc in oa_docs:
            abstract = doc.page_content
            title = doc.metadata.get("title", "Untitled")
            summary = _generate_summary(title, abstract)
            doi_ending = doc.metadata.get("doi", "").split("/")[-1] or str(hash(title))[:8]
            
            articles.append(ResearchArticle(
                pmid=f"OA-{doi_ending}",
                title=title,
                journal=doc.metadata.get("book_name", "").replace("OpenAlex: ", ""),
                year=doc.metadata.get("section", "2024"),
                authors="OA Authors",
                summary=summary,
                abstract=abstract,
                pubmed_url=doc.metadata.get("url", ""),
                pdf_url=doc.metadata.get("full_text_url")
            ))
    except Exception as e:
        logger.warning(f"Failed to merge OpenAlex: {e}")

    has_more = (retstart + PAGE_SIZE) < total_found
    return ScholarlyFeedResponse(articles=articles, page=page, total_found=total_found, has_more=has_more)


@router.get("/research/guidelines", response_model=GuidelinesFeedResponse)
async def get_guidelines_feed(
    page: int = Query(default=1, ge=1)
):
    """Returns curated RSS guidelines"""
    try:
        items = fetch_rss_guidelines(page=page)
        # Inject an AI Summary for each guideline so it matches the scholarly UI format
        for item in items:
            if not item.summary or len(item.summary) < 20:
                item_data = f"Guideline Title: {item.title}"
            else:
                item_data = f"Title: {item.title}. Meta: {item.summary}"
            
            ai_summary = _generate_summary("Medical Guideline", item_data)
            item.summary = ai_summary # Override the raw source tag with AI summary
        
        return GuidelinesFeedResponse(guidelines=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _generate_summary(title: str, abstract: str) -> str:
    """Generates a 2-3 sentence clinical summary. Uses OpenAI gpt-4o-mini (cheap + fast) → Gemini fallback."""
    # Strip raw HTML tags sometimes present in PubMed abstracts
    clean_abstract = re.sub(r'<[^>]+>', '', abstract)

    # Check Supabase cache first (avoids duplicate LLM calls)
    content_hash = hashlib.sha256(f"{title}:{clean_abstract}".encode('utf-8')).hexdigest()
    cached = get_cached_summary(content_hash)
    if cached:
        return cached

    prompt = (
        f"Summarize this clinical paper/guideline for a busy physician in 2-3 clear sentences. "
        f"Be specific about key findings. No markdown bold tags.\n"
        f"Title: {title}\nAbstract: {clean_abstract[:1500]}"
    )

    # ── Try OpenAI gpt-4o-mini first (cost-efficient at ~$0.15/1M tokens) ──
    if ACTIVE_PROVIDER == PROVIDER_OPENAI and _openai_client:
        try:
            completion = _openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )
            final_summary = completion.choices[0].message.content.strip().replace("**", "")
            cache_summary(content_hash, final_summary)
            return final_summary
        except Exception as e:
            logger.warning(f"[Research] OpenAI summary failed, using Gemini: {e}")

    # ── Fallback: Gemini ──
    try:
        response = _gemini.generate_content(prompt)
        final_summary = response.text.strip().replace("**", "")
        cache_summary(content_hash, final_summary)
        return final_summary
    except Exception:
        return clean_abstract[:280] + "..."
