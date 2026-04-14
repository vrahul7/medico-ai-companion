import os
import time
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# Load environment variables
load_dotenv()

pinecone_key = os.getenv("PINECONE_API_KEY")
index_name = "medico-ai-companion"

print("Starting Data Ingestion Pipeline...")

# 1. Initialize Pinecone
pc = Pinecone(api_key=pinecone_key)

# Check if index exists, create if not
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
if index_name not in existing_indexes:
    print(f"Creating new Pinecone index: '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=768, # Google text-embedding-004 dimension
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1") 
    )
    # Wait for index to be ready
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)
    print("Index created successfully!")
else:
    print(f"Index '{index_name}' already exists.")

# 2. Embeddings setup
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001") 

# 3. Load PDFs
data_dir = Path(__file__).resolve().parent.parent / "data" / "documents"
pdf_files = list(data_dir.glob("*.pdf"))

if not pdf_files:
    print(f"No PDFs found in {data_dir.absolute()}")
    exit(1)

print(f"Found {len(pdf_files)} PDF(s) to process.")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
vector_store = PineconeVectorStore(index=pc.Index(index_name), embedding=embeddings)

# Process each PDF
for pdf_path in pdf_files:
    print(f"\nProcessing: {pdf_path.name}")
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()
    print(f"  Extracted {len(docs)} pages.")
    
    # Split
    chunks = splitter.split_documents(docs)
    print(f"  Split into {len(chunks)} chunks.")
    
    batch_size = 100
    
    log_file = data_dir.parent / "ingestion_progress.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Started processing {pdf_path.name}. Found {len(chunks)} chunks.\n")
        
    for i in tqdm(range(0, len(chunks), batch_size), desc="  Uploading batches"):
        batch = chunks[i:i+batch_size]
        for doc in batch:
            doc.metadata["type"] = "offline_book"
            doc.metadata["title"] = pdf_path.name
        
        vector_store.add_documents(batch)
        
        # Append progress every batch
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {pdf_path.name}: Uploaded {i + len(batch)} / {len(chunks)} chunks.\n")

print("\nIngestion Complete! The offline textbook data is now searchable in Pinecone.")
with open(data_dir.parent / "ingestion_progress.txt", "a", encoding="utf-8") as f:
    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] INGESTION FULLY COMPLETED!\n")
