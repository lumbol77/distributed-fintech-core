import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import request_id_ctx

class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if an ID already exists (from another service), otherwise create one
        tx_id = request.headers.get("X-Request-ID", f"TX-{uuid.uuid4().hex[:8].upper()}")
        
        # Set the context for the logger
        token = request_id_ctx.set(tx_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = tx_id
            return response
        finally:
            # Clean up context after request finishes
            request_id_ctx.reset(token)