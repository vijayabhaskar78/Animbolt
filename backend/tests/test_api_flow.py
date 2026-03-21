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


def test_auth_project_scene_and_jobs_flow(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"title": "Networking Basics", "description": "Test project"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    generate_response = client.post(
        "/api/v1/scenes/generate",
        headers=headers,
        json={
            "project_id": project_id,
            "prompt": "Client to server to database cache miss",
            "style_preset": "technical-clean",
            "max_duration_sec": 8,
            "aspect_ratio": "16:9",
        },
    )
    assert generate_response.status_code == 201
    payload = generate_response.json()
    assert payload["scene_id"]
    assert payload["preview_job_id"]

    job_response = client.get(f"/api/v1/jobs/{payload['preview_job_id']}", headers=headers)
    assert job_response.status_code == 200
    assert job_response.json()["job_type"] == "preview"

    tts_response = client.post(
        "/api/v1/voiceovers/tts",
        headers=headers,
        json={
            "project_id": project_id,
            "text": "Voice over text",
            "voice": "en-US-AriaNeural",
        },
    )
    assert tts_response.status_code == 201
    assert tts_response.json()["asset_id"]

    export_response = client.post(
        f"/api/v1/compositions/{project_id}/export",
        headers=headers,
        json={"title": "Main Composition"},
    )
    assert export_response.status_code == 202
    assert export_response.json()["job_id"]
