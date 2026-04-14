import sys
sys.path.insert(0, '.')
from scripts.ingest_hierarchical import _INDEX_NAME, run_ingestion
print(f"[OK] Script imports correctly. Index: {_INDEX_NAME}")
print("[OK] Ingestion engine is ready.")
print("[READY] You can now run ingest_all.bat")
