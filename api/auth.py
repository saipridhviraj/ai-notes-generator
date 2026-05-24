"""API key authentication dependency.

Usage in routes:
    from api.auth import require_api_key
    @router.post("/generate", dependencies=[Depends(require_api_key)])

Set APP_API_KEY in .env. If APP_API_KEY is not set, all requests are allowed
(dev convenience only — always set it in production).
"""
import os
import logging
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    expected = os.getenv("APP_API_KEY", "")
    if not expected:
        logger.warning("APP_API_KEY not set — running without auth (dev mode)")
        return "dev"

    if not api_key or api_key != expected:
        logger.warning("Unauthorized request — invalid or missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set X-API-Key header.",
        )

    return api_key
