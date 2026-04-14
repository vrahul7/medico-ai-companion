import os
import re
import sys
import time
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

class HierarchicalMedicalParser:
    """
    Simulates a hierarchical structure parser for dense medical PDFs.
    Extracts text maintaining Chapter > Section > Paragraph hierarchies for the Data Flywheel moat.
    """
    def __init__(self, file_path: str, book_name: str):
        self.file_path = file_path
        self.book_name = book_name

    def parse(self) -> List[Document]:
        print(f"Reading PDF: {self.file_path}...")
        try:
            reader = PdfReader(self.file_path)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return []

        documents = []
        current_chapter = "Unknown Chapter"
        current_section = "Unknown Section"
        
        # Simple heuristic regex for chapters/sections in dense texts
        chapter_pattern = re.compile(r"^(?:CHAPTER|PART)\s+\d+[\s\:]+(.*)", re.IGNORECASE)
        section_pattern = re.compile(r"^\d+\.\d+\s+(.*)")

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
                
            paragraphs = text.split("\n\n")
            for para_num, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # Check for structural hierarchy updates
                lines = paragraph.split('\n')
                first_line = lines[0].strip()
                
                ch_match = chapter_pattern.match(first_line)
                sec_match = section_pattern.match(first_line)
                
                if ch_match:
                    current_chapter = ch_match.group(1).strip()
                    current_section = "Introduction" # Reset section
                elif sec_match:
                    current_section = sec_match.group(1).strip()
                
                if len(paragraph) > 50: # Filter noise
                    # The structural metadata required for the "Source Preview" moat
                    doc = Document(
                        page_content=paragraph,
                        metadata={
                            "book_name": self.book_name,
                            "chapter": current_chapter,
                            "section": current_section,
                            "page_number": page_num + 1,
                            "paragraph_id": para_num
                        }
                    )
                    documents.append(doc)
                    
        print(f"Extracted {len(documents)} hierarchical chunks.")
        return documents

def run_ingestion(pdf_path: str, book_name: str):
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    parser = HierarchicalMedicalParser(file_path=pdf_path, book_name=book_name)
    docs = parser.parse()

    if not docs:
        print("No documents parsed.")
        return

    # -- Embedding via new google-genai SDK (v1 endpoint, avoids v1beta issue) --
    EMBED_MODEL = "models/gemini-embedding-001"
    BATCH_SIZE = 10    # Reduced batch size to stay well under per-minute quota
    MAX_RETRIES = 5    # Max retries per batch before giving up
    namespace = book_name.lower().replace(" ", "_").replace("'", "")

    print(f"Uploading {len(docs)} chunks to Pinecone index '{_INDEX_NAME}' (namespace: '{namespace}')...")
    print(f"Embedding model: {EMBED_MODEL} | Batch size: {BATCH_SIZE}")

    genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(_INDEX_NAME)

    total_uploaded = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i + BATCH_SIZE]
        texts = [doc.page_content for doc in batch]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE

        # Exponential backoff retry for 429 quota exhaustion
        embeddings_list = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = genai_client.models.embed_content(
                    model=EMBED_MODEL,
                    contents=texts,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                )
                embeddings_list = [e.values for e in response.embeddings]
                break  # Success — exit retry loop
            except Exception as embed_err:
                err_str = str(embed_err)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_sec = (2 ** attempt) * 10  # 20s, 40s, 80s, 160s, 320s
                    print(f"  [QUOTA] Batch {batch_num}/{total_batches} rate-limited. Waiting {wait_sec}s before retry {attempt}/{MAX_RETRIES}...")
                    time.sleep(wait_sec)
                else:
                    print(f"  [ERROR] Non-quota embedding error on batch {batch_num}: {embed_err}")
                    sys.exit(1)

        if embeddings_list is None:
            print(f"  [FATAL] Batch {batch_num} failed after {MAX_RETRIES} retries. Stopping.")
            print(f"  [INFO]  {total_uploaded} chunks uploaded before failure.")
            print(f"  [INFO]  Re-run the script after a few minutes to resume from this point.")
            sys.exit(1)

        # Build Pinecone vectors with hierarchical metadata
        vectors = []
        for j, (doc, embedding) in enumerate(zip(batch, embeddings_list)):
            vec_id = f"{namespace}_{i + j}"
            vectors.append({
                "id": vec_id,
                "values": embedding,
                "metadata": {
                    **doc.metadata,
                    "text": doc.page_content[:1000]  # Pinecone metadata limit
                }
            })

        try:
            index.upsert(vectors=vectors, namespace=namespace)
            total_uploaded += len(vectors)
            progress_pct = round((total_uploaded / len(docs)) * 100, 1)
            print(f"  Progress: {total_uploaded}/{len(docs)} chunks ({progress_pct}%) — Batch {batch_num}/{total_batches}")
        except Exception as upsert_err:
            print(f"  [ERROR] Pinecone upsert failed: {upsert_err}")
            sys.exit(1)

        # Throttle: 2s between batches to respect free-tier limits
        time.sleep(2.0)

    print(f"[SUCCESS] Ingestion complete for '{book_name}'. {total_uploaded} chunks uploaded.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest Medical Textbooks Hierarchically")
    parser.add_argument("--file", type=str, required=True, help="Path to the PDF file")
    parser.add_argument("--book", type=str, required=True, help="Name of the textbook (e.g., 'Harrison Internal Medicine')")
    args = parser.parse_args()
    
    run_ingestion(args.file, args.book)
