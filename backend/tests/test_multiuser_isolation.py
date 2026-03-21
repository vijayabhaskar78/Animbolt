"""
Tests that data belonging to one user is not accessible by another user.
Covers: projects, scenes, and jobs endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    artifacts_path = tmp_path / "artifacts"
    artifacts_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("ARTIFACTS_DIR", artifacts_path.as_posix())
    monkeypatch.setenv("SIMULATE_RENDER", "true")
    monkeypatch.setenv("GROQ_API_KEY", "")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.db.base import Base
    from app.db.session import configure_engine

    engine, _ = configure_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    import app.api.routes.compositions as compositions_routes
    import app.api.routes.scenes as scenes_routes
    import app.api.routes.voiceovers as voiceovers_routes
    from app.main import app

    monkeypatch.setattr(scenes_routes.celery_app, "send_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(compositions_routes.celery_app, "send_task", lambda *args, **kwargs: None)
    monkeypatch.setattr(voiceovers_routes, "synthesize_tts", lambda text, voice, output_path: output_path.write_bytes(b"fake"))

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def _register_and_token(client: TestClient, email: str) -> str:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_user_cannot_access_other_users_project(client: TestClient) -> None:
    token_a = _register_and_token(client, "alice@example.com")
    token_b = _register_and_token(client, "bob@example.com")

    # Alice creates a project
    r = client.post("/api/v1/projects", headers=_headers(token_a), json={"title": "Alice Project", "description": ""})
    assert r.status_code == 201
    alice_project_id = r.json()["id"]

    # Bob cannot fetch Alice's project
    r = client.get(f"/api/v1/projects/{alice_project_id}", headers=_headers(token_b))
    assert r.status_code == 404

    # Bob's project list is empty
    r = client.get("/api/v1/projects", headers=_headers(token_b))
    assert r.status_code == 200
    assert r.json() == []


def test_user_cannot_access_other_users_scene_job(client: TestClient) -> None:
    token_a = _register_and_token(client, "alice2@example.com")
    token_b = _register_and_token(client, "bob2@example.com")

    # Alice creates a project and generates a scene
    r = client.post("/api/v1/projects", headers=_headers(token_a), json={"title": "Alice P", "description": ""})
    alice_project_id = r.json()["id"]

    r = client.post(
        "/api/v1/scenes/generate",
        headers=_headers(token_a),
        json={
            "project_id": alice_project_id,
            "prompt": "Show a cache miss flow",
            "style_preset": "technical-clean",
            "max_duration_sec": 5,
            "aspect_ratio": "16:9",
        },
    )
    assert r.status_code == 201
    alice_job_id = r.json()["preview_job_id"]
    alice_scene_id = r.json()["scene_id"]

    # Bob cannot fetch Alice's job
    r = client.get(f"/api/v1/jobs/{alice_job_id}", headers=_headers(token_b))
    assert r.status_code == 404

    # Bob cannot render-hd Alice's scene
    r = client.post(f"/api/v1/scenes/{alice_scene_id}/render-hd", headers=_headers(token_b))
    assert r.status_code == 404

    # Bob cannot regenerate Alice's scene
    r = client.post(
        f"/api/v1/scenes/{alice_scene_id}/regenerate",
        headers=_headers(token_b),
        json={"prompt": "modified", "style_preset": "minimal", "max_duration_sec": 5, "aspect_ratio": "16:9"},
    )
    assert r.status_code == 404


def test_user_cannot_export_other_users_project(client: TestClient) -> None:
    token_a = _register_and_token(client, "alice3@example.com")
    token_b = _register_and_token(client, "bob3@example.com")

    r = client.post("/api/v1/projects", headers=_headers(token_a), json={"title": "Alice Export P", "description": ""})
    alice_project_id = r.json()["id"]

    # Bob cannot export Alice's project
    r = client.post(
        f"/api/v1/compositions/{alice_project_id}/export",
        headers=_headers(token_b),
        json={"title": "Hijacked Export"},
    )
    assert r.status_code == 404


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    r = client.get("/api/v1/projects")
    assert r.status_code == 401

    r = client.post("/api/v1/scenes/generate", json={"project_id": "x", "prompt": "y"})
    assert r.status_code == 401
