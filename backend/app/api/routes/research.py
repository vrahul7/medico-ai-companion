"""
research.py — Live Medical Research & Guidelines Feeds
======================================================
Exposes feeds for:
  1. GET /api/research/scholarly : PubMed articles + AI summaries
  2. GET /api/research/guidelines: Curated RSS guidelines + AI summaries
  3. POST /api/research/feedback : Record thumbs up/down feedback on summaries

Summary provider: Google Gemini 1.5/2.5
Database: Cloud Firestore caching
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

from app.services.llm_provider import GEMINI_API_KEY
from app.services.firebase_client import (
    get_cached_summary, 
    cache_summary, 
    submit_summary_feedback,
    mark_feed_as_read,
    get_read_feed_ids,
    toggle_bookmark,
    get_bookmarked_feed_ids
)
from app.services.rss_fetcher import fetch_rss_guidelines, RSSItem

load_dotenv(override=True)
logger = logging.getLogger(__name__)

router = APIRouter()

# ── Entrez Setup ──
Entrez.email   = os.getenv("ENTREZ_EMAIL", "medico@example.com")
Entrez.api_key = os.getenv("NCBI_API_KEY")

# ── Gemma Setup ──
genai.configure(api_key=GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", ""))
_gemma = genai.GenerativeModel(
    model_name="gemma-4-31b-it",
    generation_config={"temperature": 0.1, "max_output_tokens": 250}
)

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

class FeedbackRequest(BaseModel):
    user_id: str
    item_id: str
    rating: str
    comment: str | None = None


TOPIC_QUERIES = {
    "general":             "(medicine[MeSH Major Topic] OR therapeutics[MeSH Major Topic]) AND clinical trial[pt]",
    "general_medicine":    "internal medicine[MeSH Major Topic] AND clinical trial[pt]",
    "pediatrics":          "pediatrics[MeSH Major Topic] AND clinical trial[pt]",
    "dermatology":         "dermatology[MeSH Major Topic] AND clinical trial[pt]",
    "psychiatry":          "psychiatry[MeSH Major Topic] AND clinical trial[pt]",
    "anesthesia":          "(anesthesiology[MeSH Major Topic] OR critical care[MeSH Major Topic] OR intensive care[MeSH Major Topic]) AND clinical trial[pt]",
    "radiology":           "(radiology[MeSH Major Topic] OR diagnostic imaging[MeSH Major Topic]) AND clinical trial[pt]",
    "respiratory_medicine": "(respiratory tract diseases[MeSH Major Topic] OR pulmonary medicine[MeSH Major Topic]) AND clinical trial[pt]",
    "emergency_medicine":   "emergency medicine[MeSH Major Topic] AND clinical trial[pt]",
    "family_medicine":     "family practice[MeSH Major Topic] AND clinical trial[pt]",
    "pathology":           "pathology[MeSH Major Topic] AND clinical trial[pt]",
    "pharmacology":        "(pharmacology[MeSH Major Topic] OR drug therapy[MeSH Major Topic]) AND clinical trial[pt]",
    "microbiology":        "microbiology[MeSH Major Topic] AND clinical trial[pt]",
    "community_medicine":  "(public health[MeSH Major Topic] OR preventive medicine[MeSH Major Topic]) AND clinical trial[pt]",
    "forensic_medicine":   "forensic medicine[MeSH Major Topic] AND clinical trial[pt]",
    "surgery":             "surgery[MeSH Major Topic] AND clinical trial[pt]",
    "ophthalmology":       "ophthalmology[MeSH Major Topic] AND clinical trial[pt]",
    "ent":                 "otolaryngology[MeSH Major Topic] AND clinical trial[pt]",
    "orthopedics":         "(orthopedics[MeSH Major Topic] OR musculoskeletal diseases[MeSH Major Topic]) AND clinical trial[pt]",
    "obgyn":               "(obstetrics[MeSH Major Topic] OR gynecology[MeSH Major Topic]) AND clinical trial[pt]"
}

PAGE_SIZE = 5


@router.get("/research/scholarly", response_model=ScholarlyFeedResponse)
def get_scholarly_feed(
    page: int = Query(default=1, ge=1),
    topic: str = Query(default="general"),
    user_id: str | None = Query(default=None)
):
    query = TOPIC_QUERIES.get(topic, TOPIC_QUERIES["general"])

    from app.services.live_sources import live_sources
    
    try:
        # Programmatically query all 11 databases in parallel!
        raw_articles = live_sources.fetch_academic_feed(query, topic=topic, page=page)
        
        # Exclude read articles if user_id is provided
        if user_id:
            read_ids = get_read_feed_ids(user_id)
            if read_ids:
                read_ids_set = set(read_ids)
                raw_articles = [art for art in raw_articles if art.get("pmid") not in read_ids_set]
                
        total_found = len(raw_articles)
        
        # Since fetch_academic_feed already filters/pages at the API level,
        # we take the first PAGE_SIZE items.
        paged_raw = raw_articles[:PAGE_SIZE]
        
        def process_scholarly_item(item):
            try:
                title = item.get("title", "Untitled Article")
                abstract = item.get("abstract", "")
                summary = _generate_summary(title, abstract)
                return ResearchArticle(
                    pmid=item.get("pmid", "0"),
                    title=title,
                    journal=item.get("journal", "Clinical Journal"),
                    year=item.get("year", "2024"),
                    authors=item.get("authors", "Et al."),
                    summary=summary,
                    abstract=abstract,
                    pubmed_url=item.get("pubmed_url", ""),
                    pdf_url=item.get("pdf_url")
                )
            except Exception as e:
                logger.error(f"Error processing scholarly article summary: {e}")
                return None

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            articles = list(executor.map(process_scholarly_item, paged_raw))
            articles = [art for art in articles if art is not None]
                
        has_more = len(raw_articles) >= PAGE_SIZE
        return ScholarlyFeedResponse(articles=articles, page=page, total_found=total_found, has_more=has_more)
        
    except Exception as e:
        logger.error(f"Aggregated academic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query academic databases: {str(e)}")


def java_hashcode(s: str) -> int:
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return h


@router.get("/research/guidelines", response_model=GuidelinesFeedResponse)
def get_guidelines_feed(
    page: int = Query(default=1, ge=1),
    user_id: str | None = Query(default=None)
):
    """Returns curated RSS guidelines with AI generated summaries."""
    try:
        items = fetch_rss_guidelines(page=page)
        
        if user_id:
            read_ids = get_read_feed_ids(user_id)
            if read_ids:
                read_ids_set = set(read_ids)
                filtered_items = []
                for item in items:
                    item_id = str(java_hashcode(item.link)) if item.link else str(java_hashcode(item.title))
                    if item_id not in read_ids_set:
                        filtered_items.append(item)
                items = filtered_items

        # Since fetch_rss_guidelines already filters/pages at the source level,
        # we take the first PAGE_SIZE items.
        paged_items = items[:PAGE_SIZE]

        def process_guideline_item(item):
            try:
                if not item.summary or len(item.summary) < 20:
                    item_data = f"Guideline Title: {item.title}"
                else:
                    item_data = f"Title: {item.title}. Details: {item.summary}"
                
                ai_summary = _generate_summary("Medical Guideline", item_data)
                item.summary = ai_summary
                return item
            except Exception as e:
                logger.error(f"Error processing guideline summary: {e}")
                return item

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            paged_items = list(executor.map(process_guideline_item, paged_items))
        
        return GuidelinesFeedResponse(guidelines=paged_items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/research/feedback")
async def post_feedback(req: FeedbackRequest):
    """Records physician rating feedback in Firestore database."""
    success = submit_summary_feedback(
        user_id=req.user_id,
        item_id=req.item_id,
        rating=req.rating,
        comment=req.comment
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save rating feedback.")
    return {"status": "success", "message": "Feedback submitted successfully."}


# ── MedGemma / Vertex AI / Custom Endpoint Setup ──
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")
MEDGEMMA_API_URL = os.getenv("MEDGEMMA_API_URL")

def get_gcp_credentials():
    import json
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    
    gcp_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if gcp_cred_path and os.path.exists(gcp_cred_path):
        return service_account.Credentials.from_service_account_file(gcp_cred_path)
        
    firebase_tools_path = r"C:\Users\NC24008_Rahul\.config\configstore\firebase-tools.json"
    if os.path.exists(firebase_tools_path):
        try:
            with open(firebase_tools_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tokens = data.get("tokens", {})
            access_token = tokens.get("access_token")
            if access_token:
                return Credentials(token=access_token)
        except Exception as e:
            logger.warning(f"Failed to read credentials from firebase-tools.json: {e}")
            
    return None

def _generate_summary(title: str, abstract: str) -> str:
    """Generates a 2-3 sentence clinical summary using Google Gemma (caching in Firestore)."""
    clean_abstract = re.sub(r'<[^>]+>', '', abstract)
    content_hash = hashlib.sha256(f"{title}:{clean_abstract}".encode('utf-8')).hexdigest()
    
    # Check Firestore cache first
    cached = get_cached_summary(content_hash)
    if cached:
        return cached

    prompt = (
        f"You are a clinical AI assistant. Summarize this clinical paper/guideline in about 200 words (maximum 200 words). The summary must be crisp, precise, and highly readable for a busy physician.\n"
        f"Format requirements:\n"
        f"1. Start writing the summary immediately. Do not include any introductory remarks, metadata, thinking process, markdown bolding, or bullet points.\n"
        f"2. Focus only on critical thresholds, patient criteria, and clinical findings.\n"
        f"Title: {title}\n"
        f"Abstract: {clean_abstract[:1500]}"
    )

    # 1. Try Custom Hosted MedGemma API URL (e.g. vLLM or Ollama deployment)
    if MEDGEMMA_API_URL:
        try:
            import requests
            headers = {"Content-Type": "application/json"}
            model_name = os.getenv("MEDGEMMA_MODEL_NAME", "medgemma")
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 250
            }
            resp = requests.post(MEDGEMMA_API_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                resp_json = resp.json()
                if "choices" in resp_json:
                    final_summary = resp_json["choices"][0]["message"]["content"].strip()
                elif "response" in resp_json:
                    final_summary = resp_json["response"].strip()
                else:
                    final_summary = resp_json.get("text", "").strip()
                
                if final_summary:
                    cache_summary(content_hash, final_summary)
                    return final_summary
        except Exception as e:
            logger.warning(f"[Research Summary] MedGemma Custom API call failed: {e}. Trying Vertex AI...")

    # 2. Try Vertex AI custom endpoint if configured
    if VERTEX_ENDPOINT_ID and VERTEX_PROJECT and VERTEX_ENDPOINT_ID != "your-deployed-endpoint-id":
        try:
            from google.cloud import aiplatform
            creds = get_gcp_credentials()
            aiplatform.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION, credentials=creds)
            endpoint = aiplatform.Endpoint(VERTEX_ENDPOINT_ID)
            response = endpoint.predict(instances=[{"prompt": prompt}])
            if response.predictions:
                pred = response.predictions[0]
                final_summary = pred.get("content", "").strip() if isinstance(pred, dict) else str(pred).strip()
                if final_summary:
                    cache_summary(content_hash, final_summary)
                    return final_summary
        except Exception as e:
            logger.warning(f"[Research Summary] Vertex AI MedGemma endpoint prediction failed: {e}. Trying Google AI Studio...")

    # 3. Fallback to Google AI Studio Gemma 4
    try:
        response = _gemma.generate_content(prompt)
        final_summary = response.text.strip().replace("**", "")
        
        # If Gemma returned a reasoning trace, extract the final clean summary from the last lines
        if "\n" in final_summary:
            lines = [line.strip() for line in final_summary.split("\n") if line.strip()]
            for line in reversed(lines):
                if not line.startswith(("*", "-", "#", "Role:", "Task:", "Input:", "Constraint:", "Draft:", "Sentence:", "Final check:")) and len(line) > 50:
                    final_summary = line
                    break
                    
        # Store in Firestore cache
        cache_summary(content_hash, final_summary)
        return final_summary
    except Exception as e:
        logger.warning(f"[Research Summary] Gemma 4 31B failed: {e}. Falling back to gemini-2.5-flash...")
        try:
            fallback_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            response = fallback_model.generate_content(prompt)
            final_summary = response.text.strip().replace("**", "")
            cache_summary(content_hash, final_summary)
            return final_summary
        except Exception as e2:
            logger.error(f"[Research Summary] Gemini fallback also failed: {e2}")
            return clean_abstract[:280] + "..."


class ReadRequest(BaseModel):
    user_id: str
    item_id: str

class BookmarkRequest(BaseModel):
    user_id: str
    item_id: str
    bookmarked: bool

@router.post("/research/read")
async def post_read_status(req: ReadRequest):
    """Marks a feed item as read by the physician."""
    success = mark_feed_as_read(user_id=req.user_id, item_id=req.item_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save read status.")
    return {"status": "success", "message": "Feed item marked as read."}

@router.post("/research/bookmark")
async def post_bookmark_status(req: BookmarkRequest):
    """Bookmarks or unbookmarks a feed item for the physician."""
    success = toggle_bookmark(user_id=req.user_id, item_id=req.item_id, bookmarked=req.bookmarked)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to toggle bookmark status.")
    return {"status": "success", "message": "Bookmark status updated successfully."}

@router.get("/research/bookmarks")
async def get_bookmarks(user_id: str = Query(...)):
    """Retrieves all bookmarked item IDs for the physician."""
    bookmarked_ids = get_bookmarked_feed_ids(user_id=user_id)
    return {"bookmarked_ids": bookmarked_ids}
