import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.base import tenant_context, org_context

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Establish a clean request context without trusting client tenant headers.

    Authenticated tenant context is bound by get_current_user after the bearer
    token is validated and the user record is loaded. Client-provided tenant
    headers are not an identity mechanism and must never establish database
    tenant scope by themselves.
    """

    async def dispatch(self, request: Request, call_next):
        # Start from a clean context. Authentication dependencies may bind the
        # verified tenant/org for the duration of the request.
        t_token = tenant_context.set(None)
        o_token = org_context.set(None)

        try:
            try:
                response = await call_next(request)
            except Exception:
                # Keep a generic response so internal exceptions and sensitive
                # connection details are not returned to the client.
                logger.exception("Unhandled error on %s", request.url.path)
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal Server Error"},
                )
            return response
        finally:
            tenant_context.reset(t_token)
            org_context.reset(o_token)
