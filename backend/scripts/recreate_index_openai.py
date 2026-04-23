"""
recreate_index_openai.py — Reset Pinecone for OpenAI Embeddings
================================================================
Deletes the existing medico-ai-companion index and recreates it
at 3072 dimensions to match OpenAI text-embedding-3-large.

OpenAI text-embedding-3-large → 3072 dimensions
(Same as existing Gemini gemini-embedding-001 setup — no dimension change needed
 if index was already at 3072. Script will check and skip if already correct.)

Run ONCE before ingestion:
    python scripts/recreate_index_openai.py
"""
import os
import time
import sys
import argparse
from dotenv import load_dotenv

load_dotenv(override=True)

from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME       = os.getenv("PINECONE_INDEX", "medico-ai-companion")
CORRECT_DIM      = 3072
METRIC           = "cosine"
CLOUD            = "aws"
REGION           = "us-east-1"

if not PINECONE_API_KEY:
    print("[FATAL] PINECONE_API_KEY not set in .env")
    sys.exit(1)

ap = argparse.ArgumentParser()
ap.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
args = ap.parse_args()

pc = Pinecone(api_key=PINECONE_API_KEY)

print("=" * 60)
print("  Medico AI -- Pinecone Index Reset")
print(f"  Target: {INDEX_NAME} @ {CORRECT_DIM} dims (text-embedding-3-large)")
print("=" * 60)

# -- Step 1: Check existing index ----------------------------------------------
existing = [idx.name for idx in pc.list_indexes()]

if INDEX_NAME in existing:
    info = pc.describe_index(INDEX_NAME)
    current_dim = info.dimension
    print(f"\n[INFO] Found existing index '{INDEX_NAME}' -- dimension: {current_dim}")

    if current_dim == CORRECT_DIM:
        print(f"[OK]   Dimension is already {CORRECT_DIM}. Will delete to clear old Gemini vectors...")
        if not args.yes:
            answer = input("\nWARNING: This will DELETE all existing vectors. Proceed? [yes/no]: ").strip().lower()
            if answer != "yes":
                print("[ABORTED] Index not modified.")
                sys.exit(0)
        else:
            print("[AUTO] --yes flag set. Proceeding with deletion.")

    print(f"\n[ACTION] Deleting index '{INDEX_NAME}'...")
    pc.delete_index(INDEX_NAME)

    for i in range(30):
        time.sleep(2)
        remaining = [idx.name for idx in pc.list_indexes()]
        if INDEX_NAME not in remaining:
            print(f"[OK] Index deleted after {(i+1)*2}s.")
            break
        print(f"  [{(i+1)*2}s] Waiting for deletion...")
    else:
        print("[WARNING] Deletion taking longer than expected. Proceeding anyway...")
else:
    print(f"\n[INFO] Index '{INDEX_NAME}' does not exist. Creating fresh.")

# ── Step 2: Create index at correct dimension ─────────────────────────────────
print(f"\n[CREATE] Creating '{INDEX_NAME}' -> {CORRECT_DIM} dims, metric={METRIC}...")
pc.create_index(
    name=INDEX_NAME,
    dimension=CORRECT_DIM,
    metric=METRIC,
    spec=ServerlessSpec(cloud=CLOUD, region=REGION),
)

# ── Step 3: Wait for ready ────────────────────────────────────────────────────
print("[WAIT] Waiting for index to become ready...")
for i in range(60):
    time.sleep(3)
    status = pc.describe_index(INDEX_NAME).status
    ready = status.get("ready", False) if isinstance(status, dict) else getattr(status, "ready", False)
    if i % 5 == 0:
        print(f"  [{i*3}s] Status: {status}")
    if ready:
        print(f"\n[READY] Index '{INDEX_NAME}' is live!")
        break
else:
    print("[WARNING] Index may still be initialising. Check Pinecone console.")

print()
print("=" * 60)
print(f"  Index:          {INDEX_NAME}")
print(f"  Dimension:      {CORRECT_DIM}  (OpenAI text-embedding-3-large)")
print(f"  Metric:         {METRIC}")
print(f"  Cloud/Region:   {CLOUD} / {REGION}")
print("=" * 60)
print()
print("[NEXT] Run ingestion:")
print("  python scripts/ingest_openai.py --all")
print()
