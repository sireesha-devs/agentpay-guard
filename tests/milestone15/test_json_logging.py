import json
import logging
import time

from backend.app.security.logging import JsonFormatter, request_log_data


def test_json_formatter_outputs_valid_json():
    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="agentpay.guard",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Transaction completed",
        args=(),
        exc_info=None,
    )

    record.event = "transaction_completed"
    record.method = "POST"
    record.path = "/transactions"
    record.status_code = 200
    record.duration_ms = 12.5

    output = formatter.format(record)
    payload = json.loads(output)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "agentpay.guard"
    assert payload["message"] == "Transaction completed"
    assert payload["event"] == "transaction_completed"
    assert payload["method"] == "POST"
    assert payload["path"] == "/transactions"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.5
    assert "timestamp" in payload


def test_request_log_data_contains_structured_fields():
    start_time = time.perf_counter()

    data = request_log_data(
        method="GET",
        path="/health",
        status_code=200,
        start_time=start_time,
    )

    assert data["event"] == "http_request"
    assert data["method"] == "GET"
    assert data["path"] == "/health"
    assert data["status_code"] == 200
    assert isinstance(data["duration_ms"], float)