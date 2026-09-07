"""App-level smoke test: the FastAPI app must boot and /health must respond
even when Qdrant/Ollama are not running (graceful-degradation contract)."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_responds_without_live_dependencies():
    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "app", "env", "deps"}
    assert set(body["deps"].keys()) == {"qdrant", "ollama"}
