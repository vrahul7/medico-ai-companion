from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.services.llm_provider import get_provider_info

from .api.routes import research, pdf_analyzer

# Load environment variables
load_dotenv(override=True)

app = FastAPI(
    title="Medico Feeds Backend API",
    description="Dedicated guidelines and research summaries backend powered by Google Gemini 1.5/2.5 & Firestore.",
    version="2.0.0"
)

# Enable CORS for local testing (Vite dev server and Android proxying)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open to mobile client network configurations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Medico Feeds Backend API!", "version": "2.0.0"}

@app.get("/api/health")
def health_check():
    """Returns current LLM status for diagnostics."""
    return {
        "status": "ok",
        "backend": "Medico Feeds",
        **get_provider_info()
    }

app.include_router(research.router,  prefix="/api",            tags=["research"])
app.include_router(pdf_analyzer.router, prefix="/api",         tags=["research"])
