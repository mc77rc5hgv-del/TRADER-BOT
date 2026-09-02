from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app
from app.webapp.router import get_validated_init_data


def test_auth_rejects_missing_header() -> None:
    client = TestClient(app)
    response = client.post("/webapp/auth")
    assert response.status_code == 401


async def test_auth_creates_and_returns_user(db_session) -> None:
    async def fake_init_data(authorization=None):
        return {"user": {"id": 777, "username": "webapp_tester"}}

    async def fake_session():
        yield db_session

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    try:
        client = TestClient(app)
        response = client.post("/webapp/auth", headers={"Authorization": "tma fake"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["user"]["telegram_id"] == 777
    assert body["user"]["username"] == "webapp_tester"


async def test_auth_missing_user_in_init_data_returns_400(db_session) -> None:
    async def fake_init_data(authorization=None):
        return {}

    async def fake_session():
        yield db_session

    app.dependency_overrides[get_validated_init_data] = fake_init_data
    app.dependency_overrides[get_session] = fake_session
    try:
        client = TestClient(app)
        response = client.post("/webapp/auth", headers={"Authorization": "tma fake"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
