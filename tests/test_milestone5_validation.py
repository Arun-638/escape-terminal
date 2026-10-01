"""
Milestone 5 Verification Test Suite: State-Based Validation Engine
==================================================================
Validates:
1. Server-side state evaluation (validating results/tokens, not specific shell commands).
2. Door 1 validation with deterministic team-specific keys.
3. Door 2 validation with both full flag and decoded hexadecimal plaintexts.
4. Cross-team isolation (Team 1's key is rejected if submitted for Team 2).
5. Fast-path REST API validation (/api/terminal/validate).
6. End-to-end solve recording and score incrementation on CTFd.
"""

import sys
from pathlib import Path

# Add terminal-service and ctfd to Python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "ctfd"))

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.validation.validator import validator

from CTFd.models import Users, Teams, Challenges, Solves
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    register_user,
    login_as_user,
    gen_challenge,
    gen_flag,
)


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(scope="module")
def ctf_app():
    """Create test CTFd instance for scoring integration verification."""
    application = create_ctfd(
        ctf_name="🐧 ESCAPE THE TERMINAL",
        ctf_description="Zero-Cost Self-Hosted Linux Escape Room",
        name="admin",
        email="admin@escapetheterminal.lan",
        password="AdminSecurePassword123!",
        user_mode="teams",
    )
    yield application
    destroy_ctfd(application)


def test_01_door_1_state_validation():
    """Verify server-side Door 1 result validation."""
    team_answers = validator.get_team_answers(team_id=1)
    correct_flag = team_answers["door1"]["flag"]

    # Valid submission
    res_valid = validator.validate_door_submission(team_id=1, door_num=1, submission=correct_flag)
    assert res_valid["valid"] is True
    assert "Door 1 successfully unlocked" in res_valid["message"]

    # Invalid submission
    res_invalid = validator.validate_door_submission(team_id=1, door_num=1, submission="ESCAPE{WRONG_KEY}")
    assert res_invalid["valid"] is False

    print("\n[VERIFIED] 1. Door 1 server-side state validation verified.")


def test_02_door_2_hex_state_validation():
    """Verify Door 2 accepts either the formatted flag or decoded hex plaintext."""
    team_answers = validator.get_team_answers(team_id=1)
    correct_flag = team_answers["door2"]["flag"]
    correct_plaintext = team_answers["door2"]["plaintext"]

    # Valid with flag
    res_flag = validator.validate_door_submission(team_id=1, door_num=2, submission=correct_flag)
    assert res_flag["valid"] is True

    # Valid with raw decoded plaintext (flexible command resolution)
    res_plain = validator.validate_door_submission(team_id=1, door_num=2, submission=correct_plaintext)
    assert res_plain["valid"] is True

    # Invalid decoy
    res_decoy = validator.validate_door_submission(team_id=1, door_num=2, submission="DECOY-001")
    assert res_decoy["valid"] is False

    print("[VERIFIED] 2. Door 2 hexadecimal state validation verified.")


def test_03_cross_team_key_rejection():
    """Verify that Team 2's key cannot be used by Team 1."""
    team1_answers = validator.get_team_answers(team_id=1)
    team2_answers = validator.get_team_answers(team_id=2)

    team2_flag = team2_answers["door1"]["flag"]

    # Attempting to submit Team 2's flag for Team 1
    res = validator.validate_door_submission(team_id=1, door_num=1, submission=team2_flag)
    assert res["valid"] is False, "Cross-team flag sharing must be rejected!"
    print("[VERIFIED] 3. Cross-team key sharing is rejected.")


def test_04_http_validation_endpoint(api_client):
    """Verify /api/terminal/validate REST API endpoint."""
    t1_answers = validator.get_team_answers(team_id=1)
    t1_d1_flag = t1_answers["door1"]["flag"]

    payload = {
        "team_id": 1,
        "door": 1,
        "submission": t1_d1_flag
    }
    res = api_client.post("/api/terminal/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["door"] == 1
    print("[VERIFIED] 4. Validation REST API endpoint verified.")


def test_05_ctfd_scoring_integration(ctf_app):
    """Verify that validating a challenge records solve and increments score in CTFd."""
    with ctf_app.app_context():
        # Setup Door 1 challenge in CTFd with Team 1's expected flag
        t1_answers = validator.get_team_answers(team_id=1)
        t1_d1_flag = t1_answers["door1"]["flag"]

        chal = gen_challenge(
            ctf_app.db,
            name="Door 1 — Filesystem Investigation (State Validated)",
            value=100,
            category="Escape",
        )
        gen_flag(ctf_app.db, challenge_id=chal.id, content=t1_d1_flag)
        chal_id = chal.id

        # Register and setup Team 1
        register_user(ctf_app, name="solver_user", email="solver@college.lan", password="SolverPassword1!")
        user = Users.query.filter_by(name="solver_user").first()
        
        team = Teams(name="Team 01 Validation Squad", password="Password123!")
        team.captain_id = user.id
        team.members.append(user)
        user.team_id = team.id
        ctf_app.db.session.add(team)
        ctf_app.db.session.commit()

        # Submit via user session to CTFd
        with login_as_user(ctf_app, name="solver_user", password="SolverPassword1!") as client:
            res = client.post(
                "/api/v1/challenges/attempt",
                json={
                    "challenge_id": chal_id,
                    "submission": t1_d1_flag
                }
            )
            assert res.status_code == 200
            data = res.get_json()["data"]
            assert data["status"] == "correct"

        # Verify team score is 100
        refreshed_team = Teams.query.filter_by(name="Team 01 Validation Squad").first()
        assert refreshed_team.score == 100
        solve = Solves.query.filter_by(challenge_id=chal_id, team_id=refreshed_team.id).first()
        assert solve is not None
    print("[VERIFIED] 5. Successful validation reflects directly in CTFd scores and solve records.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
