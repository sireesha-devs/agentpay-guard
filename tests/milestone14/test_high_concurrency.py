from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from backend.app.idempotency.store import idempotency_store
from backend.app.main import app


client = TestClient(app)


def valid_payload() -> dict[str, object]:
    return {
        "transaction_id": "concurrent-transaction-1",
        "buyer_id": "buyer-1",
        "quantity": 2,
        "max_budget": 1000.0,
        "currency": "INR",
        "minimum_refund_days": 7,
        "seller_id": "seller-1",
        "unit_price": 400.0,
        "seller_currency": "INR",
        "refund_days": 7,
        "terms": "Seven-day return policy",
    }

def test_rate_limiter_isolated_per_api_key_under_burst():
    """
    A burst from one API key must be throttled independently
    from another API key.
    """
    from backend.app.security.rate_limit import rate_limiter

    rate_limiter.reset()

    def send_request(api_key: str, index: int):
        headers = {
            "X-API-Key": api_key,
            "Idempotency-Key": f"m14-rate-{api_key}-{index}",
        }

        payload = valid_payload()
        payload["transaction_id"] = f"m14-rate-{api_key}-{index}"

        return client.post(
            "/transactions",
            json=payload,
            headers=headers,
        )

    # Send 31 concurrent requests for buyer-demo-key.
    with ThreadPoolExecutor(max_workers=31) as executor:
        buyer_responses = list(
            executor.map(
                lambda index: send_request(
                    "buyer-demo-key",
                    index,
                ),
                range(31),
            )
        )

    buyer_success = [
        response
        for response in buyer_responses
        if response.status_code == 200
    ]

    buyer_throttled = [
        response
        for response in buyer_responses
        if response.status_code == 429
    ]

    assert len(buyer_success) == 30
    assert len(buyer_throttled) == 1

    # A different API key must have its own independent quota.
    response = send_request("admin-demo-key", 0)

    assert response.status_code == 200

def test_concurrent_transaction_requests_are_idempotent():
    """
    Multiple concurrent requests using the same idempotency key
    must result in one logical transaction.
    """
    idempotency_store.clear()

    headers = {
        "X-API-Key": "buyer-demo-key",
        "Idempotency-Key": "m14-concurrent-transaction",
    }

    def send_request():
        return client.post(
            "/transactions",
            json=valid_payload(),
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(
            executor.map(
                lambda _: send_request(),
                range(10),
            )
        )

    successful = [
        response
        for response in responses
        if response.status_code == 200
    ]

    conflicts = [
        response
        for response in responses
        if response.status_code == 409
    ]

    assert len(successful) >= 1
    assert len(successful) + len(conflicts) == 10

    # All successful requests must return the same cached result.
    successful_bodies = [
        response.json()
        for response in successful
    ]

    assert all(
        body == successful_bodies[0]
        for body in successful_bodies
    )

    # Verify the idempotency record completed successfully.
    record = idempotency_store.get(
        "transaction:buyer-demo-key:m14-concurrent-transaction"
    )

    assert record is not None
    assert record.status == "COMPLETED"