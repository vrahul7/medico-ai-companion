from fastapi import HTTPException
from pydantic import BaseModel

# In a production environment, this would mock connecting to Redis or Supabase User Metadata
class RateLimiterService:
    def __init__(self):
        # Mock database of user usage
        self.user_limits = {
            "free_user_1": {"queries_used": 19, "tier": "free"},
            "free_user_2": {"queries_used": 20, "tier": "free"},
            "pro_user_1": {"queries_used": 150, "tier": "pro"}
        }
        self.FREE_TIER_LIMIT = 20

    def enforce_query_limit(self, user_id: str) -> bool:
        """
        Enforce strict query limits on the Free Tier.
        Medical users demand a clean interface, so we use hard limits over Ads.
        """
        user_data = self.user_limits.get(user_id)
        if not user_data:
            # Assume new user
            return True

        if user_data["tier"] == "pro":
            return True # Unlimited

        if user_data["queries_used"] >= self.FREE_TIER_LIMIT:
            raise HTTPException(
                status_code=429, 
                detail="Free tier limit reached. Please upgrade to Pro to run further Differential Diagnoses."
            )
            
        return True

    def increment_usage(self, user_id: str):
        if user_id in self.user_limits:
            self.user_limits[user_id]["queries_used"] += 1

rate_limiter = RateLimiterService()
