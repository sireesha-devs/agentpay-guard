from fastapi import FastAPI


app = FastAPI(title="AgentPay Guard API")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}
