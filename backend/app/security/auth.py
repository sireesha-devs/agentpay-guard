from __future__ import annotations

import os
from typing import Final

from fastapi import Header, HTTPException, status


DEFAULT_API_KEYS: Final[dict[str, str]] = {
    "buyer-demo-key": "buyer",
    "seller-demo-key": "seller",
    "admin-demo-key": "admin",
}


def _api_keys() -> dict[str, str]:
    """Return configured API keys mapped to their roles."""
    return {
        os.getenv("AGENTPAY_BUYER_API_KEY", "buyer-demo-key"): "buyer",
        os.getenv("AGENTPAY_SELLER_API_KEY", "seller-demo-key"): "seller",
        os.getenv("AGENTPAY_ADMIN_API_KEY", "admin-demo-key"): "admin",
    }


def authenticate(api_key: str | None, required_role: str | None = None) -> str:
    """Validate an API key and optionally enforce a role."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    role = _api_keys().get(api_key)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if required_role is not None and role not in {required_role, "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized for this endpoint",
        )

    return role


def require_role(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    required_role: str | None = None,
) -> str:
    """FastAPI dependency for API-key authentication and RBAC."""
    return authenticate(x_api_key, required_role)
