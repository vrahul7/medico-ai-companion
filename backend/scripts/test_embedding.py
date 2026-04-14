"""
Verify the correct embedding model works end-to-end.
"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

result = client.models.embed_content(
    model="models/gemini-embedding-001",
    contents="What is the treatment for pediatric acute asthma exacerbation?",
    config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
)

dims = len(result.embeddings[0].values)
print(f"[OK] gemini-embedding-001 works correctly.")
print(f"[OK] Vector dimensions: {dims}")
