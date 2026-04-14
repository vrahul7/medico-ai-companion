from Bio import Entrez
import os

# Set your NCBI email (required by NCBI)
Entrez.email = os.getenv("NCBI_EMAIL", "developer@medico.test")

# Optional API key for higher rate limits
api_key = os.getenv("NCBI_API_KEY")
if api_key:
    Entrez.api_key = api_key

def fetch_pubmed_abstracts(query: str, limit: int = 3):
    """
    Search PubMed for the given clinical query and return formatted abstracts.
    """
    try:
        # Search PubMed
        handle = Entrez.esearch(db="pubmed", term=query, retmax=limit)
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record.get("IdList", [])
        
        if not id_list:
            return []
            
        # Fetch details for the IDs
        fetch_handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
        articles = Entrez.read(fetch_handle)
        fetch_handle.close()
        
        results = []
        for article in articles.get("PubmedArticle", []):
            medline = article.get("MedlineCitation", {})
            article_data = medline.get("Article", {})
            
            title = article_data.get("ArticleTitle", "No title")
            
            # Extract Abstract
            abstract_text = ""
            abstract = article_data.get("Abstract", {}).get("AbstractText", [])
            if abstract:
                abstract_text = " ".join([str(a) for a in abstract])
            else:
                abstract_text = "No abstract available."
            
            # Construct PubMed URL
            pmid = medline.get("PMID", "")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
            
            results.append({
                "title": title,
                "snippet": abstract_text,
                "url": url,
                "type": "pubmed"
            })
            
        return results
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")
        return []
