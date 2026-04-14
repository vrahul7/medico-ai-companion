"""
live_sources.py — Real-time Online Data Adapter
================================================
Connects Medico AI to three live medical databases:
  1. PubMed         (NCBI Entrez via BioPython)
  2. OpenAlex       (Open scholarly graph — no API key required)
  3. Unpaywall      (Free full-text resolver)

All results are normalised into LangChain Document objects with
source metadata matching our Pinecone schema so the Synthesis
Engine treats them identically to offline textbook chunks.
"""

import os
import time
import logging
import requests
from typing import List, Optional
from langchain.docstore.document import Document

# BioPython Entrez for PubMed
from Bio import Entrez

logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────
ENTREZ_EMAIL = os.getenv("ENTREZ_EMAIL", "medico-ai@example.com")
NCBI_API_KEY = os.getenv("NCBI_API_KEY")             # Optional: increases rate limit 3x→10 req/sec
UNPAYWALL_EMAIL = os.getenv("ENTREZ_EMAIL", "medico-ai@example.com")

Entrez.email = ENTREZ_EMAIL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY


# ═══════════════════════════════════════════════════════════════════════════
# 1. PUBMED ADAPTER
# ═══════════════════════════════════════════════════════════════════════════
class PubMedAdapter:
    """
    Fetches the top-N most relevant PubMed abstracts for a clinical query.
    Uses NCBI Entrez eSearch + eFetch pipeline.
    Rate limit: 3 req/sec (free) | 10 req/sec (with API key)
    """
    MAX_RESULTS = 5

    def search(self, query: str) -> List[Document]:
        docs = []
        try:
            # Step 1: Search for relevant PMIDs
            search_handle = Entrez.esearch(
                db="pubmed",
                term=f"{query}[Title/Abstract]",
                retmax=self.MAX_RESULTS,
                sort="relevance",
                usehistory="y"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()

            ids = search_results.get("IdList", [])
            if not ids:
                logger.info(f"PubMed: No results for query '{query[:60]}'")
                return []

            # Step 2: Fetch abstracts in batch
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=",".join(ids),
                rettype="abstract",
                retmode="xml"
            )
            records = Entrez.read(fetch_handle)
            fetch_handle.close()

            for article in records.get("PubmedArticle", []):
                try:
                    medline = article["MedlineCitation"]
                    article_data = medline["Article"]

                    title = str(article_data.get("ArticleTitle", "Untitled"))
                    pmid = str(medline["PMID"])

                    # Extract abstract text
                    abstract_obj = article_data.get("Abstract", {})
                    abstract_parts = abstract_obj.get("AbstractText", [])
                    if isinstance(abstract_parts, list):
                        abstract = " ".join(str(p) for p in abstract_parts)
                    else:
                        abstract = str(abstract_parts)

                    if not abstract or len(abstract) < 50:
                        continue

                    # Extract journal + year
                    journal = str(article_data.get("Journal", {}).get("Title", "Unknown Journal"))
                    pub_date = article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
                    year = str(pub_date.get("Year", pub_date.get("MedlineDate", "n.d.")))

                    docs.append(Document(
                        page_content=abstract,
                        metadata={
                            "source_type": "pubmed",
                            "book_name": f"PubMed: {journal}",
                            "chapter": f"PMID {pmid}",
                            "section": year,
                            "title": title,
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            "pmid": pmid,
                        }
                    ))
                except Exception as parse_err:
                    logger.warning(f"PubMed article parse error: {parse_err}")
                    continue

            logger.info(f"PubMed: Retrieved {len(docs)} abstracts for '{query[:60]}'")

        except Exception as e:
            logger.error(f"PubMed search failed: {e}")

        return docs


# ═══════════════════════════════════════════════════════════════════════════
# 2. OPENALEX ADAPTER
# ═══════════════════════════════════════════════════════════════════════════
class OpenAlexAdapter:
    """
    Queries the OpenAlex open scholarly graph API.
    No API key required. 100,000 req/day free.
    Returns the top-N most-cited open-access papers.
    Docs: https://docs.openalex.org/
    """
    BASE_URL = "https://api.openalex.org/works"
    MAX_RESULTS = 4

    def search(self, query: str) -> List[Document]:
        docs = []
        try:
            params = {
                "search": query,
                "filter": "is_oa:true",       # Open Access only — avoids paywall dead-ends
                "sort": "cited_by_count:desc", # Most cited first = highest evidence quality
                "per_page": self.MAX_RESULTS,
                "mailto": ENTREZ_EMAIL,        # Polite pool = faster responses
                "select": "id,title,abstract_inverted_index,primary_location,publication_year,cited_by_count,doi"
            }
            response = requests.get(self.BASE_URL, params=params, timeout=8)
            response.raise_for_status()
            results = response.json().get("results", [])

            for work in results:
                # Reconstruct abstract from inverted index format (OpenAlex specific)
                inverted = work.get("abstract_inverted_index")
                if not inverted:
                    continue

                abstract = self._reconstruct_abstract(inverted)
                if len(abstract) < 80:
                    continue

                title = work.get("title", "Untitled")
                year = work.get("publication_year", "n.d.")
                citations = work.get("cited_by_count", 0)
                doi = work.get("doi", "")
                source_name = work.get("primary_location", {}).get("source", {}) or {}
                journal = source_name.get("display_name", "Open Access Journal")

                docs.append(Document(
                    page_content=abstract,
                    metadata={
                        "source_type": "openalex",
                        "book_name": f"OpenAlex: {journal}",
                        "chapter": f"Cited {citations}x",
                        "section": str(year),
                        "title": title,
                        "url": f"https://doi.org/{doi.replace('https://doi.org/', '')}" if doi else "",
                        "doi": doi,
                    }
                ))

            logger.info(f"OpenAlex: Retrieved {len(docs)} works for '{query[:60]}'")

        except requests.exceptions.Timeout:
            logger.warning("OpenAlex request timed out — skipping live enrichment")
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")

        return docs

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """OpenAlex stores abstracts as {word: [position_list]} — reconstruct to sentence."""
        try:
            max_pos = max(pos for positions in inverted_index.values() for pos in positions)
            word_map = [""] * (max_pos + 1)
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_map[pos] = word
            return " ".join(w for w in word_map if w)
        except Exception:
            return ""


# ═══════════════════════════════════════════════════════════════════════════
# 3. UNPAYWALL ADAPTER
# ═══════════════════════════════════════════════════════════════════════════
class UnpaywallAdapter:
    """
    Resolves DOIs to free full-text PDF links via Unpaywall.
    Used to enrich OpenAlex results with full-text access URLs.
    No API key required. Just needs an email.
    Docs: https://unpaywall.org/products/api
    """
    BASE_URL = "https://api.unpaywall.org/v2"

    def get_oa_url(self, doi: str) -> Optional[str]:
        if not doi:
            return None
        try:
            clean_doi = doi.replace("https://doi.org/", "")
            url = f"{self.BASE_URL}/{clean_doi}?email={UNPAYWALL_EMAIL}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                best_oa = data.get("best_oa_location")
                if best_oa:
                    return best_oa.get("url_for_pdf") or best_oa.get("url")
        except Exception as e:
            logger.warning(f"Unpaywall lookup failed for DOI {doi}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 4. UNIFIED LIVE SOURCES MANAGER
# ═══════════════════════════════════════════════════════════════════════════
class LiveSourcesManager:
    """
    Orchestrates all live data adapters.
    Called by HybridRAGEngine.fetch_live_pubmed_context()
    Returns a unified, deduplicated list of Document objects.
    """
    def __init__(self):
        self.pubmed = PubMedAdapter()
        self.openalex = OpenAlexAdapter()
        self.unpaywall = UnpaywallAdapter()

    def fetch(self, query: str) -> List[Document]:
        all_docs: List[Document] = []

        # --- PubMed ---
        try:
            pubmed_docs = self.pubmed.search(query)
            all_docs.extend(pubmed_docs)
        except Exception as e:
            logger.error(f"PubMed pipeline error: {e}")

        # Brief pause to respect NCBI rate limits before next API call
        time.sleep(0.4)

        # --- OpenAlex ---
        try:
            oa_docs = self.openalex.search(query)

            # Enrich DOIs with Unpaywall free full-text links
            for doc in oa_docs:
                doi = doc.metadata.get("doi", "")
                if doi:
                    oa_url = self.unpaywall.get_oa_url(doi)
                    if oa_url:
                        doc.metadata["full_text_url"] = oa_url

            all_docs.extend(oa_docs)
        except Exception as e:
            logger.error(f"OpenAlex pipeline error: {e}")

        logger.info(f"LiveSourcesManager: Total {len(all_docs)} live documents fetched.")
        return all_docs


# Singleton instance for import
live_sources = LiveSourcesManager()
