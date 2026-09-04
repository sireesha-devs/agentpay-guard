# AgentPay Guard

> AI-native transaction safety and agentic commerce gateway.

AgentPay Guard is a production-oriented payment safety layer for AI-driven commerce. It evaluates transactions through deterministic policy and risk controls before allowing payment capture.

##  Core Capabilities

- Buyer, seller, and admin authentication
- Idempotent transaction processing
- Buyer/seller negotiation orchestration
- Budget enforcement
- Velocity controls
- Deterministic risk guard
- Webhook delivery with retry handling
- Tamper-evident audit chain
- Prometheus metrics
- Structured JSON logging
- Health and readiness endpoints
- Docker Compose deployment
- Automated tests and CI quality checks

## Architecture

Client / AI Agent
        |
        v
Authentication
        |
        v
Idempotency Layer
        |
        v
Negotiation
        |
        v
Transaction Guard Pipeline
        |
   +----+----+
   |    |    |
   v    v    v
Budget Velocity Risk
   |    |    |
   +----+----+
        |
        v
Policy Evaluation
        |
        v
Payment Capture
        |
   +----+----+
   |         |
   v         v
Webhook    Audit
Delivery   Chain

Observability
  - Prometheus Metrics
  - Structured JSON Logs
  - Health and Readiness
