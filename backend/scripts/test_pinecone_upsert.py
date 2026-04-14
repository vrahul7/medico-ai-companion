"""
Quick smoke test: embed one sentence and upsert to Pinecone.
Confirms 3072-dim vectors are accepted by the new index.
"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from google import genai
from google.genai import types
from pinecone import Pinecone

INDEX_NAME = os.getenv("PINECONE_INDEX")

# Embed
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
r = client.models.embed_content(
    model="models/gemini-embedding-001",
    contents=["Acute asthma exacerbation management in pediatric patients"],
    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
)
vec = r.embeddings[0].values
print(f"[OK] Embedding generated. Dimensions: {len(vec)}")

# Upsert
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(INDEX_NAME)
index.upsert(vectors=[{
    "id": "smoke_test_001",
    "values": vec,
    "metadata": {"book_name": "Smoke Test", "chapter": "Ch1", "text": "Test vector"}
}], namespace="smoke_test")

print(f"[OK] Upsert to '{INDEX_NAME}' successful.")
print(f"[OK] 3072-dim index is working correctly. Ready for ingest_all.bat")

# Clean up
index.delete(ids=["smoke_test_001"], namespace="smoke_test")
print(f"[OK] Test vector cleaned up.")
