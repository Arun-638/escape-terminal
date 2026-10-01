"""
Milestone 7 Verification Test Suite: Security Hardening & Abuse Prevention
===========================================================================
Validates:
1. Docker Sandbox container configuration (non-root UID 1001, cap_drop ALL, no-new-privileges).
2. Resource quota specifications (256MB RAM, 0.5 CPU, 100 PIDs fork bomb protection).
3. Complete network isolation (network_mode: none).
4. Rate limiting on validation API (sliding-window: 15 req/min -> HTTP 429).
5. Input boundary enforcement (door 1-6, positive team_id, payload length limits).
6. Strict IDOR protection between different teams.
"""

import sys
from pathlib import Path

# Add paths for terminal-service and ctfd
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "ctfd"))

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.config import settings
from app.containers.manager import container_manager
from app.security.rate_limiter import validation_limiter
from app.security.auth import auth_manager
from app.validation.validator import validator


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter before each test."""
    validation_limiter.reset()
    yield
    validation_limiter.reset()


def test_01_sandbox_container_security_specs():
    """Verify that container manager enforces all mandatory security constraints."""
    # Check default config settings
    assert settings.CONTAINER_CPU == 0.5
    assert settings.CONTAINER_MEMORY == "256m"
    assert settings.CONTAINER_PIDS == 100

    # Inspect Docker run arguments specified in ContainerManager._create_container
    import inspect
    source = inspect.getsource(container_manager._create_container)

    # 1. Non-root user
    assert 'user="player"' in source or "user='player'" in source
    # 2. Network isolation
    assert 'network_mode="none"' in source or "network_mode='none'" in source
    # 3. No new privileges
    assert "no-new-privileges:true" in source
    # 4. Capabilities drop
    assert 'cap_drop=["ALL"]' in source or "cap_drop=['ALL']" in source
    # 5. PIDs limit for fork-bomb mitigation
    assert "pids_limit=settings.CONTAINER_PIDS" in source
    # 6. Memory and CPU limits
    assert "mem_limit=settings.CONTAINER_MEMORY" in source
    assert "cpu_quota=cpu_quota" in source


def test_02_dockerfile_and_entrypoint_hardening():
    """Verify Dockerfile and entrypoint script follow least-privilege standards."""
    dockerfile_path = repo_root / "challenge-environment" / "Dockerfile"
    entrypoint_path = repo_root / "challenge-environment" / "scripts" / "entrypoint.sh"

    assert dockerfile_path.exists()
    assert entrypoint_path.exists()

    df_content = dockerfile_path.read_text(encoding="utf-8")
    ep_content = entrypoint_path.read_text(encoding="utf-8")

    # Dockerfile creates unprivileged UID 1001 user
    assert "useradd -u 1001" in df_content or "-u 1001" in df_content
    # Strips SUID/SGID bits
    assert "chmod a-s" in df_content or "perm /6000" in df_content

    # Entrypoint locks answers directory to root (chmod 700 / 600)
    assert "chmod 700 /var/run/escape" in ep_content
    assert "chmod 600 /var/run/escape/answers.json" in ep_content


def test_03_validation_api_rate_limiting(api_client):
    """Verify sliding-window rate limiter blocks excessive submissions with HTTP 429."""
    team_id = 99
    answers = validator.get_team_answers(team_id)
    flag = answers["door1"]["flag"]

    # Make 15 requests (the allowed max in 1 minute)
    for i in range(15):
        resp = api_client.post("/api/terminal/validate", json={
            "team_id": team_id,
            "door": 1,
            "submission": flag
        })
        assert resp.status_code == 200, f"Request {i+1} should be permitted"

    # The 16th request must trigger HTTP 429 Too Many Requests
    blocked_resp = api_client.post("/api/terminal/validate", json={
        "team_id": team_id,
        "door": 1,
        "submission": flag
    })
    assert blocked_resp.status_code == 429
    assert "Rate limit exceeded" in blocked_resp.json()["detail"]
    assert "Retry-After" in blocked_resp.headers

    # Other teams must NOT be affected by Team 99's rate limiting
    other_team_resp = api_client.post("/api/terminal/validate", json={
        "team_id": 100,
        "door": 1,
        "submission": validator.get_team_answers(100)["door1"]["flag"]
    })
    assert other_team_resp.status_code == 200


def test_04_input_boundary_validation(api_client):
    """Verify strict validation of parameters against injection and payload floods."""
    # Test invalid door numbers (< 1 or > 6)
    for bad_door in [0, 7, -1, 99]:
        resp = api_client.post("/api/terminal/validate", json={
            "team_id": 1,
            "door": bad_door,
            "submission": "ESCAPE{TEST}"
        })
        assert resp.status_code == 400
        assert "door must be an integer between 1 and 6" in resp.json()["detail"]

    # Test invalid team_id
    for bad_team in [0, -5, 2000]:
        resp = api_client.post("/api/terminal/validate", json={
            "team_id": bad_team,
            "door": 1,
            "submission": "ESCAPE{TEST}"
        })
        assert resp.status_code == 400
        assert "team_id" in resp.json()["detail"]

    # Test oversized submission payload (> 256 chars)
    giant_payload = "A" * 300
    resp = api_client.post("/api/terminal/validate", json={
        "team_id": 1,
        "door": 1,
        "submission": giant_payload
    })
    assert resp.status_code == 400
    assert "submission must be between 1 and 256 characters" in resp.json()["detail"]


def test_05_anti_idor_auth_enforcement():
    """Verify that auth_manager strictly blocks unauthorized cross-team access."""
    # Test token impersonation
    assert auth_manager.authorize_team_access("test-token-team-1", requested_team_id=1) is True
    assert auth_manager.authorize_team_access("test-token-team-1", requested_team_id=2) is False

    # Empty or missing session
    assert auth_manager.authorize_team_access(None, requested_team_id=1) is False
    assert auth_manager.authorize_team_access("", requested_team_id=1) is False
