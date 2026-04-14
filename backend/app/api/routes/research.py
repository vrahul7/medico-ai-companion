"""
research.py — Live Medical Research Feed
=========================================
GET /api/research/feed?page=1&topic=general

Fetches the 5 most recent high-impact PubMed articles per page,
then uses Gemini to generate a 3-sentence clinical summary of each
abstract so physicians can quickly scan new evidence without reading
the full paper.

Pages are 1-indexed. Each call returns 5 articles.
"""

import os
import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from Bio import Entrez
import google.generativeai as genai

load_dotenv(override=True)
logger = logging.getLogger(__name__)

router = APIRouter()

# ── Entrez Setup ──────────────────────────────────────────────────────────
Entrez.email   = os.getenv("ENTREZ_EMAIL", "medico@example.com")
Entrez.api_key = os.getenv("NCBI_API_KEY")

# ── Gemini Setup ──────────────────────────────────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_gemini = genai.GenerativeModel(
    model_name="gemini-1.5-flash",   # Flash for speed on summaries
    generation_config={"temperature": 0.2, "max_output_tokens": 200}
)

# ── Data Models ───────────────────────────────────────────────────────────
class ResearchArticle(BaseModel):
    pmid: str
    title: str
    journal: str
    year: str
    authors: str
    summary: str          # Gemini-generated 3-sentence clinical summary
    abstract: str         # Full abstract for expanded view
    pubmed_url: str

class ResearchFeedResponse(BaseModel):
    articles: List[ResearchArticle]
    page: int
    total_found: int
    has_more: bool

# ── Research Topics ───────────────────────────────────────────────────────
TOPIC_QUERIES = {
    "general":     "medicine[MeSH Major Topic] AND clinical trial[pt]",
    "pediatrics":  "pediatrics[MeSH Major Topic] AND clinical trial[pt]",
    "cardiology":  "cardiology[MeSH Major Topic] AND clinical trial[pt]",
    "neurology":   "neurology[MeSH Major Topic] AND clinical trial[pt]",
    "infectious":  "infectious disease[MeSH Major Topic] AND clinical trial[pt]",
    "emergency":   "emergency medicine[MeSH Major Topic]",
}

PAGE_SIZE = 5

@router.get("/research/feed", response_model=ResearchFeedResponse)
async def get_research_feed(
    page: int = Query(default=1, ge=1, description="Page number, 1-indexed"),
    topic: str = Query(default="general", description="Medical topic filter"),
):
    """
    Returns 5 latest PubMed articles with AI-generated clinical summaries.
    Sorted by publication date descending (newest first).
    """
    query = TOPIC_QUERIES.get(topic, TOPIC_QUERIES["general"])
    retstart = (page - 1) * PAGE_SIZE

    # ── Step 1: Search PubMed ─────────────────────────────────────────────
    try:
        search_handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=PAGE_SIZE,
            retstart=retstart,
            sort="pub+date",    # Newest first
            usehistory="y",
        )
        search_results = Entrez.read(search_handle)
        search_handle.close()
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        raise HTTPException(status_code=502, detail="PubMed search service unavailable")

    ids = search_results.get("IdList", [])
    total_found = int(search_results.get("Count", 0))

    if not ids:
        return ResearchFeedResponse(articles=[], page=page, total_found=0, has_more=False)

    # ── Step 2: Fetch full article metadata ───────────────────────────────
    try:
        fetch_handle = Entrez.efetch(
            db="pubmed",
            id=",".join(ids),
            rettype="abstract",
            retmode="xml"
        )
        records = Entrez.read(fetch_handle)
        fetch_handle.close()
    except Exception as e:
        logger.error(f"PubMed fetch failed: {e}")
        raise HTTPException(status_code=502, detail="PubMed fetch service unavailable")

    # ── Step 3: Parse + Summarize each article ────────────────────────────
    articles: List[ResearchArticle] = []
    for article_rec in records.get("PubmedArticle", []):
        try:
            medline   = article_rec["MedlineCitation"]
            art       = medline["Article"]
            pmid      = str(medline["PMID"])
            title     = str(art.get("ArticleTitle", "Untitled")).strip()

            # Abstract
            abstract_obj = art.get("Abstract", {})
            abstract_parts = abstract_obj.get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join(str(p) for p in abstract_parts).strip()
            else:
                abstract = str(abstract_parts).strip()

            if not abstract or len(abstract) < 60:
                continue   # Skip articles without useful abstracts

            # Journal + year
            journal_obj = art.get("Journal", {})
            journal     = str(journal_obj.get("Title", "Unknown Journal"))
            pub_date    = journal_obj.get("JournalIssue", {}).get("PubDate", {})
            year        = str(pub_date.get("Year", pub_date.get("MedlineDate", "2025")))

            # Authors
            author_list = art.get("AuthorList", [])
            if author_list:
                first = author_list[0]
                last_name  = first.get("LastName", "")
                fore_name  = first.get("ForeName", "")
                authors = f"{last_name} {fore_name}"
                if len(author_list) > 1:
                    authors += f" et al."
            else:
                authors = "Unknown Authors"

            # ── Gemini summary ────────────────────────────────────────────
            summary = _generate_summary(title, abstract)

            articles.append(ResearchArticle(
                pmid=pmid,
                title=title,
                journal=journal,
                year=year,
                authors=authors,
                summary=summary,
                abstract=abstract,
                pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))

            # Brief pause between Gemini calls to avoid 429
            time.sleep(0.5)

        except Exception as parse_err:
            logger.warning(f"Skipping article due to parse error: {parse_err}")
            continue

    has_more = (retstart + PAGE_SIZE) < total_found
    return ResearchFeedResponse(
        articles=articles,
        page=page,
        total_found=total_found,
        has_more=has_more,
    )


def _generate_summary(title: str, abstract: str) -> str:
    """Uses Gemini Flash to generate a 2-3 sentence clinical summary."""
    prompt = f"""You are a senior physician writing for a clinical bulletin aimed at medical residents.
Write a concise 2-3 sentence summary of this research for a busy doctor.
Focus on: what was studied, key finding, and clinical relevance.
Be direct. No filler phrases like "This study". Start with the main finding.

Title: {title}
Abstract: {abstract[:1500]}

2-3 sentence clinical summary:"""
    try:
        response = _gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini summary failed for PMID, using abstract snippet: {e}")
        return abstract[:280] + "..."
