"""
rss_fetcher.py — RSS Guidelines Adapter
========================================
Fetches the latest guidelines/news via RSS from trusted health organizations.
Includes in-memory TTL caching to avoid spamming the upstream servers.
"""

import time
import feedparser
import requests
import logging
from typing import List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Very basic TTL Cache to avoid hammering external feeds
_CACHE = {}
_CACHE_TTL = 3600  # 1 hour

class RSSItem(BaseModel):
    title: str
    link: str
    published: str
    summary: str
    source: str
    pdf_url: str | None = None

def fetch_rss_guidelines(page: int = 1, limit_per_feed: int = 5) -> List[RSSItem]:
    global _CACHE
    now = time.time()
    cache_key = f"guidelines_p{page}"

    if cache_key in _CACHE and (now - _CACHE[cache_key]["time"]) < _CACHE_TTL:
        return _CACHE[cache_key]["data"]

    results = []

    # 1. Fetch DOHFW Guidelines via JSON API
    try:
        dohfw_url = f"https://www.mohfw-dohfw.gov.in/cms/wp-json/document/documents?document_category=guidelines&limit={limit_per_feed}&page={page}"
        response = requests.get(dohfw_url, timeout=10, verify=False)
        if response.status_code == 200:
            items = response.json().get("posts", []) if isinstance(response.json(), dict) else response.json()
            for item in items:
                pdf_url = None
                # The fast JSON lacks the direct PDF URL, so we query the individual post endpoint
                post_id = item.get("ID")
                if post_id:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        media_resp = requests.get(f"https://www.mohfw-dohfw.gov.in/cms/wp-json/post-page/post?id={post_id}", timeout=5, headers=headers, verify=False)
                        if media_resp.status_code == 200:
                            media_json = media_resp.json()
                            pdf_info = media_json.get("posts", {}).get("acf_data", {}).get("pdf", {})
                            if pdf_info and "url" in pdf_info:
                                pdf_url = pdf_info["url"]
                    except Exception as e:
                        logger.error(f"Could not resolve DOHFW PDF for {post_id}: {e}")

                results.append(RSSItem(
                    title=item.get("post_title", "DOHFW Guideline"),
                    link=f"https://www.mohfw-dohfw.gov.in/documents/guidelines/{item.get('post_name', '')}",
                    published=item.get("post_date", ""),
                    summary="Department of Health and Family Welfare Official Guideline.",
                    source="DOHFW",
                    pdf_url=pdf_url
                ))
    except Exception as e:
        logger.error(f"Error fetching DOHFW guidelines: {e}")

    # 2. Fetch WHO SEARO Guidelines via hidden Sitecore JSON API
    try:
        skip = (page - 1) * limit_per_feed
        who_url = f"https://www.who.int/api/hubs/publications?sf_site=15210d59-ad60-47ff-a542-7ed76645f0c7&sf_provider=OpenAccessProvider&sf_culture=en&$orderby=PublicationDateAndTime%20desc&$select=Title,ItemDefaultUrl,FormatedDate,Tag,ThumbnailUrl,DownloadUrl,TrimmedTitle&%24format=json&%24top={limit_per_feed}&%24skip={skip}&%24filter=publishingoffices%2Fany(a%3Aa%20eq%20c09761c0-ab8e-4cfa-9744-99509c4d306b)&%24count=true"
        response = requests.get(who_url, timeout=10)
        if response.status_code == 200:
            items = response.json().get("value", [])
            for item in items:
                results.append(RSSItem(
                    title=item.get("Title", "WHO Guideline"),
                    link=f"https://www.who.int/publications/i/item{item.get('ItemDefaultUrl', '')}",
                    published=item.get("FormatedDate", ""),
                    summary=item.get("Tag", "Technical Document"),
                    source="WHO SEARO",
                    pdf_url=("https://iris.who.int" + item.get("DownloadUrl")) if item.get("DownloadUrl", "").startswith("/") else item.get("DownloadUrl")
                ))
    except Exception as e:
        logger.error(f"Error fetching WHO guidelines: {e}")

    # Cache the result
    _CACHE[cache_key] = {"time": now, "data": results}
    return results
