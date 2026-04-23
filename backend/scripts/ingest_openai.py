"""
ingest_openai.py — Medical Textbook Ingestion (OpenAI text-embedding-3-large)
===============================================================================
Ingests all configured medical PDFs into Pinecone using OpenAI embeddings.

Key features:
  • Hierarchical parsing: Chapter > Section > Paragraph metadata
  • Checkpoint/resume: crash-safe, picks up exactly where it left off
  • Batch embedding: up to 2048 texts per API call (OpenAI limit)
  • Zero throttle needed: OpenAI Tier 1 allows 3,000 req/min
  • Progress bar with ETA and chunk rate
  • Automatic namespace-per-book for granular search control

Usage:
    # Ingest all books (recommended)
    python scripts/ingest_openai.py --all

    # Ingest a single book
    python scripts/ingest_openai.py --file data/documents/Nelson_Vol1.pdf --book Nelson_Vol1

    # Force fresh restart (clears checkpoints for all books)
    python scripts/ingest_openai.py --all --fresh

Pinecone namespace naming:
    Nelson Vol1  → nelson_vol1_semantic
    Nelson Vol2  → nelson_vol2_semantic
    PiyushGupta Vol1 → piyushgupta_vol1_semantic
    PiyushGupta Vol2 → piyushgupta_vol2_semantic
    PiyushGupta Vol3 → piyushgupta_vol3_semantic
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

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    from openai import OpenAI
except ImportError:
    print("[FATAL] openai package not installed. Run: pip install openai>=1.30.0")
    sys.exit(1)

try:
    from pinecone import Pinecone
except ImportError:
    print("[FATAL] pinecone-client not installed. Run: pip install pinecone-client")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL    = "text-embedding-3-large"   # 3072-dim, OpenAI SOTA
EMBED_DIM      = 3072
BATCH_SIZE     = 50      # texts per embedding call — reduced for free-tier TPM limits
UPSERT_SIZE    = 100     # vectors per Pinecone upsert (Pinecone max)
MIN_PARA_LEN   = 80      # skip noise paragraphs shorter than this
MAX_RETRIES    = 6       # retries on API errors
THROTTLE_SEC   = 1.0    # sleep between embedding calls (free tier: ~150k TPM)

# ── Env validation ────────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
INDEX_NAME       = os.getenv("PINECONE_INDEX", "medico-ai-companion")

if not OPENAI_API_KEY.startswith("sk-"):
    print("[FATAL] OPENAI_API_KEY not set or invalid in .env")
    sys.exit(1)
if not PINECONE_API_KEY:
    print("[FATAL] PINECONE_API_KEY not set in .env")
    sys.exit(1)
if not INDEX_NAME:
    print("[FATAL] PINECONE_INDEX not set in .env")
    sys.exit(1)

# ── Book registry — all 5 textbooks ──────────────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPTS_DIR, "..", "data", "documents")

ALL_BOOKS: List[Tuple[str, str, str]] = [
    # (pdf_path, book_id, pinecone_namespace)
    (
        os.path.join(DATA_DIR, "Nelson Textbook of Pediatrics  Volume 1   22ed  2024.pdf"),
        "Nelson_Vol1",
        "nelson_vol1_semantic",
    ),
    (
        os.path.join(DATA_DIR, "Nelson Textbook of Pediatrics  Volume 2 22ed  2024.pdf"),
        "Nelson_Vol2",
        "nelson_vol2_semantic",
    ),
    (
        os.path.join(DATA_DIR, "Piyush Gupta PG textbook of Pediatrics Vol1.pdf"),
        "PiyushGupta_Vol1",
        "piyushgupta_vol1_semantic",
    ),
    (
        os.path.join(DATA_DIR, "Piyush Gupta PG Textbook of Pediatrics Vol 2_compressed.pdf"),
        "PiyushGupta_Vol2",
        "piyushgupta_vol2_semantic",
    ),
    (
        os.path.join(DATA_DIR, "Piyush Gupta PG Textbook of Pediatrics Vol 3_compressed.pdf"),
        "PiyushGupta_Vol3",
        "piyushgupta_vol3_semantic",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
def _ckpt_path(namespace: str) -> str:
    return os.path.join(SCRIPTS_DIR, f".ckpt_{namespace}_openai.json")

def _load_checkpoint(namespace: str) -> int:
    path = _ckpt_path(namespace)
    if os.path.exists(path):
        try:
            data = json.loads(open(path).read())
            idx = data.get("last_uploaded_idx", 0)
            ts  = data.get("ts", 0)
            age = round((time.time() - ts) / 3600, 1)
            print(f"  [RESUME] Checkpoint found — resuming from chunk {idx} (saved {age}h ago)")
            return idx
        except Exception:
            pass
    return 0

def _save_checkpoint(namespace: str, idx: int):
    with open(_ckpt_path(namespace), "w") as f:
        json.dump({"last_uploaded_idx": idx, "ts": time.time()}, f)

def _clear_checkpoint(namespace: str):
    path = _ckpt_path(namespace)
    if os.path.exists(path):
        os.remove(path)
        print(f"  [CKPT] Checkpoint cleared for '{namespace}'")


# ══════════════════════════════════════════════════════════════════════════════
# PDF PARSER — Hierarchical Medical Parser
# ══════════════════════════════════════════════════════════════════════════════
class HierarchicalMedicalParser:
    """
    Extracts text from dense medical PDFs with rich hierarchical metadata.
    Chapter > Section > Paragraph structure enables precision citation mapping.
    """

    CHAPTER_RE = re.compile(
        r"^(?:CHAPTER|PART|UNIT|SECTION)\s+[\dIVXLC]+[\s:\.\-]+(.*)", re.IGNORECASE
    )
    SECTION_RE = re.compile(r"^(?:\d+[\.\-]\d+(?:[\.\-]\d+)?)\s+(.*)")
    CAPS_RE    = re.compile(r"^([A-Z][A-Z\s]{4,60})$")

    def __init__(self, file_path: str, book_id: str):
        self.file_path = file_path
        self.book_id   = book_id

    def parse(self) -> List[Document]:
        print(f"\n  [PARSE] Opening: {os.path.basename(self.file_path)}")
        try:
            reader = PdfReader(self.file_path)
        except Exception as e:
            print(f"  [ERROR] Cannot open PDF: {e}")
            return []

        total_pages = len(reader.pages)
        print(f"  [PARSE] Pages: {total_pages}")

        docs: List[Document] = []
        current_chapter = "Preface"
        current_section = "Introduction"

        for page_num, page in enumerate(reader.pages):
            if page_num % 200 == 0:
                pct = round((page_num / total_pages) * 100)
                print(f"  [PARSE] Page {page_num}/{total_pages} ({pct}%)")

            text = page.extract_text()
            if not text:
                continue

            for para_num, paragraph in enumerate(text.split("\n\n")):
                paragraph = paragraph.strip()
                if len(paragraph) < MIN_PARA_LEN:
                    continue

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

                # Create a stable content hash for deduplication
                content_hash = hashlib.md5(paragraph.encode()).hexdigest()[:8]

                docs.append(Document(
                    page_content=paragraph,
                    metadata={
                        "book_name":    self.book_id,
                        "chapter":      current_chapter,
                        "section":      current_section,
                        "page_number":  page_num + 1,
                        "paragraph_id": para_num,
                        "content_hash": content_hash,
                    }
                ))

        print(f"  [PARSE] Extracted {len(docs):,} chunks from {total_pages:,} pages")
        return docs


# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDING ENGINE — OpenAI text-embedding-3-large
# ══════════════════════════════════════════════════════════════════════════════
def embed_batch(client: OpenAI, texts: List[str]) -> List[List[float]]:
    """
    Embeds a batch of texts using OpenAI text-embedding-3-large.
    Retries on transient errors with exponential backoff.
    Free tier: ~150k TPM. THROTTLE_SEC added between calls.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(
                model=EMBED_MODEL,
                input=texts,
                encoding_format="float",
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            err = str(e)
            print(f"  [EMBED ERROR] Attempt {attempt}/{MAX_RETRIES}: {err[:200]}")
            if "rate_limit" in err.lower() or "429" in err:
                wait = min(2 ** attempt * 5, 120)  # 10s, 20s, 40s, 80s, 120s, 120s
                print(f"  [RATE LIMIT] Waiting {wait}s...")
                time.sleep(wait)
            elif "quota" in err.lower() or "insufficient" in err.lower() or "billing" in err.lower():
                print(f"  [QUOTA/BILLING] Account issue: {err[:300]}")
                print("  [ACTION] Check your OpenAI billing at https://platform.openai.com/usage")
                raise
            else:
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries.")


# ══════════════════════════════════════════════════════════════════════════════
# INGESTION PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
# ==============================================================================
def run_ingestion(pdf_path: str, book_id: str, namespace: str, fresh: bool = False):
    """
    Full pipeline: Parse PDF → Embed chunks → Upsert to Pinecone.
    Checkpoint-safe: resumes from last successful upload if interrupted.
    """
    print(f"\n{'=' * 70}")
    print(f"  Book:      {book_id}")
    print(f"  File:      {os.path.basename(pdf_path)}")
    print(f"  Namespace: {namespace}")
    print(f"  Model:     {EMBED_MODEL} ({EMBED_DIM} dims)")
    print(f"  Index:     {INDEX_NAME}")
    print(f"{'=' * 70}")

    if not os.path.exists(pdf_path):
        print(f"  [SKIP] File not found: {pdf_path}")
        return False

    # -- Parse -----------------------------------------------------------------
    parser = HierarchicalMedicalParser(file_path=pdf_path, book_id=book_id)
    docs   = parser.parse()

    if not docs:
        print(f"  [ERROR] No content parsed from {book_id}. Skipping.")
        return False

    # -- Fresh mode: clear checkpoint ------------------------------------------
    if fresh:
        _clear_checkpoint(namespace)

    # -- Resume from checkpoint ------------------------------------------------
    resume_idx = _load_checkpoint(namespace)
    if resume_idx >= len(docs):
        print(f"  [DONE] '{book_id}' is already fully ingested ({len(docs):,} chunks).")
        _clear_checkpoint(namespace)
        return True

    remaining     = docs[resume_idx:]
    total_chunks  = len(docs)
    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"\n  Total chunks: {total_chunks:,}  |  Remaining: {len(remaining):,}  |  Batches: {total_batches:,}")
    print(f"  Batch (embed): {BATCH_SIZE}  |  Batch (upsert): {UPSERT_SIZE}")

    # -- Init clients ----------------------------------------------------------
    oai_client = OpenAI(api_key=OPENAI_API_KEY)
    pc         = Pinecone(api_key=PINECONE_API_KEY)
    index      = pc.Index(INDEX_NAME)

    total_uploaded = resume_idx
    t_start        = time.time()

    for batch_num, i in enumerate(range(0, len(remaining), BATCH_SIZE), start=1):
        batch     = remaining[i : i + BATCH_SIZE]
        texts     = [doc.page_content for doc in batch]
        abs_start = resume_idx + i   # Absolute position for stable vector IDs

        # -- Embed --------------------------------------------------------------
        try:
            embeddings = embed_batch(oai_client, texts)
        except Exception as e:
            print(f"\n  [FATAL] Embedding failed: {e}")
            print(f"  [INFO]  Checkpoint saved at chunk {total_uploaded}. Re-run to resume.")
            _save_checkpoint(namespace, total_uploaded)
            return False

        # -- Build Pinecone vectors ---------------------------------------------
        vectors = []
        for j, (doc, emb) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id": f"{namespace}_{abs_start + j}",
                "values": emb,
                "metadata": {
                    **doc.metadata,
                    "text": doc.page_content[:1500],   # Pinecone metadata cap
                }
            })

        # -- Upsert in sub-batches ----------------------------------------------
        for ui in range(0, len(vectors), UPSERT_SIZE):
            sub = vectors[ui : ui + UPSERT_SIZE]
            try:
                index.upsert(vectors=sub, namespace=namespace)
            except Exception as e:
                print(f"\n  [ERROR] Pinecone upsert failed: {e}")
                _save_checkpoint(namespace, total_uploaded)
                return False

        total_uploaded += len(batch)
        elapsed          = time.time() - t_start
        pct              = (total_uploaded / total_chunks) * 100
        rate             = total_uploaded / max(elapsed, 1)
        remaining_chunks = total_chunks - total_uploaded
        eta_sec          = int(remaining_chunks / max(rate, 0.001))
        eta_min          = eta_sec // 60
        eta_sec_rem      = eta_sec % 60

        # Progress bar
        bar_len  = 30
        filled   = int(bar_len * total_uploaded / total_chunks)
        bar      = "#" * filled + "-" * (bar_len - filled)

        print(
            f"  [{bar}] {pct:5.1f}% | "
            f"Batch {batch_num}/{total_batches} | "
            f"{total_uploaded:,}/{total_chunks:,} chunks | "
            f"{rate:.0f} c/s | ETA: {eta_min}m {eta_sec_rem:02d}s"
        )

        # -- Save checkpoint after every batch ---------------------------------
        _save_checkpoint(namespace, total_uploaded)

        # -- Throttle (free tier) ----------------------------------------------
        time.sleep(THROTTLE_SEC)

    # -- Success ---------------------------------------------------------------
    elapsed_total = round((time.time() - t_start) / 60, 1)
    print(f"\n  [SUCCESS] '{book_id}' complete! {total_uploaded:,} chunks in {elapsed_total} min.")
    _clear_checkpoint(namespace)
    return True


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Medico AI — OpenAI Textbook Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ingest_openai.py --all
  python scripts/ingest_openai.py --all --fresh
  python scripts/ingest_openai.py --file data/documents/Nelson_Vol1.pdf --book Nelson_Vol1 --namespace nelson_vol1_semantic
        """
    )
    ap.add_argument("--all",       action="store_true", help="Ingest all 5 books in sequence")
    ap.add_argument("--file",      help="Path to a single PDF file")
    ap.add_argument("--book",      help="Book identifier (used in metadata)")
    ap.add_argument("--namespace", help="Pinecone namespace override (default: derived from --book)")
    ap.add_argument("--fresh",     action="store_true", help="Clear checkpoints and re-ingest from scratch")
    args = ap.parse_args()

    if not args.all and not args.file:
        ap.print_help()
        sys.exit(1)

    print()
    print("+" + "=" * 68 + "+")
    print("| Medico AI -- Textbook Ingestion Engine (OpenAI Embeddings)       |")
    print("+" + "=" * 68 + "+")
    print(f"|  Model:  {EMBED_MODEL:<59}|")
    print(f"|  Dims:   {EMBED_DIM:<59}|")
    print(f"|  Index:  {INDEX_NAME:<59}|")
    print("+" + "=" * 68 + "+")
    print()

    books_to_run = []

    if args.all:
        books_to_run = ALL_BOOKS
        print(f"[INFO] Ingesting all {len(ALL_BOOKS)} books...")
        for path, book_id, ns in ALL_BOOKS:
            exists = "OK" if os.path.exists(path) else "MISSING"
            print(f"  {exists}  {book_id}  ->  {ns}")
        print()
    else:
        if not args.file or not args.book:
            print("[FATAL] --file and --book are both required when not using --all")
            sys.exit(1)
        ns = args.namespace or (args.book.lower().replace(" ", "_") + "_semantic")
        books_to_run = [(args.file, args.book, ns)]

    # -- Verify index dimension -------------------------------------------------
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        print(f"[FATAL] Pinecone index '{INDEX_NAME}' does not exist.")
        print(f"        Run first: python scripts/recreate_index_openai.py")
        sys.exit(1)

    info = pc.describe_index(INDEX_NAME)
    dim  = info.dimension
    if dim != EMBED_DIM:
        print(f"[FATAL] Index dimension mismatch: index={dim}, expected={EMBED_DIM}")
        print(f"        Run: python scripts/recreate_index_openai.py")
        sys.exit(1)

    print(f"[OK] Pinecone index '{INDEX_NAME}' verified at {dim} dims.\n")

    # -- Run ingestion for each book --------------------------------------------
    grand_start   = time.time()
    success_count = 0
    fail_count    = 0

    for idx, (pdf_path, book_id, namespace) in enumerate(books_to_run, 1):
        print(f"\n[{idx}/{len(books_to_run)}] Processing: {book_id}")
        ok = run_ingestion(
            pdf_path=pdf_path,
            book_id=book_id,
            namespace=namespace,
            fresh=args.fresh,
        )
        if ok:
            success_count += 1
        else:
            fail_count += 1
            print(f"  [WARNING] '{book_id}' failed or was skipped.")

    # -- Final summary ---------------------------------------------------------
    grand_elapsed = round((time.time() - grand_start) / 60, 1)
    print()
    print("+" + "=" * 68 + "+")
    print("|                    INGESTION COMPLETE                           |")
    print("+" + "=" * 68 + "+")
    print(f"|  Successful:  {success_count:<53}|")
    print(f"|  Failed:      {fail_count:<53}|")
    print(f"|  Total time:  {grand_elapsed} min{'':<49}|")
    print("+" + "=" * 68 + "+")
    print()

    if fail_count > 0:
        print("[WARNING] Some books failed. Re-run the same command to resume from checkpoints.")
        sys.exit(1)
    else:
        print("[SUCCESS] All books ingested! The RAG engine is ready.")


if __name__ == "__main__":
    main()
