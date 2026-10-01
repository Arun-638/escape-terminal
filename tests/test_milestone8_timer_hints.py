"""
Milestone 8 Verification Test Suite: Persistent Competition Timer & Progressive Hints
=====================================================================================
Validates:
1. Server-authoritative countdown timer (start, pause, resume, reset, adjust).
2. Persistence across restarts (simulating process restart retaining exact remaining time).
3. Progressive hints catalog with masked clues prior to unlocking.
4. Correct point and time deduction accounting per team.
5. Cross-team isolation of hints (Team A unlocking a hint does not unlock it for Team B).
6. REST API endpoints for timer and hint lifecycle.
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
from app.competition.timer import CompetitionTimer, competition_timer
from app.competition.hints import HintsManager, hints_manager


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_timer_and_hints(tmp_path):
    """Ensure clean state before and after each test."""
    competition_timer.reset(new_duration=3000)
    hints_manager.reset()
    yield
    competition_timer.reset(new_duration=3000)
    hints_manager.reset()


def test_01_server_side_timer_lifecycle(tmp_path):
    """Verify state transitions: not_started -> running -> paused -> running -> reset."""
    timer = CompetitionTimer(state_file=tmp_path / "test_lifecycle.json", default_duration=100)
    assert timer.state == "not_started"
    status = timer.get_status()
    assert status["remaining_seconds"] == 100
    assert status["is_active"] is False

    # Start timer
    timer.start()
    assert timer.state == "running"
    time.sleep(0.1)
    status_running = timer.get_status()
    assert status_running["is_active"] is True
    assert status_running["elapsed_seconds"] >= 0.1

    # Pause timer
    timer.pause()
    assert timer.state == "paused"
    status_paused = timer.get_status()
    paused_remaining = status_paused["remaining_seconds"]
    time.sleep(0.1)
    # Remaining time should NOT have decreased while paused
    assert timer.get_status()["remaining_seconds"] == paused_remaining

    # Resume timer
    timer.resume()
    assert timer.state == "running"

    # Adjust time (+30s)
    timer.adjust_time(30)
    assert timer.get_status()["remaining_seconds"] > paused_remaining

    # Reset timer
    timer.reset(new_duration=500)
    assert timer.state == "not_started"
    assert timer.get_status()["remaining_seconds"] == 500


def test_02_timer_persistence_across_restart(tmp_path):
    """Verify that restarting the service process preserves exact elapsed time and state."""
    state_file = tmp_path / "test_timer_state.json"
    timer_instance_1 = CompetitionTimer(state_file=state_file, default_duration=120)

    # Start and consume some time
    timer_instance_1.start()
    time.sleep(0.15)
    timer_instance_1.pause()
    consumed = timer_instance_1.time_consumed_before_pause
    assert consumed >= 0.1

    # Simulate server crash/restart by loading a new instance from the same state file
    timer_instance_2 = CompetitionTimer(state_file=state_file, default_duration=120)
    assert timer_instance_2.state == "paused"
    assert abs(timer_instance_2.time_consumed_before_pause - consumed) < 0.01
    assert timer_instance_2.get_status()["remaining_seconds"] <= 120


def test_03_hints_masking_and_progressive_unlock():
    """Verify clues are hidden until unlocked and penalties accumulate accurately."""
    team_id = 42

    # Check initial door 1 hints (both must be masked)
    hints = hints_manager.get_hints_for_door(team_id=team_id, door=1)
    assert len(hints) == 2
    for h in hints:
        assert h["unlocked"] is False
        assert h["content"] is None  # Server hides content!

    # Unlock Hint 1
    unlock_res = hints_manager.unlock_hint(team_id=team_id, hint_id="d1_h1")
    assert unlock_res["success"] is True
    assert unlock_res["cost"] == 15
    assert "find" in unlock_res["hint"]["content"]

    # Verify Door 1 hints now: Hint 1 is revealed, Hint 2 remains masked
    updated_hints = hints_manager.get_hints_for_door(team_id=team_id, door=1)
    assert updated_hints[0]["unlocked"] is True
    assert "find" in updated_hints[0]["content"]
    assert updated_hints[1]["unlocked"] is False
    assert updated_hints[1]["content"] is None

    # Verify duplicate unlock is idempotent (does not charge twice)
    dup_unlock = hints_manager.unlock_hint(team_id=team_id, hint_id="d1_h1")
    assert dup_unlock["already_unlocked"] is True

    # Check total penalty
    penalties = hints_manager.get_team_total_penalties(team_id=team_id)
    assert penalties["total_points_deducted"] == 15
    assert penalties["total_seconds_deducted"] == 60
    assert penalties["unlocked_count"] == 1


def test_04_cross_team_hints_isolation():
    """Verify unlocking a hint for Team A does NOT unlock or reveal it for Team B."""
    team_a = 10
    team_b = 20

    # Team A unlocks Hint 2 for Door 1
    hints_manager.unlock_hint(team_id=team_a, hint_id="d1_h2")

    # Team A sees unlocked content
    a_hints = hints_manager.get_hints_for_door(team_id=team_a, door=1)
    assert a_hints[1]["unlocked"] is True
    assert a_hints[1]["content"] is not None

    # Team B must still see locked / masked content
    b_hints = hints_manager.get_hints_for_door(team_id=team_b, door=1)
    assert b_hints[1]["unlocked"] is False
    assert b_hints[1]["content"] is None

    # Team B penalty must be 0
    assert hints_manager.get_team_total_penalties(team_id=team_b)["total_points_deducted"] == 0


def test_05_timer_and_hints_api_integration(api_client):
    """Verify REST API endpoints for timer control and hint purchasing."""
    # 1. Start timer via API
    resp_start = api_client.post("/api/competition/timer/control", json={"action": "start", "duration": 3000})
    assert resp_start.status_code == 200
    assert resp_start.json()["state"] == "running"

    # 2. Get timer status via API
    resp_get = api_client.get("/api/competition/timer")
    assert resp_get.status_code == 200
    assert resp_get.json()["remaining_seconds"] <= 3000
    assert "formatted_remaining" in resp_get.json()

    # 3. Query hints for door 2
    resp_hints = api_client.get("/api/competition/hints/2?team_id=5")
    assert resp_hints.status_code == 200
    assert len(resp_hints.json()["hints"]) == 2
    assert resp_hints.json()["hints"][0]["content"] is None

    # 4. Unlock hint for door 2 via API
    resp_unlock = api_client.post("/api/competition/hints/unlock", json={"team_id": 5, "hint_id": "d2_h1"})
    assert resp_unlock.status_code == 200
    assert resp_unlock.json()["cost"] == 15
    assert "ls -la" in resp_unlock.json()["hint"]["content"]

    # 5. Check penalty endpoint
    resp_pen = api_client.get("/api/competition/hints/penalties/5")
    assert resp_pen.status_code == 200
    assert resp_pen.json()["total_points_deducted"] == 15
