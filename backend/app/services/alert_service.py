"""
alert_service.py — Breaking Guideline Alerts Service
=====================================================
Monitors RSS guideline feeds for new publications from priority health
organizations and sends FCM push notifications to registered devices.

Priority sources: WHO SEARO, DOHFW, DGHS, AAP, KDIGO, ACOG
"""

import hashlib
import logging
from firebase_admin import messaging

from app.services.rss_fetcher import fetch_rss_guidelines
from app.services.firebase_client import (
    is_guideline_seen,
    mark_guideline_seen,
    get_all_device_tokens,
)

logger = logging.getLogger(__name__)

# Sources that trigger breaking alerts
ALERT_SOURCES = {"WHO SEARO", "DOHFW", "DGHS", "AAP", "KDIGO", "ACOG"}


def _compute_guideline_hash(link: str) -> str:
    """Computes a stable SHA-256 hash of the guideline link for deduplication."""
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


def send_fcm_notification(
    tokens: list[str], title: str, body: str, data: dict | None = None
) -> int:
    """Sends an FCM push notification to a list of device tokens.
    Returns the number of successful sends.
    """
    if not tokens:
        logger.info("[Alerts] No device tokens registered — skipping FCM send.")
        return 0

    success_count = 0
    # FCM multicast supports up to 500 tokens per batch
    batch_size = 500
    for i in range(0, len(tokens), batch_size):
        batch_tokens = tokens[i : i + batch_size]
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=batch_tokens,
        )
        try:
            response = messaging.send_each_for_multicast(message)
            success_count += response.success_count
            if response.failure_count > 0:
                logger.warning(
                    f"[Alerts] FCM batch {i // batch_size + 1}: "
                    f"{response.failure_count}/{len(batch_tokens)} failed."
                )
        except Exception as e:
            logger.error(f"[Alerts] FCM send failed for batch {i // batch_size + 1}: {e}")

    logger.info(f"[Alerts] FCM notifications sent successfully to {success_count} devices.")
    return success_count


def check_and_notify():
    """Main scheduler entry point — fetches latest guidelines, detects unseen
    items from priority sources, and sends FCM push notifications.
    """
    logger.info("[Alerts] Running scheduled guideline check...")

    try:
        guidelines = fetch_rss_guidelines(page=1)
    except Exception as e:
        logger.error(f"[Alerts] Failed to fetch guidelines for alert check: {e}")
        return

    new_guidelines = []
    for item in guidelines:
        # Only alert on priority sources
        if item.source not in ALERT_SOURCES:
            continue

        guideline_hash = _compute_guideline_hash(item.link)

        try:
            if is_guideline_seen(guideline_hash):
                continue
        except Exception as e:
            logger.warning(f"[Alerts] Error checking seen status for {item.link}: {e}")
            continue

        new_guidelines.append((item, guideline_hash))

    if not new_guidelines:
        logger.info("[Alerts] No new guidelines detected — nothing to notify.")
        return

    logger.info(f"[Alerts] Found {len(new_guidelines)} new guideline(s) to notify.")

    # Retrieve all registered device tokens once
    try:
        tokens = get_all_device_tokens()
    except Exception as e:
        logger.error(f"[Alerts] Failed to retrieve device tokens: {e}")
        return

    for item, guideline_hash in new_guidelines:
        title = f"🏥 New {item.source} Guideline"
        body = item.title[:200]  # FCM body limit safety
        data = {
            "type": "guideline_alert",
            "source": item.source,
            "link": item.link,
            "published": item.published or "",
        }

        try:
            send_fcm_notification(tokens=tokens, title=title, body=body, data=data)
        except Exception as e:
            logger.error(f"[Alerts] Notification send failed for {item.link}: {e}")

        # Mark as seen regardless of send outcome to avoid re-alerting
        try:
            mark_guideline_seen(guideline_hash)
        except Exception as e:
            logger.error(f"[Alerts] Failed to mark guideline as seen: {e}")

    logger.info("[Alerts] Scheduled guideline check complete.")
