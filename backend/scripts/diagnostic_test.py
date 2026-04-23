import os
import sys
from dotenv import load_dotenv

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(override=True)

from app.services.rag import HybridRAGEngine
from app.services.whatsapp_bot import whatsapp_bot

def test_rag():
    import sys
    import io
    # Ensure UTF-8 output for Windows
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("\n--- Diagnostic: RAG Synthesis Test ---")
    engine = HybridRAGEngine()
    query = "What is the management of acute bronchiolitis?"
    
    try:
        print(f"Synthesizing for: '{query}'...")
        result = engine.synthesize(query)
        print("\n[RAG RESULT KEYS]:", result.keys())
        print("\n[RAG ANSWER]:\n", result.get("answer"))
        print("\n[RAG CITATIONS]:", len(result.get("sources", [])))
        
        print("\n--- Diagnostic: WhatsApp Formatting Test ---")
        reply = whatsapp_bot.process(from_number="whatsapp:+917200071296", body=query)
        print("\n[WHATSAPP REPLY]:\n", reply)
        
    except Exception as e:
        print(f"\n[ERROR] Diagnostic failed: {e}")

if __name__ == "__main__":
    test_rag()
