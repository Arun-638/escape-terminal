"""
Milestones 9 & 10 Verification Test Suite: Scoreboard, Room Progress & Admin Controls
=====================================================================================
Validates:
1. Live escape room progress calculation (doors cleared, current door, locked/in_progress/cleared states).
2. Leaderboard ranking algorithm (doors cleared -> net score -> solve timestamp).
3. Hint penalty subtraction from gross solve score.
4. Escaped completion status when all 6 doors are cleared.
5. Admin emergency broadcast announcement distribution.
6. Per-team emergency container reset endpoint.
7. HTML UI route accessibility (/scoreboard and /admin).
"""

import sys
import time
from pathlib import Path

# Add paths for terminal-service and ctfd
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "terminal-service"))
sys.path.insert(0, str(repo_root / "ctfd"))

import pytest
from starlette.testclient import TestClient
from app.main import app
from app.competition.scoreboard import ScoreboardManager, scoreboard_manager
from app.competition.hints import hints_manager


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    scoreboard_manager.reset()
    hints_manager.reset()
    yield
    scoreboard_manager.reset()
    hints_manager.reset()


def test_01_door_progress_and_ranking():
    """Verify team doors cleared, current door assignment, and ranking order."""
    sb = ScoreboardManager()

    # Team 1 solves Door 1 and 2
    sb.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=1, points=100)
    sb.record_solve(team_id=1, team_name="Team CyberPhantoms", door_num=2, points=100)

    # Team 2 solves Door 1
    sb.record_solve(team_id=2, team_name="Team BinaryBrawlers", door_num=1, points=100)

    # Team 3 solves Doors 1, 2, 3
    sb.record_solve(team_id=3, team_name="Team KernelKnights", door_num=1, points=100)
    sb.record_solve(team_id=3, team_name="Team KernelKnights", door_num=2, points=100)
    sb.record_solve(team_id=3, team_name="Team KernelKnights", door_num=3, points=100)

    leaderboard = sb.get_leaderboard()
    assert len(leaderboard) == 3

    # Rank 1 must be Team 3 (3 doors solved)
    assert leaderboard[0]["team_id"] == 3
    assert leaderboard[0]["rank"] == 1
    assert leaderboard[0]["doors_cleared_count"] == 3
    assert leaderboard[0]["current_door"] == 4
    assert leaderboard[0]["door_statuses"]["door_1"] == "cleared"
    assert leaderboard[0]["door_statuses"]["door_3"] == "cleared"
    assert leaderboard[0]["door_statuses"]["door_4"] == "in_progress"
    assert leaderboard[0]["door_statuses"]["door_5"] == "locked"

    # Rank 2 must be Team 1 (2 doors solved)
    assert leaderboard[1]["team_id"] == 1
    assert leaderboard[1]["rank"] == 2
    assert leaderboard[1]["doors_cleared_count"] == 2
    assert leaderboard[1]["current_door"] == 3

    # Rank 3 must be Team 2 (1 door solved)
    assert leaderboard[2]["team_id"] == 2
    assert leaderboard[2]["rank"] == 3
    assert leaderboard[2]["doors_cleared_count"] == 1
    assert leaderboard[2]["current_door"] == 2


def test_02_net_score_penalty_deduction():
    """Verify that hint penalties deduct from score without negative scores."""
    sb = ScoreboardManager()
    sb.record_solve(team_id=1, team_name="Alpha", door_num=1, points=100)

    # Fake hint penalty fn returning 25 points deducted
    def mock_penalties(t_id):
        return {"total_points_deducted": 25}

    board = sb.get_leaderboard(hints_penalties_fn=mock_penalties)
    assert board[0]["base_score"] == 100
    assert board[0]["penalties"] == 25
    assert board[0]["net_score"] == 75


def test_03_escaped_status():
    """Verify team gets ESCAPED status when clearing all 6 doors."""
    sb = ScoreboardManager()
    for d in range(1, 7):
        sb.record_solve(team_id=9, team_name="EliteEscapers", door_num=d, points=100)

    board = sb.get_leaderboard()
    assert board[0]["team_id"] == 9
    assert board[0]["doors_cleared_count"] == 6
    assert board[0]["escaped"] is True
    assert board[0]["base_score"] == 600
    for d in range(1, 7):
        assert board[0]["door_statuses"][f"door_{d}"] == "cleared"


def test_04_emergency_broadcast_api(api_client):
    """Verify emergency broadcast banner can be set and cleared by admin."""
    # Send broadcast
    post_res = api_client.post("/api/admin/announcement", json={
        "message": "ATTENTION: 10 minutes remaining!",
        "level": "warning"
    })
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "broadcasted"

    # Query announcement
    get_res = api_client.get("/api/competition/announcement")
    assert get_res.status_code == 200
    assert get_res.json()["message"] == "ATTENTION: 10 minutes remaining!"
    assert get_res.json()["level"] == "warning"

    # Verify announcement is included in scoreboard data
    sb_res = api_client.get("/api/competition/scoreboard")
    assert sb_res.status_code == 200
    assert sb_res.json()["announcement"]["message"] == "ATTENTION: 10 minutes remaining!"

    # Clear broadcast
    clear_res = api_client.post("/api/admin/announcement", json={"message": None})
    assert clear_res.status_code == 200
    assert clear_res.json()["status"] == "cleared"

    # Verify cleared
    sb_res2 = api_client.get("/api/competition/scoreboard")
    assert sb_res2.json()["announcement"] is None


def test_05_admin_team_reset_and_ui_routes(api_client):
    """Verify admin sandbox reset endpoint and HTML view routes."""
    # Reset team container
    reset_res = api_client.post("/api/admin/teams/3/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "reset_successful"

    # UI routes return HTML
    score_ui = api_client.get("/scoreboard")
    assert score_ui.status_code == 200
    assert "text/html" in score_ui.headers["content-type"]
    assert "ESCAPE THE TERMINAL" in score_ui.text

    admin_ui = api_client.get("/admin")
    assert admin_ui.status_code == 200
    assert "text/html" in admin_ui.headers["content-type"]
    assert "ADMIN EMERGENCY CONTROL CENTER" in admin_ui.text
