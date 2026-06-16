from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/health", tags=["system"])
def check_health():
    """
    v2 API Health check endpoint.
    """
    return {
        "status": "healthy",
        "api_version": "v2",
        "enterprise_hardened": True
    }
