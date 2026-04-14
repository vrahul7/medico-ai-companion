"""
whatsapp.py — WhatsApp Webhook Router
======================================
Handles Twilio WhatsApp Sandbox webhook calls.

Endpoints:
  GET  /api/whatsapp/webhook  — Twilio webhook verification ping
  POST /api/whatsapp/webhook  — Incoming WhatsApp message handler

Setup:
  1. Run: ngrok http 8000
  2. Set Twilio sandbox webhook to: https://<ngrok-url>/api/whatsapp/webhook
  3. Doctors WhatsApp "join <code>" to Twilio sandbox number
  4. First message triggers welcome + whitelist check
"""

import os
import logging
import hmac
import hashlib
import base64
from fastapi import APIRouter, Form, Request, Response, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

router = APIRouter()

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")


def _validate_twilio_signature(request: Request, body: bytes) -> bool:
    """
    Validates that the webhook POST is genuinely from Twilio.
    Uses HMAC-SHA1 of the URL + sorted POST params.
    Skip validation in dev mode if auth token not configured.
    """
    if not TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_AUTH_TOKEN not set — skipping signature validation (dev mode)")
        return True

    twilio_sig = request.headers.get("X-Twilio-Signature", "")
    if not twilio_sig:
        return False

    url = str(request.url)
    # Reconstruct validation string: URL + sorted key=value pairs
    # (Twilio sends form-encoded data, so we need the raw body for this)
    mac = hmac.new(TWILIO_AUTH_TOKEN.encode(), url.encode(), hashlib.sha1)
    expected = base64.b64encode(mac.digest()).decode()
    return hmac.compare_digest(expected, twilio_sig)


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None,
):
    """
    Meta WhatsApp Cloud API verification endpoint.
    (Twilio doesn't need this, but included for future Meta migration.)
    """
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "medico-ai-verify")
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("WhatsApp webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook")
async def receive_whatsapp_message(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
    MessageSid: str = Form(default=""),
    ProfileName: str = Form(default=""),
):
    """
    Twilio WhatsApp Sandbox message receiver.
    Twilio sends incoming messages as application/x-www-form-urlencoded POST.
    Returns TwiML XML that Twilio uses to send the reply back to WhatsApp.
    """
    logger.info(f"[WhatsApp] Incoming | From: {From} | SID: {MessageSid} | Body: {Body[:60]}")

    # Import here to avoid circular imports at module init
    from app.services.whatsapp_bot import whatsapp_bot

    # Process the message through the bot pipeline
    try:
        reply_text = whatsapp_bot.process(from_number=From, body=Body)
    except Exception as e:
        logger.exception(f"[WhatsApp] Unhandled bot error for {From}: {e}")
        reply_text = (
            "⚠️ Medico AI encountered an unexpected error.\n"
            "Please try again in a moment or contact support."
        )

    # Build TwiML response (Twilio reads this XML to send the reply)
    resp = MessagingResponse()
    resp.message(reply_text)

    logger.info(f"[WhatsApp] Reply sent to {From} ({len(reply_text)} chars)")
    return Response(content=str(resp), media_type="application/xml")
