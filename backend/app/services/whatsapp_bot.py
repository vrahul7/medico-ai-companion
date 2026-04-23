"""
whatsapp_bot.py — WhatsApp Bot Message Processor
=================================================
Handles incoming clinical queries from approved doctors on WhatsApp.

Responsibilities:
  - Whitelist gate: only approved phone numbers get responses
  - Session memory: remembers last 3 turns per doctor
  - Presidio PII strip before RAG engine
  - Formats RAG responses into WhatsApp-safe plain text (max 1500 chars)
  - Rate limits: same 20 queries/day free tier as web
  - Mandatory clinical disclaimer on first message of a session
"""

import os
import logging
from datetime import date
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

def _normalize_phone(num: str) -> str:
    """Removes all non-digit characters except the leading '+' and 'whatsapp:' prefix."""
    prefix = "whatsapp:" if num.startswith("whatsapp:") else ""
    digits = "".join(filter(str.isdigit, num))
    if not digits: return ""
    # Ensure it starts with the country code
    return f"{prefix}+{digits}"

_RAW_WHITELIST = os.getenv("WHATSAPP_APPROVED_NUMBERS", "")
APPROVED_NUMBERS: set = {
    _normalize_phone(n.strip()) for n in _RAW_WHITELIST.split(",") if n.strip()
}

# ── Rate Limiter (in-memory, per phone number per day) ─────────────────────
_QUERY_COUNTS: Dict[str, Dict] = {}  # {number: {"date": date, "count": int}}
FREE_TIER_LIMIT = 20

# ── Session Memory (last 3 turns per doctor) ───────────────────────────────
_SESSIONS: Dict[str, List[str]] = {}   # {number: ["Q: ...\nA: ...", ...]}
SESSION_MAX_TURNS = 3

# ── Clinical Disclaimer ────────────────────────────────────────────────────
DISCLAIMER = (
    "⚠️ *Medico AI — Clinical Support Tool*\n"
    "Not a substitute for professional medical judgment.\n"
    "Do NOT share patient names, DOB, or any personal details.\n"
    "─────────────────────────\n"
)

WELCOME_MSG = (
    "👋 Welcome to *Medico AI Companion*!\n\n"
    "I can help with:\n"
    "• Differential diagnoses\n"
    "• Drug dosing & interactions\n"
    "• Clinical guidelines\n"
    "• Latest research summaries\n\n"
    "Type *HELP* anytime for commands.\n\n"
    + DISCLAIMER
)

RATE_LIMIT_MSG = (
    "🔒 You've used your *20 free queries today*.\n"
    "Your limit resets at midnight.\n\n"
    "Upgrade to Pro for unlimited access:\n"
    "👉 medico-ai.club/pro"
)

NOT_AUTHORIZED_MSG = (
    "🔒 *Access Restricted*\n\n"
    "This service is available to approved medical professionals only.\n"
    "Contact your administrator to request access."
)

# ── Special Commands ───────────────────────────────────────────────────────
COMMANDS = {
    "HELP": (
        "📋 *Medico AI Commands*\n\n"
        "• Ask any clinical question directly\n"
        "• *CLEAR* — clear conversation history\n"
        "• *LIMIT* — check your query count today\n"
        "• *HELP* — show this menu\n\n"
        "Example queries:\n"
        "_DDx for 4yo with fever, wheeze, SpO2 94%_\n"
        "_Salbutamol dose for 15kg child_\n"
        "_Nelson's on febrile seizure management_"
    ),
    "CLEAR": "✅ Conversation history cleared.",
    "LIMIT": None,  # Dynamic — filled at runtime
}


class WhatsAppBotService:
    """Main service class wiring whitelist → rate limit → anonymizer → RAG → formatter."""

    def __init__(self):
        from app.services.rag import HybridRAGEngine
        from app.services.anonymizer import anonymize_text
        self._engine = HybridRAGEngine()
        self._anonymize = anonymize_text
        logger.info(f"WhatsApp bot ready. {len(APPROVED_NUMBERS)} approved numbers loaded.")

    def is_approved(self, from_number: str) -> bool:
        """Check if incoming number is in the whitelist."""
        if not APPROVED_NUMBERS:
            logger.warning("WHATSAPP_APPROVED_NUMBERS not set — all access denied.")
            return False
        
        normalized_from = _normalize_phone(from_number).replace("whatsapp:", "")
        # Also check against the raw from_number just in case
        is_ok = normalized_from in APPROVED_NUMBERS or from_number.replace("whatsapp:", "") in APPROVED_NUMBERS
        
        if not is_ok:
            logger.warning(f"[Auth] Access denied for: {from_number} (Normalized: {normalized_from})")
            logger.warning(f"[Auth] Whitelist contains: {list(APPROVED_NUMBERS)}")
            
        return is_ok

    def check_rate_limit(self, from_number: str) -> bool:
        """Returns True if doctor is within daily query limit."""
        today = date.today()
        entry = _QUERY_COUNTS.get(from_number)
        if not entry or entry["date"] != today:
            _QUERY_COUNTS[from_number] = {"date": today, "count": 0}
        return _QUERY_COUNTS[from_number]["count"] < FREE_TIER_LIMIT

    def increment_usage(self, from_number: str):
        today = date.today()
        if from_number not in _QUERY_COUNTS or _QUERY_COUNTS[from_number]["date"] != today:
            _QUERY_COUNTS[from_number] = {"date": today, "count": 0}
        _QUERY_COUNTS[from_number]["count"] += 1

    def get_usage(self, from_number: str) -> int:
        today = date.today()
        entry = _QUERY_COUNTS.get(from_number)
        if not entry or entry["date"] != today:
            return 0
        return entry["count"]

    def get_session(self, from_number: str) -> str:
        """Returns formatted conversation history for context injection."""
        turns = _SESSIONS.get(from_number, [])
        return "\n\n".join(turns[-SESSION_MAX_TURNS:])

    def save_to_session(self, from_number: str, query: str, answer: str):
        if from_number not in _SESSIONS:
            _SESSIONS[from_number] = []
        _SESSIONS[from_number].append(f"Q: {query}\nA: {answer[:200]}")
        # Keep only last N turns
        _SESSIONS[from_number] = _SESSIONS[from_number][-SESSION_MAX_TURNS:]

    def clear_session(self, from_number: str):
        _SESSIONS.pop(from_number, None)

    def is_first_message(self, from_number: str) -> bool:
        return from_number not in _SESSIONS or len(_SESSIONS[from_number]) == 0

    def process(self, from_number: str, body: str) -> str:
        """
        Main entry point. Returns the WhatsApp reply string.
        """
        body = body.strip()
        upper = body.upper()

        # ── 1. Whitelist gate ──────────────────────────────────────────────
        if not self.is_approved(from_number):
            logger.warning(f"Blocked unauthorized number: {from_number}")
            return NOT_AUTHORIZED_MSG

        # ── 2. Special commands ────────────────────────────────────────────
        if upper == "HELP":
            return COMMANDS["HELP"]

        if upper == "CLEAR":
            self.clear_session(from_number)
            return COMMANDS["CLEAR"]

        if upper == "LIMIT":
            used = self.get_usage(from_number)
            remaining = max(0, FREE_TIER_LIMIT - used)
            return (
                f"📊 *Query Usage Today*\n\n"
                f"Used: {used} / {FREE_TIER_LIMIT}\n"
                f"Remaining: {remaining} queries\n"
                f"Resets at midnight."
            )

        # ── 3. Welcome message on first contact ───────────────────────────
        if self.is_first_message(from_number):
            # Send welcome, then process the query below
            welcome = WELCOME_MSG
        else:
            welcome = None

        # ── 4. Rate limit check ───────────────────────────────────────────
        if not self.check_rate_limit(from_number):
            return RATE_LIMIT_MSG

        # ── 5. Presidio PII anonymization ─────────────────────────────────
        try:
            safe_query = self._anonymize(body)
        except Exception:
            safe_query = body  # Fail open — proceed with original if anonymizer down

        # ── 6. Inject conversation context ────────────────────────────────
        history = self.get_session(from_number)
        if history:
            full_query = f"[Conversation history:\n{history}]\n\nNew question: {safe_query}"
        else:
            full_query = safe_query

        # ── 7. RAG synthesis ──────────────────────────────────────────────
        try:
            result = self._engine.synthesize(full_query)
        except Exception as e:
            logger.error(f"RAG synthesis error for {from_number}: {e}")
            return (
                "⚠️ I encountered an error processing your query.\n"
                "Please try rephrasing or contact support."
            )

        # ── 8. Format response for WhatsApp ───────────────────────────────
        reply = self._format_whatsapp_response(result)

        # ── 9. Save to session + increment usage ──────────────────────────
        self.save_to_session(from_number, body, result.get("answer", ""))
        self.increment_usage(from_number)

        # Prepend welcome for first-time users
        if welcome:
            return welcome + "\n\n" + reply
        return reply

    def _format_whatsapp_response(self, result: dict) -> str:
        """
        Converts RAG result dict to WhatsApp-safe plain text.
        WhatsApp supports *bold*, _italic_, ~strikethrough~, ```code```.
        Max safe message length: ~1500 chars.
        """
        answer = result.get("answer") or result.get("clinical_answer") or "No answer generated."
        citations = result.get("citations", [])
        confidence = result.get("confidence_score", 0.0)

        # Truncate answer to 1100 chars to leave room for citations
        if len(answer) > 1100:
            answer = answer[:1097] + "..."

        parts = [f"🩺 *Medico AI*\n{'─' * 25}\n{answer}"]

        # Format citations
        if citations:
            cite_lines = ["", "📚 *Sources:*"]
            for i, c in enumerate(citations[:4], 1):  # Cap at 4 sources
                ctx = c.get("structural_context", "")
                quote = c.get("exact_quote", "")[:80]
                cite_lines.append(f"[{i}] {ctx}")
                if quote:
                    cite_lines.append(f"    _\"{quote}...\"_")
            parts.append("\n".join(cite_lines))

        # Confidence warning for borderline answers
        if 0 < confidence < 0.85:
            parts.append(
                "\n⚠️ _Low confidence — please cross-check with primary sources._"
            )

        # Footer disclaimer (short version)
        parts.append("\n─────────────────────────")
        parts.append("_For clinical support only. Not medical advice._")

        full = "\n".join(parts)

        # Final safety truncation
        if len(full) > 1500:
            full = full[:1490] + "...\n_[truncated]_"

        return full


# Singleton
whatsapp_bot = WhatsAppBotService()
