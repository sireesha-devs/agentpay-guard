from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agentpay.guard")


def _perform_transaction_post_processing(
    transaction_id: str,
    result: Any,
) -> None:
    logger.info(
        "Transaction post-processing completed",
        extra={
            "event": "transaction_post_processing",
            "transaction_id": transaction_id,
            "payment_status": getattr(result, "payment_status", None),
        },
    )


def process_transaction_post_processing(
    transaction_id: str,
    result: Any,
) -> None:
    """
    Perform non-critical post-processing safely.

    Failures here must never affect the primary transaction request.
    """
    try:
        _perform_transaction_post_processing(transaction_id, result)
    except Exception:
        logger.exception(
            "Transaction post-processing failed",
            extra={
                "event": "transaction_post_processing_failed",
                "transaction_id": transaction_id,
            },
        )