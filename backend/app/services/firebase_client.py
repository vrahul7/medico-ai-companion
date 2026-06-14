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


def get_cached_summary(content_hash: str) -> str | None:
    """Fetches a summary from Firestore if it exists and is less than 24 hours old."""
    global _local_cache
    if not db:
        # Fallback to local memory cache
        cached = _local_cache.get(content_hash)
        if cached:
            time_diff = datetime.datetime.now(datetime.timezone.utc) - cached["created_at"]
            if time_diff.total_seconds() < 86400:
                return cached["summary_text"]
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
                    return data.get('summary_text')
        return None
    except Exception as e:
        logger.warning(f"Error reading from Cloud Firestore cache: {e}")
        return None


def cache_summary(content_hash: str, summary_text: str):
    """Upserts a generated summary into Cloud Firestore."""
    global _local_cache
    now = datetime.datetime.now(datetime.timezone.utc)
    if not db:
        # Fallback to local memory cache
        _local_cache[content_hash] = {
            "summary_text": summary_text,
            "created_at": now
        }
        return

    try:
        doc_ref = db.collection('feed_summaries').document(content_hash)
        doc_ref.set({
            'content_hash': content_hash,
            'summary_text': summary_text,
            'created_at': now
        })
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
_bookmarked_feeds_cache = {}  # dict mapping user_id -> set of item_ids

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

def toggle_bookmark(user_id: str, item_id: str, bookmarked: bool) -> bool:
    """Bookmarks or unbookmarks a feed item for the user in Firestore."""
    global _bookmarked_feeds_cache
    if not db:
        if user_id not in _bookmarked_feeds_cache:
            _bookmarked_feeds_cache[user_id] = set()
        if bookmarked:
            _bookmarked_feeds_cache[user_id].add(item_id)
        else:
            _bookmarked_feeds_cache[user_id].discard(item_id)
        logger.info(f"[Firebase Mock Bookmark] User {user_id} set bookmark for {item_id} to: {bookmarked}")
        return True
        
    try:
        bookmark_ref = db.collection('feed_bookmarks').document(f"{user_id}_{item_id}")
        if bookmarked:
            bookmark_ref.set({
                'user_id': user_id,
                'item_id': item_id,
                'bookmarked_at': datetime.datetime.now(datetime.timezone.utc)
            })
        else:
            bookmark_ref.delete()
        return True
    except Exception as e:
        logger.error(f"Failed to toggle bookmark in Cloud Firestore: {e}")
        return False

def get_bookmarked_feed_ids(user_id: str) -> list[str]:
    """Retrieves all feed item IDs bookmarked by the user."""
    global _bookmarked_feeds_cache
    if not db:
        return list(_bookmarked_feeds_cache.get(user_id, set()))
        
    try:
        docs = db.collection('feed_bookmarks').where('user_id', '==', user_id).stream()
        return [doc.to_dict().get('item_id') for doc in docs if doc.to_dict().get('item_id')]
    except Exception as e:
        logger.warning(f"Error reading bookmarked feeds from Cloud Firestore: {e}")
        return []
