"""
ingest_gemini.py — Medical Textbook Ingestion (Google text-embedding-004)
========================================================================
Ingests all medical PDFs into Pinecone using the paid Gemini API.
Optimized for text-embedding-004 (768-dim) and cost efficiency.

Key features:
  - Hierarchical parsing
  - Checkpoint/resume support
  - Batch embedding (Gemini allows 100 texts per call)
  - Automatic retry with exponential backoff
  - Progress tracking

Usage:
    python scripts/ingest_gemini.py --all
"""

import os
import re
import sys
import time
import json
import hashlib
import argparse
from typing import List, Tuple
from pypdf import PdfReader
from langchain.docstore.document import Document
from dotenv import load_dotenv

load_dotenv(override=True)

# -- Dependency check ----------------------------------------------------------
try:
    import google.generativeai as genai
except ImportError:
    print("[FATAL] google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

try:
    from pinecone import Pinecone
except ImportError:
    print("[FATAL] pinecone-client not installed. Run: pip install pinecone-client")
    sys.exit(1)

# -- Config --------------------------------------------------------------------
EMBED_MODEL    = "models/gemini-embedding-001"
EMBED_DIM      = 3072
BATCH_SIZE     = 100     # Gemini batch limit
UPSERT_SIZE    = 100     # Pinecone batch limit
MIN_PARA_LEN   = 80
MAX_RETRIES    = 10
THROTTLE_SEC   = 0.5     # Slight delay between batches

# -- Env validation ------------------------------------------------------------
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
INDEX_NAME       = os.getenv("PINECONE_INDEX", "medico-ai-companion")

if not GEMINI_API_KEY:
    print("[FATAL] GEMINI_API_KEY not set in .env")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# -- Book registry -------------------------------------------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPTS_DIR, "..", "data", "documents")

ALL_BOOKS: List[Tuple[str, str, str]] = [
    (os.path.join(DATA_DIR, "Nelson Textbook of Pediatrics  Volume 1   22ed  2024.pdf"), "Nelson_Vol1", "nelson_vol1_semantic"),
    (os.path.join(DATA_DIR, "Nelson Textbook of Pediatrics  Volume 2 22ed  2024.pdf"), "Nelson_Vol2", "nelson_vol2_semantic"),
    (os.path.join(DATA_DIR, "Piyush Gupta PG textbook of Pediatrics Vol1.pdf"), "PiyushGupta_Vol1", "piyushgupta_vol1_semantic"),
    (os.path.join(DATA_DIR, "Piyush Gupta PG Textbook of Pediatrics Vol 2_compressed.pdf"), "PiyushGupta_Vol2", "piyushgupta_vol2_semantic"),
    (os.path.join(DATA_DIR, "Piyush Gupta PG Textbook of Pediatrics Vol 3_compressed.pdf"), "PiyushGupta_Vol3", "piyushgupta_vol3_semantic"),
]

# -- Checkpoint Helpers --------------------------------------------------------
def _ckpt_path(namespace: str) -> str:
    return os.path.join(SCRIPTS_DIR, f".ckpt_{namespace}_gemini.json")

def _load_checkpoint(namespace: str) -> int:
    path = _ckpt_path(namespace)
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
                return data.get("last_uploaded_idx", 0)
        except: pass
    return 0

def _save_checkpoint(namespace: str, idx: int):
    with open(_ckpt_path(namespace), "w") as f:
        json.dump({"last_uploaded_idx": idx, "ts": time.time()}, f)

def _clear_checkpoint(namespace: str):
    path = _ckpt_path(namespace)
    if os.path.exists(path): os.remove(path)

# -- Hierarchical Parser -------------------------------------------------------
class HierarchicalMedicalParser:
    CHAPTER_RE = re.compile(r"^(?:CHAPTER|PART|UNIT|SECTION)\s+[\dIVXLC]+[\s:\.\-]+(.*)", re.IGNORECASE)
    SECTION_RE = re.compile(r"^(?:\d+[\.\-]\d+(?:[\.\-]\d+)?)\s+(.*)")
    CAPS_RE    = re.compile(r"^([A-Z][A-Z\s]{4,60})$")

    def __init__(self, file_path: str, book_id: str):
        self.file_path = file_path
        self.book_id   = book_id

    def parse(self) -> List[Document]:
        print(f"  [PARSE] Opening: {os.path.basename(self.file_path)}", flush=True)
        try:
            reader = PdfReader(self.file_path)
        except Exception as e:
            print(f"  [ERROR] PDF Open failed: {e}", flush=True)
            return []

        docs: List[Document] = []
        current_chapter = "Preface"
        current_section = "Introduction"

        for page_num, page in enumerate(reader.pages):
            if page_num % 100 == 0:
                print(f"  [PARSE] Page {page_num}/{len(reader.pages)}...", flush=True)
            text = page.extract_text()
            if not text: continue

            for para_num, paragraph in enumerate(text.split("\n\n")):
                paragraph = paragraph.strip()
                if len(paragraph) < MIN_PARA_LEN: continue

                first_line = paragraph.split("\n")[0].strip()
                ch = self.CHAPTER_RE.match(first_line)
                sc = self.SECTION_RE.match(first_line)
                cp = self.CAPS_RE.match(first_line)

                if ch:
                    current_chapter = ch.group(1).strip()[:120]
                    current_section = "Introduction"
                elif sc:
                    current_section = sc.group(1).strip()[:120]
                elif cp and len(first_line) < 80:
                    current_section = first_line.strip()[:120]

                docs.append(Document(
                    page_content=paragraph,
                    metadata={
                        "book_name": self.book_id,
                        "chapter": current_chapter,
                        "section": current_section,
                        "page_number": page_num + 1,
                        "paragraph_id": para_num,
                    }
                ))
        return docs

# -- Embedding Engine ----------------------------------------------------------
def embed_batch(texts: List[str]) -> List[List[float]]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = genai.embed_content(
                model=EMBED_MODEL,
                content=texts,
                task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            err = str(e)
            print(f"  [EMBED ERROR] Attempt {attempt}/{MAX_RETRIES}: {err[:200]}")
            if "429" in err or "quota" in err.lower():
                wait = min(2 ** attempt * 5, 120)
                print(f"  [QUOTA] Waiting {wait}s...")
                time.sleep(wait)
            else:
                if attempt == MAX_RETRIES: raise
                time.sleep(2 ** attempt)
    raise RuntimeError("Embedding failed after retries.")

# -- Ingestion Pipeline --------------------------------------------------------
def run_ingestion(pdf_path: str, book_id: str, namespace: str, fresh: bool = False):
    print(f"\n{'=' * 70}")
    print(f"  Book:      {book_id}")
    print(f"  Namespace: {namespace}")
    print(f"  Model:     {EMBED_MODEL}")
    print(f"{'=' * 70}")

    if not os.path.exists(pdf_path):
        print(f"  [SKIP] Not found: {pdf_path}")
        return False

    docs = HierarchicalMedicalParser(pdf_path, book_id).parse()
    if not docs: return False

    if fresh: _clear_checkpoint(namespace)
    resume_idx = _load_checkpoint(namespace)

    remaining = docs[resume_idx:]
    total_chunks = len(docs)
    if not remaining:
        print(f"  [DONE] Already fully ingested.")
        return True

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)

    total_uploaded = resume_idx
    t_start = time.time()

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        texts = [doc.page_content for doc in batch]
        abs_start = resume_idx + i

        embeddings = embed_batch(texts)
        
        vectors = []
        for j, (doc, emb) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id": f"{namespace}_{abs_start + j}",
                "values": emb,
                "metadata": {**doc.metadata, "text": doc.page_content[:1500]}
            })

        for ui in range(0, len(vectors), UPSERT_SIZE):
            index.upsert(vectors=vectors[ui : ui + UPSERT_SIZE], namespace=namespace)

        total_uploaded += len(batch)
        pct = (total_uploaded / total_chunks) * 100
        rate = total_uploaded / max(time.time() - t_start, 1)
        
        bar = "#" * int(30 * total_uploaded / total_chunks) + "-" * (30 - int(30 * total_uploaded / total_chunks))
        print(f"  [{bar}] {pct:5.1f}% | {total_uploaded:,}/{total_chunks:,} chunks | {rate:.1f} c/s")
        
        _save_checkpoint(namespace, total_uploaded)
        time.sleep(THROTTLE_SEC)

    print(f"\n  [SUCCESS] '{book_id}' complete!")
    _clear_checkpoint(namespace)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()

    print("\n+====================================================================+")
    print("|     Medico AI -- Textbook Ingestion Engine (Gemini Paid)         |")
    print("+====================================================================+")
    print(f"|  Model:  {EMBED_MODEL:<58}|")
    print(f"|  Index:  {INDEX_NAME:<58}|")
    print("+====================================================================+\n")

    books = ALL_BOOKS if args.all else []
    if not books:
        print("Usage: python scripts/ingest_gemini.py --all")
        return

    for path, bid, ns in books:
        run_ingestion(path, bid, ns, args.fresh)

if __name__ == "__main__":
    main()
