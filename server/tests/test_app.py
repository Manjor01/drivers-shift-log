from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_exposes_openapi() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Driver Shift Diary"
