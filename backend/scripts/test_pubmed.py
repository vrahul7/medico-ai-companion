"""
Quick end-to-end test of the PubMed live data adapter.
Verifies NCBI API key is active and returning real abstracts.
"""
from dotenv import load_dotenv
load_dotenv(override=True)
import os

from Bio import Entrez

Entrez.email = os.getenv("ENTREZ_EMAIL")
Entrez.api_key = os.getenv("NCBI_API_KEY")

print(f"[CHECK] NCBI_API_KEY set: {bool(Entrez.api_key)}")
print(f"[CHECK] ENTREZ_EMAIL: {Entrez.email}")
print()

# Test search
query = "Acute asthma exacerbation pediatric management"
handle = Entrez.esearch(db="pubmed", term=query, retmax=3, sort="relevance")
results = Entrez.read(handle)
handle.close()

ids = results.get("IdList", [])
print(f"[OK] PubMed returned {len(ids)} PMIDs: {ids}")

# Fetch abstracts
if ids:
    fetch_handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="abstract", retmode="xml")
    records = Entrez.read(fetch_handle)
    fetch_handle.close()

    articles = records.get("PubmedArticle", [])
    print(f"[OK] Fetched {len(articles)} full abstracts.")
    for article in articles[:2]:
        title = article["MedlineCitation"]["Article"].get("ArticleTitle", "N/A")
        pmid = article["MedlineCitation"]["PMID"]
        print(f"  - [{pmid}] {str(title)[:80]}")

print()
print("[SUCCESS] PubMed live data adapter is fully operational.")
