from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.services.llm_provider import get_provider_info

from .api.routes import chat, research, whatsapp, pdf_analyzer

# Load environment variables (API keys)
load_dotenv(override=True)

app = FastAPI(
    title="Medico AI Companion API",
    description="Backend for the Hybrid RAG AI Medical Chat. Provider: OpenAI (primary) → Gemini (fallback).",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Medico AI Companion Backend API!", "version": "1.1.0"}

@app.get("/api/health")
def health_check():
    """Returns current LLM provider status for observability and debugging."""
    return {
        "status": "ok",
        "backend": "Medico AI Companion",
        **get_provider_info()
    }

app.include_router(chat.router,      prefix="/api",            tags=["chat"])
app.include_router(research.router,  prefix="/api",            tags=["research"])
app.include_router(pdf_analyzer.router, prefix="/api",         tags=["research"])
app.include_router(whatsapp.router,  prefix="/api/whatsapp",   tags=["whatsapp"])
