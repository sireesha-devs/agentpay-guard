from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """
    Simple fixed-window/sliding-window rate limiter.

    Suitable for this local/demo deployment.
    A production multi-instance deployment should replace this
    with a Redis-backed implementation.
    """

    def __init__(
        self,
        limit: int = 30,
        window_seconds: int = 60,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={
                        "Retry-After": str(self.window_seconds),
                    },
                )

            timestamps.append(now)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


rate_limiter = InMemoryRateLimiter(
    limit=30,
    window_seconds=60,
)


def rate_limit_request(request: Request) -> None:
    """
    Apply rate limiting using API key when available,
    otherwise fall back to client IP.
    """
    api_key = request.headers.get("X-API-Key")

    if api_key:
        client_key = f"api-key:{api_key}"
    else:
        client_host = request.client.host if request.client else "unknown"
        client_key = f"ip:{client_host}"

    rate_limiter.check(client_key)