import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str = "mia.agent") -> str:
    response = client.post("/auth/login", data={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_and_dashboard(client: TestClient) -> None:
    token = login(client)
    response = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "mia.agent"
    assert "conversion_rate" in data["metrics"]


def test_manager_benchmarks(client: TestClient) -> None:
    token = login(client, "olivia.manager")
    response = client.get("/manager/benchmarks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_ai_fallback_for_appraisal(client: TestClient) -> None:
    token = login(client)
    appraisals = client.get("/appraisals", headers={"Authorization": f"Bearer {token}"}).json()
    response = client.post(f"/appraisals/{appraisals[0]['id']}/ai/prep_brief", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "appraisal" in response.json()["content"].lower()
