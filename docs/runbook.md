 # AgentPay Guard — Operations Runbook

## 1. Overview

AgentPay Guard is a transaction safety and agentic-commerce gateway designed to protect AI-driven payment workflows.

Key capabilities:

- Buyer/seller authentication
- Transaction idempotency
- Negotiation orchestration
- Budget and velocity controls
- Deterministic risk evaluation
- Payment authorization/capture
- Webhook delivery with retries
- Tamper-evident audit events
- Prometheus metrics
- Structured JSON logging
- Health and readiness endpoints
- Docker deployment
- Automated CI quality checks

## 2. Start the Application

Start with Docker Compose:

```powershell
docker compose up -d