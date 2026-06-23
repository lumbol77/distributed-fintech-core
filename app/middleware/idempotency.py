import json
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis

# Connect to your offline Redis container locally
redis_client = redis.Redis(host="redis", port=6379, db=1, decode_responses=False)

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Only enforce idempotency on POST requests (like transfers/deposits)
        if request.method != "POST":
            return await call_next(request)

        # 2. Extract the unique tracking key sent by the frontend
        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            # If no key is provided, let it pass normally or enforce it based on policy
            return await call_next(request)

        redis_key = f"idempotency:{idempotency_key}"

        # 3. Check if this key already exists in Redis cache
        cached_data = redis_client.get(redis_key)
        
        if cached_data:
            # Decode the stored status
            cached_json = json.loads(cached_data.decode('utf-8'))
            
            if cached_json.get("status") == "PROCESSING":
                raise HTTPException(status_code=409, detail="Duplicate request detected. Transaction is already processing.")
            
            # If it's fully completed, return the identical saved response instantly!
            return Response(
                content=cached_json["body"],
                status_code=cached_json["status_code"],
                media_type="application/json"
            )

        # 4. If key doesn't exist, lock it as "PROCESSING" for 5 minutes
        initial_payload = json.dumps({"status": "PROCESSING"})
        redis_client.setex(redis_key, 300, initial_payload)

        # 5. Let the request proceed to your wallet.py endpoints
        try:
            response = await call_next(request)
            
            # Consuming response body safely to cache it
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # 6. Save the final successful result back to Redis
            final_payload = json.dumps({
                "status": "COMPLETED",
                "status_code": response.status_code,
                "body": response_body.decode('utf-8')
            })
            redis_client.setex(redis_key, 300, final_payload)

            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
        except Exception as e:
            # If your app crashes mid-way, delete the lock so the user can try again safely
            redis_client.delete(redis_key)
            raise e