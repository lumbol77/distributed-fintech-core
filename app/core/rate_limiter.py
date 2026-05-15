from fastapi import HTTPException, Depends
from app.core.redis_client import redis_client
from app.security import get_current_user

def rate_limit_user(current_user = Depends(get_current_user), limit: int = 5, window: int = 60):
    # We get the ID directly from the logged-in user
    user_id = current_user.id
    key = f"rate_limit:{user_id}"

    current = redis_client.get(key)

    if current is None:
        # First request → set counter to 1
        redis_client.set(key, 1, ex=window)
        return

    if int(current) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    # Increment counter for every successful request within the window
    redis_client.incr(key)