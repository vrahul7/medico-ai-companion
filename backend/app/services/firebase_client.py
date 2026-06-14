import os
import datetime
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# Global Firestore client instance
db = None
_local_cache = {}

try:
    # Try initialization with credentials file path
    firebase_cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if firebase_cred_path and os.path.exists(firebase_cred_path):
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("[Firebase] ✅ Firebase initialized with service account certificate.")
    else:
        # Try default credential resolution (Google App Engine/Cloud Run automatic IAM)
        try:
            firebase_admin.initialize_app()
            db = firestore.client()
            logger.info("[Firebase] ✅ Firebase initialized with Application Default Credentials.")
        except Exception:
            logger.warning("[Firebase] ⚠️ No credentials found. Running in local mock/in-memory database fallback mode.")
except Exception as e:
    logger.error(f"[Firebase] Initialization failed: {e}. Running in local mock/in-memory database fallback mode.")


def get_cached_summary(content_hash: str) -> dict | None:
    """Fetches a cached summary dict from Firestore if it exists and is less than 24 hours old.
    Returns dict with 'summary_text' and 'clinical_digest' keys, or None if not cached.
    """
    global _local_cache
    if not db:
        # Fallback to local memory cache
        cached = _local_cache.get(content_hash)
        if cached:
            time_diff = datetime.datetime.now(datetime.timezone.utc) - cached["created_at"]
            if time_diff.total_seconds() < 86400:
                return {
                    "summary_text": cached["summary_text"],
                    "clinical_digest": cached.get("clinical_digest")
                }
        return None

    try:
        doc_ref = db.collection('feed_summaries').document(content_hash)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if created_at:
                # Firestore returns datetime objects directly
                if isinstance(created_at, str):
                    created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now = datetime.datetime.now(datetime.timezone.utc)
                if (now - created_at).total_seconds() < 86400: # 24 hours TTL
                    return {
                        "summary_text": data.get('summary_text'),
                        "clinical_digest": data.get('clinical_digest')
                    }
        return None
    except Exception as e:
        logger.warning(f"Error reading from Cloud Firestore cache: {e}")
        return None


def cache_summary(content_hash: str, summary_text: str, clinical_digest: str | None = None):
    """Upserts a generated summary into Cloud Firestore."""
    global _local_cache
    now = datetime.datetime.now(datetime.timezone.utc)
    if not db:
        # Fallback to local memory cache
        _local_cache[content_hash] = {
            "summary_text": summary_text,
            "clinical_digest": clinical_digest,
            "created_at": now
        }
        return

    try:
        doc_ref = db.collection('feed_summaries').document(content_hash)
        doc_data = {
            'content_hash': content_hash,
            'summary_text': summary_text,
            'created_at': now
        }
        if clinical_digest:
            doc_data['clinical_digest'] = clinical_digest
        doc_ref.set(doc_data)
    except Exception as e:
        logger.warning(f"Error writing to Cloud Firestore cache: {e}")


def submit_summary_feedback(user_id: str, item_id: str, rating: str, comment: str = None) -> bool:
    """Records rating feedback for research summary cards."""
    if not db:
        logger.info(f"[Firebase Mock Feedback] User {user_id} rated {item_id}: {rating} (comment: {comment})")
        return True

    try:
        feedback_ref = db.collection('feed_feedback').document()
        feedback_ref.set({
            'user_id': user_id,
            'item_id': item_id,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.datetime.now(datetime.timezone.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Failed to save feedback to Cloud Firestore: {e}")
        return False


_read_feeds_cache = {}  # dict mapping user_id -> set of item_ids
_bookmarked_feeds_cache = {}  # dict mapping user_id -> dict of item_id -> {tags, bookmarked_at}

def mark_feed_as_read(user_id: str, item_id: str) -> bool:
    """Marks a feed item as read by the user in Firestore."""
    global _read_feeds_cache
    if not db:
        if user_id not in _read_feeds_cache:
            _read_feeds_cache[user_id] = set()
        _read_feeds_cache[user_id].add(item_id)
        logger.info(f"[Firebase Mock Read] User {user_id} read feed item: {item_id}")
        return True
        
    try:
        read_ref = db.collection('feed_read').document(f"{user_id}_{item_id}")
        read_ref.set({
            'user_id': user_id,
            'item_id': item_id,
            'read_at': datetime.datetime.now(datetime.timezone.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Failed to save read state to Cloud Firestore: {e}")
        return False

def get_read_feed_ids(user_id: str) -> list[str]:
    """Retrieves all feed item IDs read by the user."""
    global _read_feeds_cache
    if not db:
        return list(_read_feeds_cache.get(user_id, set()))
        
    try:
        docs = db.collection('feed_read').where('user_id', '==', user_id).stream()
        return [doc.to_dict().get('item_id') for doc in docs if doc.to_dict().get('item_id')]
    except Exception as e:
        logger.warning(f"Error reading read feeds from Cloud Firestore: {e}")
        return []

def toggle_bookmark(user_id: str, item_id: str, bookmarked: bool, tags: list[str] | None = None) -> bool:
    """Bookmarks or unbookmarks a feed item for the user in Firestore, with optional tags."""
    global _bookmarked_feeds_cache
    if not db:
        if user_id not in _bookmarked_feeds_cache:
            _bookmarked_feeds_cache[user_id] = {}
        if bookmarked:
            _bookmarked_feeds_cache[user_id][item_id] = {
                "tags": tags or [],
                "bookmarked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        else:
            _bookmarked_feeds_cache[user_id].pop(item_id, None)
        logger.info(f"[Firebase Mock Bookmark] User {user_id} set bookmark for {item_id} to: {bookmarked} (tags: {tags})")
        return True
        
    try:
        bookmark_ref = db.collection('feed_bookmarks').document(f"{user_id}_{item_id}")
        if bookmarked:
            doc_data = {
                'user_id': user_id,
                'item_id': item_id,
                'bookmarked_at': datetime.datetime.now(datetime.timezone.utc)
            }
            if tags:
                doc_data['tags'] = tags
            bookmark_ref.set(doc_data)
        else:
            bookmark_ref.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to toggle bookmark in Cloud Firestore: {e}")
        return False


def update_bookmark_tags(user_id: str, item_id: str, tags: list[str]) -> bool:
    """Updates tags on an existing bookmark."""
    global _bookmarked_feeds_cache
    if not db:
        if user_id in _bookmarked_feeds_cache and item_id in _bookmarked_feeds_cache[user_id]:
            _bookmarked_feeds_cache[user_id][item_id]["tags"] = tags
            logger.info(f"[Firebase Mock Tags] User {user_id} updated tags for {item_id}: {tags}")
            return True
        logger.warning(f"[Firebase Mock Tags] Bookmark {item_id} not found for user {user_id}")
        return False

    try:
        bookmark_ref = db.collection('feed_bookmarks').document(f"{user_id}_{item_id}")
        doc = bookmark_ref.get()
        if not doc.exists:
            logger.warning(f"Bookmark {item_id} not found for user {user_id}")
            return False
        bookmark_ref.update({'tags': tags})
        return True
    except Exception as e:
        logger.error(f"Failed to update bookmark tags in Cloud Firestore: {e}")
        return False


def get_bookmarked_feed_ids(user_id: str, tag: str | None = None) -> list[str]:
    """Retrieves bookmarked item IDs for the user, optionally filtered by tag."""
    global _bookmarked_feeds_cache
    if not db:
        bookmarks = _bookmarked_feeds_cache.get(user_id, {})
        if tag:
            return [item_id for item_id, data in bookmarks.items() if tag in data.get("tags", [])]
        return list(bookmarks.keys())
        
    try:
        query = db.collection('feed_bookmarks').where('user_id', '==', user_id)
        if tag:
            query = query.where('tags', 'array_contains', tag)
        docs = query.stream()
        return [doc.to_dict().get('item_id') for doc in docs if doc.to_dict().get('item_id')]
    except Exception as e:
        logger.warning(f"Error reading bookmarked feeds from Cloud Firestore: {e}")
        return []


def get_bookmarks_with_tags(user_id: str) -> list[dict]:
    """Retrieves full bookmark data including tags for the user."""
    global _bookmarked_feeds_cache
    if not db:
        bookmarks = _bookmarked_feeds_cache.get(user_id, {})
        return [
            {"item_id": item_id, "tags": data.get("tags", []), "bookmarked_at": data.get("bookmarked_at")}
            for item_id, data in bookmarks.items()
        ]

    try:
        docs = db.collection('feed_bookmarks').where('user_id', '==', user_id).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "item_id": data.get("item_id"),
                "tags": data.get("tags", []),
                "bookmarked_at": data.get("bookmarked_at", "").isoformat() if hasattr(data.get("bookmarked_at", ""), "isoformat") else str(data.get("bookmarked_at", ""))
            })
        return results
    except Exception as e:
        logger.warning(f"Error reading bookmarks with tags from Cloud Firestore: {e}")
        return []


# ═══════════════════════════════════════════════════════════
# Task 3: Breaking Guideline Alerts — Firestore Functions
# ═══════════════════════════════════════════════════════════

_device_tokens_cache = {}  # user_id -> fcm_token
_seen_guidelines_cache = set()  # set of guideline hashes
_alert_preferences_cache = {}  # user_id -> preferences dict

# Default alert sources — all enabled
DEFAULT_ALERT_SOURCES = {
    "WHO SEARO": True,
    "DOHFW": True,
    "DGHS": True,
    "AAP": True,
    "KDIGO": True,
    "ACOG": True,
}


def register_device_token(user_id: str, fcm_token: str) -> bool:
    """Upserts a device FCM token for push notifications."""
    global _device_tokens_cache
    if not db:
        _device_tokens_cache[user_id] = fcm_token
        logger.info(f"[Firebase Mock] Registered device token for user {user_id}")
        return True

    try:
        doc_ref = db.collection('device_tokens').document(user_id)
        doc_ref.set({
            'user_id': user_id,
            'fcm_token': fcm_token,
            'updated_at': datetime.datetime.now(datetime.timezone.utc)
        })
        logger.info(f"[Firebase] Registered device token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to register device token: {e}")
        return False


def get_all_device_tokens() -> list[str]:
    """Returns list of all registered FCM tokens."""
    global _device_tokens_cache
    if not db:
        return list(_device_tokens_cache.values())

    try:
        docs = db.collection('device_tokens').stream()
        tokens = []
        for doc in docs:
            data = doc.to_dict()
            token = data.get('fcm_token')
            if token:
                tokens.append(token)
        return tokens
    except Exception as e:
        logger.error(f"Failed to retrieve device tokens: {e}")
        return []


def mark_guideline_seen(guideline_hash: str) -> bool:
    """Marks a guideline as seen (by hash) in Firestore."""
    global _seen_guidelines_cache
    if not db:
        _seen_guidelines_cache.add(guideline_hash)
        return True

    try:
        doc_ref = db.collection('seen_guidelines').document(guideline_hash)
        doc_ref.set({
            'guideline_hash': guideline_hash,
            'seen_at': datetime.datetime.now(datetime.timezone.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Failed to mark guideline as seen: {e}")
        return False


def is_guideline_seen(guideline_hash: str) -> bool:
    """Checks if a guideline hash has already been seen."""
    global _seen_guidelines_cache
    if not db:
        return guideline_hash in _seen_guidelines_cache

    try:
        doc_ref = db.collection('seen_guidelines').document(guideline_hash)
        doc = doc_ref.get()
        return doc.exists
    except Exception as e:
        logger.error(f"Failed to check seen guideline: {e}")
        return False


def save_alert_preferences(user_id: str, preferences: dict) -> bool:
    """Stores user alert source preferences in Firestore."""
    global _alert_preferences_cache
    if not db:
        _alert_preferences_cache[user_id] = preferences
        logger.info(f"[Firebase Mock] Saved alert preferences for user {user_id}")
        return True

    try:
        doc_ref = db.collection('alert_preferences').document(user_id)
        doc_ref.set({
            'user_id': user_id,
            'sources': preferences,
            'updated_at': datetime.datetime.now(datetime.timezone.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Failed to save alert preferences: {e}")
        return False


def get_alert_preferences(user_id: str) -> dict:
    """Retrieves user alert preferences. Returns defaults if none saved."""
    global _alert_preferences_cache
    if not db:
        return _alert_preferences_cache.get(user_id, DEFAULT_ALERT_SOURCES.copy())

    try:
        doc_ref = db.collection('alert_preferences').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get('sources', DEFAULT_ALERT_SOURCES.copy())
        return DEFAULT_ALERT_SOURCES.copy()
    except Exception as e:
        logger.error(f"Failed to get alert preferences: {e}")
        return DEFAULT_ALERT_SOURCES.copy()

