import os
import re
import sys
import time
import hashlib
import json
from typing import List
from pypdf import PdfReader
from langchain.docstore.document import Document
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone

# Force reload from .env — avoids stale process cache issues
load_dotenv(override=True)

# ── Startup Validation Guard ───────────────────────────────────────────────
_INDEX_NAME = os.getenv("PINECONE_INDEX")
if not _INDEX_NAME:
    print("[FATAL] PINECONE_INDEX is not set in your .env file.")
    print("[FATAL] Add: PINECONE_INDEX=medico-ai-companion")
    sys.exit(1)
print(f"[OK] Pinecone index resolved: '{_INDEX_NAME}'")

# ── Tunable Performance Config ─────────────────────────────────────────────
EMBED_MODEL  = "models/gemini-embedding-001"
BATCH_SIZE   = 100    # Maximise chunks per request (100 is max allowed) to avoid 1500 req/day limit
UPSERT_SIZE  = 100    # Pinecone upsert batch (max 100 vectors per call)
THROTTLE_SEC = 4.5    # Gemini free tier limit is 15 req/min (1 req every 4s)
MAX_RETRIES  = 6      # Exponential backoff retries on 429
MIN_PARA_LEN = 80     # Skip noise paragraphs shorter than this

# ── Checkpoint helpers ─────────────────────────────────────────────────────
def _checkpoint_path(namespace: str) -> str:
    return os.path.join(os.path.dirname(__file__), f".ckpt_{namespace}.json")

def _load_checkpoint(namespace: str) -> int:
    """Returns the last successfully uploaded chunk index (0 if fresh start)."""
    path = _checkpoint_path(namespace)
    if os.path.exists(path):
        try:
            data = json.loads(open(path).read())
            idx = data.get("last_uploaded_idx", 0)
            print(f"[RESUME] Checkpoint found — resuming from chunk {idx} for '{namespace}'")
            return idx
        except Exception:
            pass
    return 0

def _save_checkpoint(namespace: str, last_uploaded_idx: int):
    path = _checkpoint_path(namespace)
    with open(path, "w") as f:
        json.dump({"last_uploaded_idx": last_uploaded_idx, "ts": time.time()}, f)

def _clear_checkpoint(namespace: str):
    path = _checkpoint_path(namespace)
    if os.path.exists(path):
        os.remove(path)


class HierarchicalMedicalParser:
    """
    Parses dense medical PDFs and extracts text with hierarchical metadata:
    Chapter > Section > Paragraph    (required for the Source-Preview and Citation moats)
    """
    def __init__(self, file_path: str, book_name: str):
        self.file_path = file_path
        self.book_name = book_name

    def parse(self) -> List[Document]:
        print(f"[PARSE] Reading PDF: {os.path.basename(self.file_path)}...")
        try:
            reader = PdfReader(self.file_path)
        except Exception as e:
            print(f"[ERROR] Could not open PDF: {e}")
            return []

        total_pages = len(reader.pages)
        print(f"[PARSE] Total pages: {total_pages}")

        documents = []
        current_chapter = "Unknown Chapter"
        current_section = "Unknown Section"

        # Broader regex patterns to catch more textbook formats
        chapter_pattern = re.compile(
            r"^(?:CHAPTER|PART|UNIT|SECTION)\s+[\dIVXLC]+[\s:\.\-]+(.*)", re.IGNORECASE
        )
        section_pattern = re.compile(
            r"^(?:\d+[\.\-]\d+(?:[\.\-]\d+)?)\s+(.*)"  # 1.2, 3.4.1, etc.
        )
        alt_section_pattern = re.compile(
            r"^([A-Z][A-Z\s]{4,60})$"  # ALL CAPS section headers (common in textbooks)
        )

        for page_num, page in enumerate(reader.pages):
            if page_num % 100 == 0:
                pct = round((page_num / total_pages) * 100)
                print(f"  [PARSE] Page {page_num}/{total_pages} ({pct}%)...")

            text = page.extract_text()
            if not text:
                continue

            paragraphs = text.split("\n\n")
            for para_num, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                if len(paragraph) < MIN_PARA_LEN:
                    continue

                lines = paragraph.split("\n")
                first_line = lines[0].strip()

                ch_match  = chapter_pattern.match(first_line)
                sec_match = section_pattern.match(first_line)
                alt_match = alt_section_pattern.match(first_line)

                if ch_match:
                    current_chapter = ch_match.group(1).strip()[:120]
                    current_section = "Introduction"
                elif sec_match:
                    current_section = sec_match.group(1).strip()[:120]
                elif alt_match and len(first_line) < 80:
                    current_section = first_line.strip()[:120]

                documents.append(Document(
                    page_content=paragraph,
                    metadata={
                        "book_name":    self.book_name,
                        "chapter":      current_chapter,
                        "section":      current_section,
                        "page_number":  page_num + 1,
                        "paragraph_id": para_num,
                    }
                ))

        print(f"[PARSE] Extracted {len(documents)} hierarchical chunks from {total_pages} pages.")
        return documents


def _embed_batch(client: genai.Client, texts: List[str]) -> List[List[float]]:
    """Calls Gemini embed_content with exponential backoff on 429."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return [e.values for e in response.embeddings]
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = (2 ** attempt) * 5   # 10s, 20s, 40s, 80s, 160s, 320s
                print(f"  [QUOTA] Rate-limited. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                print(f"  [ERROR] Embedding error: {e}")
                raise
    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries.")


def run_ingestion(pdf_path: str, book_name: str):
    if not os.path.exists(pdf_path):
        print(f"[FATAL] File not found: {pdf_path}")
        sys.exit(1)

    # ── Parse ──────────────────────────────────────────────────────────────
    parser = HierarchicalMedicalParser(file_path=pdf_path, book_name=book_name)
    docs = parser.parse()

    if not docs:
        print("[FATAL] No documents parsed. Check the PDF is readable.")
        sys.exit(1)

    namespace = book_name.lower().replace(" ", "_").replace("'", "")

    # ── Resume from checkpoint ─────────────────────────────────────────────
    resume_idx = _load_checkpoint(namespace)
    if resume_idx >= len(docs):
        print(f"[OK] '{book_name}' is already fully ingested ({len(docs)} chunks). Skipping.")
        _clear_checkpoint(namespace)
        return

    remaining = docs[resume_idx:]
    total_uploaded = resume_idx

    print(f"\n{'='*70}")
    print(f"  Book:      {book_name}")
    print(f"  Namespace: {namespace}")
    print(f"  Total chunks: {len(docs)}  |  To upload: {len(remaining)}")
    print(f"  Batch size (embed): {BATCH_SIZE}  |  Batch size (upsert): {UPSERT_SIZE}")
    print(f"  Index: {_INDEX_NAME}")
    print(f"{'='*70}\n")

    # ── Init API clients ───────────────────────────────────────────────────
    genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(_INDEX_NAME)

    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    t_start = time.time()

    for batch_num, i in enumerate(range(0, len(remaining), BATCH_SIZE), start=1):
        batch     = remaining[i:i + BATCH_SIZE]
        texts     = [doc.page_content for doc in batch]
        abs_start = resume_idx + i   # Absolute chunk index for IDs

        # ── Embed ──────────────────────────────────────────────────────────
        try:
            embeddings = _embed_batch(genai_client, texts)
        except RuntimeError as e:
            print(f"\n[FATAL] {e}")
            print(f"[INFO]  Checkpoint saved at chunk {total_uploaded}. Re-run to resume.")
            _save_checkpoint(namespace, total_uploaded)
            sys.exit(1)

        # ── Build vectors ──────────────────────────────────────────────────
        vectors = []
        for j, (doc, emb) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id":     f"{namespace}_{abs_start + j}",
                "values": emb,
                "metadata": {
                    **doc.metadata,
                    "text": doc.page_content[:1000]   # Pinecone metadata limit
                }
            })

        # ── Upsert in sub-batches of UPSERT_SIZE ──────────────────────────
        for ui in range(0, len(vectors), UPSERT_SIZE):
            sub = vectors[ui:ui + UPSERT_SIZE]
            try:
                index.upsert(vectors=sub, namespace=namespace)
            except Exception as upsert_err:
                print(f"\n  [ERROR] Pinecone upsert failed: {upsert_err}")
                _save_checkpoint(namespace, total_uploaded)
                sys.exit(1)

        total_uploaded += len(batch)
        elapsed   = time.time() - t_start
        pct       = round((total_uploaded / len(docs)) * 100, 1)
        rate      = total_uploaded / max(elapsed, 1)
        remaining_chunks = len(docs) - total_uploaded
        eta_sec   = int(remaining_chunks / max(rate, 0.001))
        eta_min   = eta_sec // 60

        print(
            f"  [{pct:5.1f}%] Batch {batch_num}/{total_batches} | "
            f"{total_uploaded}/{len(docs)} chunks | "
            f"{rate:.1f} chunks/s | ETA: {eta_min}m"
        )

        # ── Save checkpoint after every batch ─────────────────────────────
        _save_checkpoint(namespace, total_uploaded)

        # ── Throttle ───────────────────────────────────────────────────────
        time.sleep(THROTTLE_SEC)

    # ── Done ───────────────────────────────────────────────────────────────
    elapsed_total = round((time.time() - t_start) / 60, 1)
    print(f"\n[SUCCESS] '{book_name}' ingested. {total_uploaded} chunks in {elapsed_total} min.")
    _clear_checkpoint(namespace)   # Clean up checkpoint file


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Medico AI — Hierarchical Textbook Ingestion")
    ap.add_argument("--file", required=True, help="Path to the PDF file")
    ap.add_argument("--book", required=True, help="Book identifier (e.g., Nelson_Vol1)")
    args = ap.parse_args()
    run_ingestion(args.file, args.book)
