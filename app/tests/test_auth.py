import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_auth.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def registered_user(client):
    payload = {"email": "auth_test@sentinel.com", "password": "StrongPass123!"}
    client.post("/users/", json=payload)
    return payload

class TestUserRegistration:
    def test_register_new_user_returns_201(self, client):
        res = client.post("/users/", json={"email": "new_user@sentinel.com", "password": "SecurePass99!"})
        assert res.status_code == 201

    def test_register_response_contains_id_and_email(self, client):
        res = client.post("/users/", json={"email": "check_fields@sentinel.com", "password": "SecurePass99!"})
        data = res.json()
        assert "id" in data
        assert "email" in data
        assert "created_at" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email_returns_400(self, client, registered_user):
        res = client.post("/users/", json=registered_user)
        assert res.status_code == 400

    def test_register_invalid_email_returns_422(self, client):
        res = client.post("/users/", json={"email": "not-an-email", "password": "Pass123!"})
        assert res.status_code == 422

    def test_register_missing_password_returns_422(self, client):
        res = client.post("/users/", json={"email": "nopass@sentinel.com"})
        assert res.status_code == 422

class TestUserLogin:
    def test_login_valid_credentials_returns_200(self, client, registered_user):
        res = client.post("/users/login", data={"username": registered_user["email"], "password": registered_user["password"]})
        assert res.status_code == 200

    def test_login_returns_bearer_token(self, client, registered_user):
        res = client.post("/users/login", data={"username": registered_user["email"], "password": registered_user["password"]})
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_login_wrong_password_returns_400(self, client, registered_user):
        res = client.post("/users/login", data={"username": registered_user["email"], "password": "WrongPassword!"})
        assert res.status_code == 400

    def test_login_nonexistent_user_returns_400(self, client):
        res = client.post("/users/login", data={"username": "ghost@sentinel.com", "password": "anything"})
        assert res.status_code == 400

    def test_login_missing_fields_returns_422(self, client):
        res = client.post("/users/login", data={"username": "only@sentinel.com"})
        assert res.status_code == 422

class TestProtectedRoutes:
    def _get_token(self, client, registered_user):
        res = client.post("/users/login", data={"username": registered_user["email"], "password": registered_user["password"]})
        return res.json()["access_token"]

    def test_get_me_with_valid_token_returns_200(self, client, registered_user):
        token = self._get_token(client, registered_user)
        res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

    def test_get_me_without_token_returns_403(self, client):
        res = client.get("/users/me")
        assert res.status_code in (401, 403)

    def test_get_me_with_invalid_token_returns_401(self, client):
        res = client.get("/users/me", headers={"Authorization": "Bearer invalidtoken"})
        assert res.status_code == 401
