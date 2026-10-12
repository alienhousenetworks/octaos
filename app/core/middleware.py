import logging
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings
from app.models.base import tenant_context, org_context

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant and org from headers
        tenant_id = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
        org_id = request.headers.get("x-organization-id") or request.headers.get("X-Organization-ID")
        
        # Attempt to decode JWT if headers aren't explicitly passed
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                if not tenant_id:
                    tenant_id = payload.get("tenant_id")
                if not org_id:
                    org_id = payload.get("organization_id")
            except Exception:
                pass
                
        t_token = tenant_context.set(tenant_id)
        o_token = org_context.set(org_id)
        
        try:
            try:
                response = await call_next(request)
            except Exception:
                # Return a normal response so the outer CORS middleware can add
                # Access-Control-Allow-Origin. A bare 500 is reported by the
                # browser as "Failed to fetch" and the workspace stays blank.
                logger.exception("Unhandled error on %s", request.url.path)
                response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
            return response
        finally:
            tenant_context.reset(t_token)
            org_context.reset(o_token)
