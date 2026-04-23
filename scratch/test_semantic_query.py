import os
import sys
from pathlib import Path

# Add backend to path so we can import app modules
backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app.services.rag import HybridRAGEngine

def test_query(query_text):
    print(f"\nQUERY: {query_text}")
    print("-" * 50)
    
    engine = HybridRAGEngine()
    
    print("Retrieving context from Gold Standard library...")
    # Using the namespaced search directly
    from langchain_pinecone import PineconeVectorStore
    vectorstore = PineconeVectorStore(index_name=engine.index_name, embedding=engine.embeddings)
    docs = vectorstore.similarity_search(query_text, k=3, namespace="piyushgupta_vol1_semantic")
    
    if not docs:
        print("No results found. The data might still be in the 'upsert' queue or the namespace check failed.")
        return

    print(f"Found {len(docs)} relevant clinical segments:\n")
    for i, doc in enumerate(docs):
        meta = doc.metadata
        print(f"--- RESULT {i+1} ---")
        print(f"SOURCE: {meta.get('book_name', 'Unknown')}")
        print(f"CONTEXT: {meta.get('chapter', 'N/A')} > {meta.get('section', 'N/A')}")
        print(f"PAGES: {meta.get('source_pages', 'N/A')}")
        print(f"SNIPPET: {doc.page_content[:500]}...")
        print("-" * 30)

if __name__ == "__main__":
    # Common early-chapter pediatric topics
    test_query("indications for phototherapy in neonatal jaundice")
