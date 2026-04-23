import os
import sys
import time
import json
import hashlib
from typing import List, Dict
from pypdf import PdfReader
from dotenv import load_dotenv
import google.generativeai as genai
from pinecone import Pinecone

# Load environment variables
load_dotenv(override=True)

# Configuration
EMBED_MODEL = "models/gemini-embedding-001" 
FLASH_MODEL = "gemini-flash-latest"
BLOCK_SIZE_PAGES = 10
MAX_RETRIES = 5

# Configure Gemini
print("DEBUG: Configuring Gemini API...")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel(FLASH_MODEL)
print(f"DEBUG: Using model: {FLASH_MODEL}")

class GeminiSemanticIngestor:
    def __init__(self, file_path: str, book_name: str):
        print(f"DEBUG: Initializing ingestor for {book_name}...")
        self.file_path = file_path
        self.book_name = book_name
        self.namespace = book_name.lower().replace(" ", "_").replace("'", "")
        print("DEBUG: Initializing Pinecone...")
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index(os.getenv("PINECONE_INDEX"))
        self.ckpt_path = f".ckpt_semantic_{self.namespace}.json"
        print(f"DEBUG: Checkpoint path: {self.ckpt_path}")

    def _load_checkpoint(self):
        if os.path.exists(self.ckpt_path):
            with open(self.ckpt_path, "r") as f:
                return json.load(f).get("last_page", 0)
        return 0

    def _save_checkpoint(self, last_page: int):
        with open(self.ckpt_path, "w") as f:
            json.dump({"last_page": last_page, "ts": time.time()}, f)

    def extract_semantic_chunks(self, text_block: str) -> List[Dict]:
        """Ask Gemini Flash to segment the text block into semantic clinical units."""
        prompt = f"""
        Segment this medical text block into distinct, logically complete clinical units.
        
        Rules:
        1. Do NOT split dosage recommendations, diagnostic steps, or list items.
        2. Assign a concise 'title' to each chunk.
        3. Identify the 'chapter' and 'section' if mentioned in context.
        4. Extract 3-5 'keywords' for medical search.
        5. Output ONLY a raw JSON array of objects. No markdown formatting.
        
        Object Schema:
        {{
            "title": "...",
            "text": "...",
            "chapter": "...",
            "section": "...",
            "keywords": ["...", "..."]
        }}
        
        Text Block from '{self.book_name}':
        {text_block}
        """
        
        for attempt in range(MAX_RETRIES):
            try:
                # Use generation_config for stable JSON-like output
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                    )
                )
                
                # Clean Markdown if LLM included it
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_text)
            except Exception as e:
                print(f"  [RETRY] Flash analysis failed (Attempt {attempt+1}/{MAX_RETRIES}): {e}")
                time.sleep(5 * (attempt + 1))
        return []

    def process(self):
        print(f"\n[START] Semantic Ingestion: {self.book_name}")
        reader = PdfReader(self.file_path)
        total_pages = len(reader.pages)
        start_page = self._load_checkpoint()
        
        print(f"[INFO] Processing {total_pages} pages starting from page {start_page}")

        for i in range(start_page, total_pages, BLOCK_SIZE_PAGES):
            end_page = min(i + BLOCK_SIZE_PAGES, total_pages)
            print(f"\n[BLOCK] Pages {i+1} to {end_page}...")
            
            # 1. Extract raw text
            block_text = ""
            for p in range(i, end_page):
                text = reader.pages[p].extract_text() or ""
                block_text += f"\n--- PAGE {p+1} ---\n{text}"

            if len(block_text.strip()) < 100:
                print("  [SKIP] Block too short or empty.")
                self._save_checkpoint(end_page)
                continue

            # 2. Semantic Chunking with Flash
            chunks = self.extract_semantic_chunks(block_text)
            if not chunks:
                print("  [ERROR] No chunks extracted by Flash.")
                continue
            
            print(f"  [OK] Extracted {len(chunks)} semantic segments.")

            # 3. Embed & Upsert
            vector_batch = []
            texts_to_embed = [c['text'] for c in chunks]
            
            try:
                # Use standard embedding method
                embed_res = genai.embed_content(
                    model=EMBED_MODEL,
                    content=texts_to_embed,
                    task_type="retrieval_document"
                )
                # Handle both 'embedding' and 'embeddings' keys
                embeddings = embed_res.get('embedding') or embed_res.get('embeddings')
                
                if not embeddings:
                    raise KeyError(f"Neither 'embedding' nor 'embeddings' found in response keys: {list(embed_res.keys())}")
                
                for j, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    vec_id = f"sem_{self.namespace}_{i}_{j}"
                    vector_batch.append({
                        "id": vec_id,
                        "values": emb,
                        "metadata": {
                            "text": chunk['text'][:1000],
                            "title": chunk.get('title', ''),
                            "book_name": self.book_name,
                            "chapter": chunk.get('chapter', ''),
                            "section": chunk.get('section', ''),
                            "keywords": ",".join(chunk.get('keywords', [])),
                            "source_pages": f"{i+1}-{end_page}",
                            "type": "offline_book_semantic"
                        }
                    })
                
                self.index.upsert(vectors=vector_batch, namespace=self.namespace)
                print(f"  [DONE] Upserted {len(vector_batch)} vectors.")
                self._save_checkpoint(end_page)
                
            except Exception as e:
                print(f"  [FATAL] Processing failed at page {i}: {e}")
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--book", required=True)
    args = parser.parse_args()
    
    ingestor = GeminiSemanticIngestor(args.file, args.book)
    ingestor.process()
