"""
Milestone 6 Verification Test Suite: Multi-Team Concurrency & Sandbox Isolation
================================================================================
Validates:
1. Deterministic generation uniqueness across multiple teams (Teams 1 through 10).
2. Cross-team isolation: zero flag leakage or valid submissions between teams.
3. Multi-team container naming and session lifecycle tracking in ContainerManager.
4. Concurrent WebSocket sessions: no data leakage or crosstalk between teams.
5. High-concurrency REST validation: concurrent validation calls for multiple teams.
6. Team provisioning and database model integrity in CTFd.
"""

import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add paths for terminal-service and ctfd
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "ctfd"))

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.validation.validator import validator
from app.containers.manager import container_manager
from app.terminal.session import session_manager

from CTFd.models import Users, Teams, Challenges, Solves
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    register_user,
    login_as_user,
)


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(scope="module")
def ctf_app():
    """Create test CTFd instance for multi-team testing."""
    application = create_ctfd(
        ctf_name="🐧 ESCAPE THE TERMINAL",
        ctf_description="Multi-Team Isolation Verification",
        name="admin",
        email="admin@escapetheterminal.lan",
        password="AdminSecurePassword123!",
        user_mode="teams",
    )
    yield application
    destroy_ctfd(application)


def test_01_multi_team_flag_uniqueness():
    """Verify that 10 distinct teams receive 10 completely unique challenge flags."""
    team_count = 10
    door1_flags = set()
    door2_flags = set()

    for team_id in range(1, team_count + 1):
        answers = validator.get_team_answers(team_id)
        d1_flag = answers["door1"]["flag"]
        d2_flag = answers["door2"]["flag"]

        assert d1_flag.startswith("ESCAPE{")
        assert d2_flag.startswith("ESCAPE{")

        # Must not have collided with any prior team
        assert d1_flag not in door1_flags, f"Collision detected for Team {team_id} Door 1!"
        assert d2_flag not in door2_flags, f"Collision detected for Team {team_id} Door 2!"

        door1_flags.add(d1_flag)
        door2_flags.add(d2_flag)

    assert len(door1_flags) == team_count
    assert len(door2_flags) == team_count


def test_02_cross_team_validation_matrix():
    """Verify that submitting Team A's solution under Team B's session fails for all combinations."""
    teams_to_test = [1, 2, 3, 5, 8]
    answers = {t: validator.get_team_answers(t) for t in teams_to_test}

    for team_a in teams_to_test:
        for team_b in teams_to_test:
            sol_a_d1 = answers[team_a]["door1"]["flag"]
            res = validator.validate_door_submission(
                team_id=team_b,
                door_num=1,
                submission=sol_a_d1
            )
            if team_a == team_b:
                assert res["valid"] is True, f"Team {team_b} failed to validate its own answer"
            else:
                assert res["valid"] is False, f"Team {team_b} improperly accepted Team {team_a}'s answer!"


def test_03_container_manager_multi_team_lifecycle():
    """Verify ContainerManager correctly formats and manages isolated containers for multiple teams."""
    teams = [1, 5, 12, 40]
    expected_names = {
        1: "escape-team-01",
        5: "escape-team-05",
        12: "escape-team-12",
        40: "escape-team-40",
    }

    for t_id, exp_name in expected_names.items():
        assert container_manager.get_container_name(t_id) == exp_name

    # Create / get containers for teams
    for t_id in teams:
        c_info = container_manager.get_or_create_team_container(t_id)
        assert c_info["team_id"] == t_id
        assert c_info["name"] == expected_names[t_id]
        assert c_info["status"] == "running"

    # Stop container test
    for t_id in teams:
        res = container_manager.stop_team_container(t_id)
        assert res is True


def test_04_concurrent_websocket_sessions(api_client):
    """Verify that multiple concurrent team WebSocket terminal sessions do not leak data."""
    import json

    # Connect Team 1 and Team 2 simultaneously
    with api_client.websocket_connect("/ws/terminal/1") as ws1:
        with api_client.websocket_connect("/ws/terminal/2") as ws2:
            init1 = ws1.receive_text()
            init2 = ws2.receive_text()

            assert "ESCAPE THE TERMINAL" in init1
            assert "ESCAPE THE TERMINAL" in init2

            # Team 1 sends command 'pwd'
            ws1.send_text(json.dumps({"type": "input", "data": "pwd\r"}))
            resp1 = ""
            for _ in range(25):
                chunk = ws1.receive_text()
                resp1 += chunk
                if "/home/player" in resp1:
                    break
            assert "/home/player" in resp1

            # Team 2 sends command 'ls'
            ws2.send_text(json.dumps({"type": "input", "data": "ls\r"}))
            resp2 = ""
            for _ in range(25):
                chunk = ws2.receive_text()
                resp2 += chunk
                if "README.txt" in resp2:
                    break
            assert "README.txt" in resp2
            # Verify Team 2 did NOT receive Team 1's pwd output
            assert "/home/player" not in resp2


def test_05_concurrent_rest_validation(api_client):
    """Verify high-concurrency REST validation without thread contention or state corruption."""
    def validate_team(team_id: int):
        answers = validator.get_team_answers(team_id)
        valid_flag = answers["door1"]["flag"]

        # Valid call
        res_ok = api_client.post("/api/terminal/validate", json={
            "team_id": team_id,
            "door": 1,
            "submission": valid_flag,
        })
        # Invalid call with bogus flag
        res_fail = api_client.post("/api/terminal/validate", json={
            "team_id": team_id,
            "door": 1,
            "submission": "ESCAPE{INVALID_WRONG_FLAG}",
        })
        return res_ok.json(), res_fail.json()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(validate_team, t) for t in range(1, 11)]
        results = [f.result() for f in futures]

    for ok_json, fail_json in results:
        assert ok_json["valid"] is True
        assert "unlocked" in ok_json["message"]
        assert fail_json["valid"] is False


def test_06_ctfd_team_creation_and_isolation(ctf_app):
    """Verify CTFd team registration and membership isolation in the database."""
    with ctf_app.app_context():
        # Create 3 teams in CTFd
        team_data = [
            ("Team CyberPhantoms", "team01", "team01@escape.lan", "Pass01!"),
            ("Team BinaryBrawlers", "team02", "team02@escape.lan", "Pass02!"),
            ("Team KernelKnights", "team03", "team03@escape.lan", "Pass03!"),
        ]

        created_teams = []
        for team_name, username, email, pwd in team_data:
            user = Users(name=username, email=email, password=pwd)
            ctf_app.db.session.add(user)
            ctf_app.db.session.commit()

            team = Teams(name=team_name, email=email, password=pwd)
            team.captain_id = user.id
            team.members.append(user)
            ctf_app.db.session.add(team)
            ctf_app.db.session.commit()

            created_teams.append(team.id)

        # Verify all 3 teams have distinct IDs and isolated user membership
        assert len(set(created_teams)) == 3
        for tid in created_teams:
            t = Teams.query.filter_by(id=tid).first()
            assert len(t.members) == 1
            assert t.captain_id == t.members[0].id
