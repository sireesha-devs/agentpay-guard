from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format application logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event"):
            payload["event"] = record.event

        if hasattr(record, "method"):
            payload["method"] = record.method

        if hasattr(record, "path"):
            payload["path"] = record.path

        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure structured JSON logging for the application."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def request_log_data(
    method: str,
    path: str,
    status_code: int,
    start_time: float,
) -> dict[str, Any]:
    """Build structured request telemetry."""
    return {
        "event": "http_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(
            (time.perf_counter() - start_time) * 1000,
            2,
        ),
    }