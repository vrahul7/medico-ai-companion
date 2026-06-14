"""
rss_fetcher.py — RSS Guidelines Adapter
========================================
Fetches the latest guidelines/news via RSS and web APIs from trusted health organizations.
Includes in-memory TTL caching to avoid spamming the upstream servers.
"""

import time
import feedparser
import requests
import logging
import concurrent.futures
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
    clinical_digest: str | None = None

def fetch_rss_guidelines(page: int = 1, limit_per_feed: int = 5) -> List[RSSItem]:
    global _CACHE
    now = time.time()
    cache_key = f"guidelines_p{page}"

    if cache_key in _CACHE and (now - _CACHE[cache_key]["time"]) < _CACHE_TTL:
        return _CACHE[cache_key]["data"]

    results = []

    # 1. Fetch DOHFW Guidelines via JSON API in Parallel
    try:
        dohfw_url = f"https://www.mohfw-dohfw.gov.in/cms/wp-json/document/documents?document_category=guidelines&limit={limit_per_feed}&page={page}"
        response = requests.get(dohfw_url, timeout=10, verify=False)
        if response.status_code == 200:
            posts = response.json().get("posts", []) if isinstance(response.json(), dict) else response.json()
            
            def resolve_dohfw_pdf(item):
                pdf_url = None
                post_id = item.get("ID")
                if post_id:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        media_resp = requests.get(f"https://www.mohfw-dohfw.gov.in/cms/wp-json/post-page/post?id={post_id}", timeout=3, headers=headers, verify=False)
                        if media_resp.status_code == 200:
                            media_json = media_resp.json()
                            pdf_info = media_json.get("posts", {}).get("acf_data", {}).get("pdf", {})
                            if pdf_info and "url" in pdf_info:
                                pdf_url = pdf_info["url"]
                    except Exception as e:
                        logger.error(f"Could not resolve DOHFW PDF for {post_id}: {e}")
                return RSSItem(
                    title=item.get("post_title", "DOHFW Guideline"),
                    link=f"https://www.mohfw-dohfw.gov.in/documents/guidelines/{item.get('post_name', '')}",
                    published=item.get("post_date", "Recent"),
                    summary="Department of Health and Family Welfare Official Guideline.",
                    source="DOHFW",
                    pdf_url=pdf_url
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                dohfw_items = list(executor.map(resolve_dohfw_pdf, posts))
                results.extend(dohfw_items)
    except Exception as e:
        logger.error(f"Error fetching DOHFW guidelines: {e}")

    # 2. Fetch WHO SEARO Guidelines via Sitecore JSON API
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
                    published=item.get("FormatedDate", "Recent"),
                    summary=item.get("Tag", "Technical Document"),
                    source="WHO SEARO",
                    pdf_url=("https://iris.who.int" + item.get("DownloadUrl")) if item.get("DownloadUrl", "").startswith("/") else item.get("DownloadUrl")
                ))
    except Exception as e:
        logger.error(f"Error fetching WHO guidelines: {e}")

    # 2b. Fetch DGHS Technical Guidelines via HTML Scraper
    try:
        dghs_url = "https://dghs.mohfw.gov.in/technical-guidelines.php"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        dghs_resp = requests.get(dghs_url, timeout=10, headers=headers, verify=False)
        if dghs_resp.status_code == 200:
            from bs4 import BeautifulSoup
            dghs_soup = BeautifulSoup(dghs_resp.text, 'html.parser')
            seen_dghs = set()
            dghs_list = []
            for a in dghs_soup.find_all('a'):
                href = a.get('href', '')
                text = a.get_text().strip()
                if not href:
                    continue
                if href.endswith('.pdf') or '/uploads/assets/' in href:
                    # Clean title
                    text = " ".join(text.split())
                    if not text:
                        parent_text = a.parent.get_text().strip() if a.parent else ""
                        text = " ".join(parent_text.split())[:100]
                    if not text:
                        text = "DGHS Guideline Document"
                    
                    # Normalize URL
                    full_url = href
                    if href.startswith('uploads/'):
                        full_url = "https://dghs.mohfw.gov.in/" + href
                    elif href.startswith('/uploads/'):
                        full_url = "https://dghs.mohfw.gov.in" + href
                    elif not href.startswith('http'):
                        full_url = "https://dghs.mohfw.gov.in/" + href
                    
                    if full_url not in seen_dghs:
                        seen_dghs.add(full_url)
                        dghs_list.append(RSSItem(
                            title=text,
                            link=full_url,
                            published="Recent",
                            summary="Official technical guideline published by the Directorate General of Health Services (DGHS), MoHFW, Government of India.",
                            source="DGHS",
                            pdf_url=full_url
                        ))
            
            # Paginate in-memory
            start_idx = (page - 1) * limit_per_feed
            paged_dghs = dghs_list[start_idx : start_idx + limit_per_feed]
            results.extend(paged_dghs)
    except Exception as e:
        logger.error(f"Error fetching DGHS guidelines: {e}")

    # 3. Fetch AAP, EULAR, KDIGO, ISPN, IAP, ACOG, NNF, NNEP, AIIMS, BSPED via targeted EuropePMC API Queries
    guideline_queries = {
        "AAP": "(\"American Academy of Pediatrics\" OR \"AAP\") AND (guideline OR recommendation OR \"policy statement\")",
        "KDIGO": "kdigo AND (guideline OR recommendation)",
        "EULAR": "eular AND (recommendation OR guideline)",
        "ISPN": "ispn AND (recommendation OR guideline)",
        "IAP": "iap AND (guideline OR recommendation)",
        "ACOG": "acog AND (guideline OR recommendation)",
        "NNF": "\"National Neonatology Forum\" AND (guideline OR recommendation)",
        "NNEP": "\"National Neonatal Perinatal\" AND (guideline OR recommendation)",
        "AIIMS": "aiims AND (guideline OR consensus OR protocol)",
        "BSPED": "bsped AND (guideline OR recommendation)"
    }


    def fetch_single_pmc_guideline(source_name, query_str):
        items = []
        try:
            url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            limit = 2
            pageSize = page * limit
            params = {
                "query": query_str,
                "format": "json",
                "pageSize": pageSize,
                "resultType": "core"
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results_list = data.get("resultList", {}).get("result", [])
                start_idx = (page - 1) * limit
                paged_results = results_list[start_idx : start_idx + limit]
                for record in paged_results:
                    title = record.get("title", "Clinical Recommendation")
                    link = f"https://doi.org/{record.get('doi')}" if record.get('doi') else f"https://europepmc.org/article/MED/{record.get('id')}"
                    pub_year = record.get("pubYear", "Recent")
                    abstract = record.get("abstractText", f"Clinical practice recommendation statement published by {source_name}.")
                    
                    items.append(RSSItem(
                        title=title,
                        link=link,
                        published=pub_year,
                        summary=abstract,
                        source=source_name,
                        pdf_url=None
                    ))
        except Exception as ex:
            logger.error(f"EuropePMC query for {source_name} failed: {ex}")
        return items

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {
                executor.submit(fetch_single_pmc_guideline, name, q): name 
                for name, q in guideline_queries.items()
            }
            for future in concurrent.futures.as_completed(future_to_source):
                pmc_items = future.result()
                results.extend(pmc_items)
    except Exception as e:
        logger.error(f"Parallel EuropePMC guidelines fetch failed: {e}")

    # Deduplicate results by link
    seen_links = set()
    deduped_results = []
    for item in results:
        if item.link not in seen_links:
            seen_links.add(item.link)
            deduped_results.append(item)

    # Sort guidelines chronologically (latest first)
    import re
    from datetime import datetime
    
    def get_guideline_sort_key(item):
        pub_str = item.published or ""
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', pub_str)
        year = int(year_match.group(1)) if year_match else 2024
        
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %Y", "%B %Y"):
            try:
                dt = datetime.strptime(pub_str.strip(), fmt)
                return dt.timestamp()
            except:
                continue
        return float(year)
        
    deduped_results.sort(key=get_guideline_sort_key, reverse=True)

    # Cache the result
    _CACHE[cache_key] = {"time": now, "data": deduped_results}
    return deduped_results
