"""
recreate_index.py — Fix Pinecone Index Dimension Mismatch
==========================================================
Deletes the existing medico-ai-companion index (768-dim, wrong)
and recreates it at 3072 dimensions to match gemini-embedding-001.

Run ONCE from the backend directory:
    python scripts/recreate_index.py
"""
import os
import time
from dotenv import load_dotenv
load_dotenv(override=True)

from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME       = os.getenv("PINECONE_INDEX", "medico-ai-companion")
CORRECT_DIM      = 3072   # gemini-embedding-001 output dimension
METRIC           = "cosine"
CLOUD            = "aws"
REGION           = "us-east-1"

pc = Pinecone(api_key=PINECONE_API_KEY)

# ── Step 1: Check existing index ──────────────────────────────────────────
existing = [idx.name for idx in pc.list_indexes()]

if INDEX_NAME in existing:
    info = pc.describe_index(INDEX_NAME)
    current_dim = info.dimension
    print(f"[INFO] Found index '{INDEX_NAME}' with dimension {current_dim}")
    if current_dim == CORRECT_DIM:
        print(f"[OK]   Dimension is already {CORRECT_DIM}. Nothing to do.")
        exit(0)
    else:
        print(f"[MISMATCH] Current: {current_dim} | Required: {CORRECT_DIM}")
        print(f"[ACTION] Deleting index '{INDEX_NAME}'...")
        pc.delete_index(INDEX_NAME)
        # Wait for deletion to propagate
        for i in range(30):
            time.sleep(2)
            remaining = [idx.name for idx in pc.list_indexes()]
            if INDEX_NAME not in remaining:
                print(f"[OK] Index deleted after {(i+1)*2}s.")
                break
        else:
            print("[WARNING] Index may still be deleting. Proceeding anyway...")
else:
    print(f"[INFO] Index '{INDEX_NAME}' does not exist yet. Creating fresh.")

# ── Step 2: Create index at correct dimension ─────────────────────────────
print(f"[CREATE] Creating '{INDEX_NAME}' at {CORRECT_DIM} dims, metric={METRIC}...")
pc.create_index(
    name=INDEX_NAME,
    dimension=CORRECT_DIM,
    metric=METRIC,
    spec=ServerlessSpec(cloud=CLOUD, region=REGION),
)

# ── Step 3: Wait for index to be ready ───────────────────────────────────
print("[WAIT] Waiting for index to be ready...")
for i in range(60):
    time.sleep(3)
    status = pc.describe_index(INDEX_NAME).status
    ready = status.get("ready", False) if isinstance(status, dict) else getattr(status, "ready", False)
    print(f"  [{i*3}s] Status: {status}")
    if ready:
        print(f"\n[READY] Index '{INDEX_NAME}' is live at {CORRECT_DIM} dims!")
        break
else:
    print("[WARNING] Index creation is taking longer than usual. Check Pinecone console.")

print()
print("=" * 60)
print(f"  Index:     {INDEX_NAME}")
print(f"  Dimension: {CORRECT_DIM}  (gemini-embedding-001)")
print(f"  Metric:    {METRIC}")
print(f"  Cloud:     {CLOUD} / {REGION}")
print("=" * 60)
print()
print("[DONE] You can now run ingest_all.bat to start ingestion.")
