from prometheus_client import Counter, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "agentpay_http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "agentpay_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

TRANSACTIONS_TOTAL = Counter(
    "agentpay_transactions_total",
    "Total transaction outcomes",
    ["status"],
)