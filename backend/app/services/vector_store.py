import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

index_name = "medico-ai-companion"

def query_local_corpus(query: str, k: int = 3):
    """
    Search the Pinecone vector store containing uploaded medical textbooks.
    Returns matched sections of text with their metadata.
    """
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    
    # Ensure index exists before querying
    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        return []

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = PineconeVectorStore(index=pc.Index(index_name), embedding=embeddings)
    
    # Perform similarity search
    results = vector_store.similarity_search(query, k=k)
    
    formatted_results = []
    for doc in results:
        formatted_results.append({
            "title": doc.metadata.get("title", "Offline Corpus"),
            "snippet": doc.page_content,
            "type": doc.metadata.get("type", "offline_book"),
            "url": None
        })
        
    return formatted_results
