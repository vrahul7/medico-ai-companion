from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api.routes import chat, ddx, research, whatsapp

# Load environment variables (API keys)
load_dotenv(override=True)

app = FastAPI(
    title="Medico AI Companion API",
    description="Backend for the Hybrid RAG AI Medical Chat.",
    version="1.0.0"
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
    return {"message": "Welcome to the Medico AI Companion Backend API!"}

app.include_router(chat.router,      prefix="/api",            tags=["chat"])
app.include_router(ddx.router,       prefix="/api/ddx",        tags=["ddx"])
app.include_router(research.router,  prefix="/api",            tags=["research"])
app.include_router(whatsapp.router,  prefix="/api/whatsapp",   tags=["whatsapp"])

