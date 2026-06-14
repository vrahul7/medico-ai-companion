from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Dict
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.services.llm_provider import get_provider_info
from app.services.alert_scheduler import start_scheduler, stop_scheduler
from app.services.firebase_client import (
    register_device_token,
    get_alert_preferences,
    save_alert_preferences
)
from .api.routes import research, pdf_analyzer

# Load environment variables
load_dotenv(override=True)

class DeviceTokenRequest(BaseModel):
    user_id: str
    fcm_token: str

class AlertPreferencesRequest(BaseModel):
    user_id: str
    sources: Dict[str, bool]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background alert scheduler
    try:
        start_scheduler()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to start alert scheduler: {e}")
    yield
    # Stop the alert scheduler on shutdown
    try:
        stop_scheduler()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to stop alert scheduler: {e}")

app = FastAPI(
    title="Medico Feeds Backend API",
    description="Dedicated guidelines and research summaries backend powered by Google Gemini 1.5/2.5 & Firestore.",
    version="2.0.0",
    lifespan=lifespan
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

# Alert management endpoints
@app.post("/api/alerts/register-device")
async def register_device(req: DeviceTokenRequest):
    success = register_device_token(user_id=req.user_id, fcm_token=req.fcm_token)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register device token.")
    return {"status": "success", "message": "Device token registered successfully."}

@app.get("/api/alerts/preferences")
async def get_preferences(user_id: str = Query(...)):
    prefs = get_alert_preferences(user_id=user_id)
    return {"user_id": user_id, "sources": prefs}

@app.post("/api/alerts/preferences")
async def update_preferences(req: AlertPreferencesRequest):
    success = save_alert_preferences(user_id=req.user_id, preferences=req.sources)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save alert preferences.")
    return {"status": "success", "message": "Alert preferences updated successfully."}

app.include_router(research.router,  prefix="/api",            tags=["research"])
app.include_router(pdf_analyzer.router, prefix="/api",         tags=["research"])
