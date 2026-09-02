from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agentpay.guard")


def process_transaction_post_processing(
    transaction_id: str,
    result: Any,
) -> None:
    """
    Perform non-critical post-processing after a transaction completes.

    This function intentionally does not participate in the critical
    payment/authorization path.
    """
    logger.info(
        "Transaction post-processing completed",
        extra={
            "event": "transaction_post_processing",
            "transaction_id": transaction_id,
            "payment_status": getattr(result, "payment_status", None),
        },
    )