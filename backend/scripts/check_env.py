from dotenv import load_dotenv
import os
load_dotenv(override=True)
print("[CHECK] PINECONE_INDEX =", os.getenv("PINECONE_INDEX"))
print("[CHECK] PINECONE_API_KEY set =", bool(os.getenv("PINECONE_API_KEY")))
print("[CHECK] GOOGLE_API_KEY set =", bool(os.getenv("GOOGLE_API_KEY")))
