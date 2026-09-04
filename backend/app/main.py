from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from backend.app.api import router
from backend.app.security.logging import (
    configure_logging,
    request_log_data,
)
from backend.app.security.rate_limit import rate_limiter
from backend.app.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
)


configure_logging()

logger = logging.getLogger("agentpay.guard")

app = FastAPI(
    title="AgentPay Guard API",
    version="1.0.0",
)

app.include_router(router)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Global API security middleware.

    - Rate limits requests.
    - Produces structured operational/security logs.
    - Keeps authentication available at endpoint level through X-API-Key.
    """
    start_time = time.perf_counter()

    # Keep health checks available for monitoring.
    if request.url.path not in {"/health", "/readiness"}:
        try:
            api_key = request.headers.get("X-API-Key")

            if api_key:
                limiter_key = f"api-key:{api_key}"
            else:
                client_host = (
                    request.client.host
                    if request.client
                    else "unknown"
                )
                limiter_key = f"ip:{client_host}"

            rate_limiter.check(limiter_key)

        except Exception as exc:
            status_code = (
                exc.status_code
                if hasattr(exc, "status_code")
                else 500
            )

            logger.warning(
                "Security middleware rejected request",
                extra={
                    "event": "security_rejection",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            )

            if hasattr(exc, "detail"):
                return JSONResponse(
                    status_code=status_code,
                    content={"detail": exc.detail},
                    headers=getattr(exc, "headers", None),
                )

            raise

    response = await call_next(request)
    duration = time.perf_counter() - start_time

    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()

    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=request.method,
        path=request.url.path,
    ).observe(duration)

    logger.info(
        "HTTP request completed",
        extra=request_log_data(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            start_time=start_time,
        ),
    )

    return response


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}

@app.get("/readiness")
def readiness_check() -> dict[str, str]:
    """Return whether the API is ready to process requests."""
    return {"status": "ready"}

@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
