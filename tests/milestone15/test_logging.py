import json
import logging

from backend.app.security.logging import JsonFormatter, request_log_data


def test_json_formatter_outputs_structured_json():
    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="agentpay.guard",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test message",
        args=(),
        exc_info=None,
    )

    record.event = "test"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.23

    output = formatter.format(record)
    payload = json.loads(output)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "agentpay.guard"
    assert payload["message"] == "test message"
    assert payload["event"] == "test"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.23
    assert "timestamp" in payload


def test_request_log_data_contains_request_telemetry():
    import time

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
    assert data["duration_ms"] >= 0
