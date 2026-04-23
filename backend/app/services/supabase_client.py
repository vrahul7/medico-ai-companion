import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

supabase: Client | None = None

try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
    else:
        logger.warning("Supabase credentials not found in environment. Summary caching will be disabled.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")

def get_cached_summary(content_hash: str) -> str | None:
    """Fetches a summary from Supabase if it exists and is less than 24 hours old."""
    if not supabase:
        return None
    try:
        # Supabase Python client query
        response = supabase.table('feed_summaries').select('summary_text, created_at').eq('content_hash', content_hash).execute()
        if response.data and len(response.data) > 0:
            # If we wanted strict 24h checks in Python, we'd parse created_at here.
            # But for simple offline caching, any response is good, or we can trust the DB TTL.
            import datetime
            created_at_str = response.data[0].get('created_at')
            if created_at_str:
                # Parse ISO 8601 string
                created_at = datetime.datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                now = datetime.datetime.now(datetime.timezone.utc)
                if (now - created_at).total_seconds() < 86400: # 24 hours
                    return response.data[0].get('summary_text')
        return None
    except Exception as e:
        logger.warning(f"Error reading from Supabase cache: {e}")
        return None

def cache_summary(content_hash: str, summary_text: str):
    """Upserts a generated summary into Supabase."""
    if not supabase:
        return
    try:
        # Upsert based on content_hash (which should be primary key or unique)
        supabase.table('feed_summaries').upsert({
            'content_hash': content_hash,
            'summary_text': summary_text
        }).execute()
    except Exception as e:
        logger.warning(f"Error writing to Supabase cache: {e}")
