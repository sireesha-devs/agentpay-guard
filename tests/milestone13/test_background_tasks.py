from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_transaction_schedules_background_task():
    payload = {
        "transaction_id": "m13-background-test",
        "buyer_id": "buyer-1",
        "quantity": 1,
        "max_budget": 1000.0,
        "currency": "USD",
        "minimum_refund_days": 7,
        "seller_id": "seller-1",
        "unit_price": 100.0,
        "seller_currency": "USD",
        "refund_days": 14,
        "terms": "Standard terms",
        "max_rounds": 3,
    }

    with patch(
        "backend.app.api.transactions.process_transaction_post_processing"
    ) as mock_task:
        response = client.post(
            "/transactions",
            json=payload,
            headers={
                "X-API-Key": "buyer-demo-key",
                "Idempotency-Key": "m13-background-test-key",
            },
        )

    assert response.status_code == 200
    mock_task.assert_called_once()