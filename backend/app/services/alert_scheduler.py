"""
alert_scheduler.py — Background Scheduler for Guideline Alerts
===============================================================
Uses APScheduler BackgroundScheduler to run check_and_notify()
every 6 hours. Integrates with FastAPI lifespan for clean start/stop.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.alert_service import check_and_notify

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    """Starts the background alert scheduler (runs every 6 hours)."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("[Scheduler] Alert scheduler is already running.")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        check_and_notify,
        trigger=IntervalTrigger(hours=6),
        id="guideline_alert_check",
        name="Breaking Guideline Alert Check",
        replace_existing=True,
        misfire_grace_time=600,  # 10 min grace for missed jobs
    )
    _scheduler.start()
    logger.info("[Scheduler] ✅ Alert scheduler started — checking every 6 hours.")


def stop_scheduler():
    """Gracefully shuts down the background alert scheduler."""
    global _scheduler

    if _scheduler is None:
        logger.info("[Scheduler] No scheduler instance to stop.")
        return

    try:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] 🛑 Alert scheduler stopped.")
    except Exception as e:
        logger.error(f"[Scheduler] Error shutting down scheduler: {e}")
    finally:
        _scheduler = None
