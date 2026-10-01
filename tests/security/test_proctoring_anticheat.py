"""
Anti-Cheat & Proctoring Verification Test Suite
===============================================
Validates:
1. Client-reported proctor violations (tab switch, window blur, fullscreen exit).
2. Warning strike progression (1/3, 2/3, 3/3).
3. Automatic disqualification upon 3rd strike.
4. Flag submission blocking for disqualified teams (HTTP 403).
5. WebSocket connection blocking for disqualified teams (code 4008).
6. Scoreboard ranking reflection (disqualified teams flagged and sorted to bottom).
7. Admin pardon functionality (resets strikes to 0 and lifts disqualification).
"""

import sys
from pathlib import Path

# Add paths for terminal-service and ctfd
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "ctfd"))

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.competition.proctor import proctor_manager
from app.competition.scoreboard import scoreboard_manager
from app.validation.validator import validator


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_proctor():
    proctor_manager.reset_all()
    scoreboard_manager.reset()
    yield
    proctor_manager.reset_all()
    scoreboard_manager.reset()


def test_01_proctor_strike_progression(api_client):
    """Verify that reporting violations increments strikes and triggers disqualification on strike 3."""
    team_id = 15

    # Initial status: 0 strikes
    status0 = api_client.get(f"/api/terminal/proctor/{team_id}").json()
    assert status0["warnings"] == 0
    assert status0["disqualified"] is False

    # Strike 1: Tab switch
    res1 = api_client.post("/api/terminal/proctor/violation", json={
        "team_id": team_id,
        "reason": "Tab switch or browser minimized"
    }).json()
    assert res1["warnings"] == 1
    assert res1["disqualified"] is False

    # Strike 2: Window blur
    res2 = api_client.post("/api/terminal/proctor/violation", json={
        "team_id": team_id,
        "reason": "Window lost focus"
    }).json()
    assert res2["warnings"] == 2
    assert res2["disqualified"] is False

    # Strike 3: Fullscreen exit -> AUTOMATIC DISQUALIFICATION
    res3 = api_client.post("/api/terminal/proctor/violation", json={
        "team_id": team_id,
        "reason": "Exited fullscreen locked mode"
    }).json()
    assert res3["warnings"] == 3
    assert res3["disqualified"] is True


def test_02_disqualified_team_cannot_submit_flags(api_client):
    """Verify that a disqualified team has all flag submission capabilities revoked."""
    team_id = 16
    answers = validator.get_team_answers(team_id)
    correct_flag = answers["door1"]["flag"]

    # Incur 3 strikes
    for i in range(3):
        api_client.post("/api/terminal/proctor/violation", json={
            "team_id": team_id,
            "reason": f"Strike {i+1}"
        })

    # Attempt to submit valid flag -> Must be rejected with HTTP 403 Forbidden
    sub_res = api_client.post("/api/terminal/validate", json={
        "team_id": team_id,
        "door": 1,
        "submission": correct_flag
    })
    assert sub_res.status_code == 403
    assert "DISQUALIFIED" in sub_res.json()["detail"]


def test_03_disqualified_team_websocket_blocked(api_client):
    """Verify that WebSocket gateway blocks connection for disqualified teams with code 4008."""
    team_id = 17

    # Disqualify team
    for i in range(3):
        proctor_manager.record_violation(team_id, "tab_switch")

    # Connect WebSocket -> Expect error message and disconnect
    with api_client.websocket_connect(f"/ws/terminal/{team_id}") as ws:
        msg = ws.receive_text()
        assert "[DISQUALIFIED]" in msg
        with pytest.raises(WebSocketDisconnect) as excinfo:
            ws.receive_text()
        assert excinfo.value.code == 4008


def test_04_scoreboard_reflects_disqualification():
    """Verify scoreboard sorts disqualified teams to the bottom and flags their status."""
    team_active = 21
    team_cheater = 22

    # Both solve Door 1
    scoreboard_manager.record_solve(team_id=team_active, team_name="HonestTeam", door_num=1, points=100)
    scoreboard_manager.record_solve(team_id=team_cheater, team_name="CheaterTeam", door_num=1, points=100)
    # Cheater also solved Door 2
    scoreboard_manager.record_solve(team_id=team_cheater, team_name="CheaterTeam", door_num=2, points=100)

    # Disqualify CheaterTeam
    for _ in range(3):
        proctor_manager.record_violation(team_cheater, "tab_switch")

    leaderboard = scoreboard_manager.get_leaderboard()

    # HonestTeam must be Rank 1 even with fewer points because CheaterTeam is disqualified!
    assert leaderboard[0]["team_id"] == team_active
    assert leaderboard[0]["disqualified"] is False

    assert leaderboard[1]["team_id"] == team_cheater
    assert leaderboard[1]["disqualified"] is True
    assert leaderboard[1]["warnings"] == 3


def test_05_admin_pardon_restores_team(api_client):
    """Verify administrator pardon lifts disqualification and restores team privileges."""
    team_id = 23
    for _ in range(3):
        proctor_manager.record_violation(team_id, "tab_switch")
    assert proctor_manager.is_disqualified(team_id) is True

    # Admin pardons team
    pardon_res = api_client.post(f"/api/admin/teams/{team_id}/pardon")
    assert pardon_res.status_code == 200
    pdata = pardon_res.json()
    assert pdata["warnings"] == 0
    assert pdata["disqualified"] is False

    # Team can now submit flags again
    answers = validator.get_team_answers(team_id)
    sub_res = api_client.post("/api/terminal/validate", json={
        "team_id": team_id,
        "door": 1,
        "submission": answers["door1"]["flag"]
    })
    assert sub_res.status_code == 200
    assert sub_res.json()["valid"] is True
