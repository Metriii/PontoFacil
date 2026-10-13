import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_retorna_200():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "tesseract" in data


def test_health_tesseract_booleano():
    resp = client.get("/api/health")
    data = resp.json()
    assert isinstance(data["tesseract"], bool)
