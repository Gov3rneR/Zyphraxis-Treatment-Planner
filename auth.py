"""
auth.py - API-key authentication for Zyphraxis.

Current implementation uses static keys for simplicity.
Replace VALID_API_KEYS with a database lookup or OAuth/JWT flow
before going to production.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, status

# ---------------------------------------------------------------------------
# Key store
# In production: load from environment variables, a secrets manager,
# or a database. Never hard-code production keys in source.
# ---------------------------------------------------------------------------

_ENV_KEY = os.getenv("ZYPHRAXIS_API_KEY")

VALID_API_KEYS: dict[str, dict] = {
    "zyphraxis-demo-key": {
        "name": "Demo User",
        "tier": "demo",
        "rate_limit_rph": 100,
    },
}

if _ENV_KEY:
    VALID_API_KEYS[_ENV_KEY] = {
        "name": "Env-Injected User",
        "tier": "production",
        "rate_limit_rph": 10_000,
    }


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def verify_api_key(x_api_key: str = Header(...)) -> dict:
    """
    FastAPI dependency for protected routes.
    Validates the X-API-Key request header and returns key metadata.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Add an X-API-Key header to your request.",
        )
    key_data = VALID_API_KEYS.get(x_api_key)
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return {"key": x_api_key, "name": key_data["name"], "tier": key_data["tier"]}


# ---------------------------------------------------------------------------
# Rate-limiting placeholder
# ---------------------------------------------------------------------------

def check_rate_limit(api_key_data: dict) -> bool:
    """
    Placeholder for Redis-backed rate limiting.
    Currently a no-op — implement with slowapi or a Redis counter
    before deploying to production.
    """
    # TODO: implement with slowapi or redis-py
    return True
