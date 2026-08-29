from fastapi import FastAPI

from backend.app.api import router


app = FastAPI(title="AgentPay Guard API")
app.include_router(router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}
