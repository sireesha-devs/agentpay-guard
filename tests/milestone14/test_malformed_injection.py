

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def valid_payload() -> dict[str, object]:
    return {
        "transaction_id": "m14-security-1",
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


def post_transaction(payload: dict[str, object], key: str):
    return client.post(
        "/transactions",
        json=payload,
        headers={
            "X-API-Key": "buyer-demo-key",
            "Idempotency-Key": key,
        },
    )


def test_nan_amount_is_rejected():
    payload = valid_payload()
    payload["unit_price"] = "NaN"

    response = post_transaction(payload, "m14-nan")

    assert response.status_code == 422


def test_infinity_amount_is_rejected():
    payload = valid_payload()
    payload["unit_price"] = "Infinity"

    response = post_transaction(payload, "m14-infinity")

    assert response.status_code == 422


def test_negative_budget_is_rejected():
    payload = valid_payload()
    payload["max_budget"] = -100.0

    response = post_transaction(payload, "m14-negative-budget")

    assert response.status_code == 422


def test_extra_fields_are_rejected():
    payload = valid_payload()
    payload["unexpected_field"] = "malicious-data"

    response = post_transaction(payload, "m14-extra-field")

    assert response.status_code == 422


def test_nested_object_in_string_field_is_rejected():
    payload = valid_payload()
    payload["terms"] = {
        "level1": {
            "level2": {
                "level3": "unexpected-object",
            }
        }
    }

    response = post_transaction(payload, "m14-nested-json")

    assert response.status_code == 422


def test_invalid_currency_is_rejected():
    payload = valid_payload()
    payload["currency"] = "INR<script>alert(1)</script>"

    response = post_transaction(payload, "m14-script-currency")

    assert response.status_code == 422


def test_invalid_quantity_is_rejected():
    payload = valid_payload()
    payload["quantity"] = 0

    response = post_transaction(payload, "m14-zero-quantity")

    assert response.status_code == 422