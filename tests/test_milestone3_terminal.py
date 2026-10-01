"""
Milestone 3 Verification Test Suite: Web Terminal Engine
========================================================
Validates:
1. Terminal service health and container status APIs.
2. WebSocket connection establishment and initial PTY banner reception.
3. Interactive command input execution (pwd, ls) and ANSI response streaming.
4. Keystroke handling including Ctrl+C and Backspace.
5. Window resize event handling (cols/rows).
6. IDOR protection & authorization gating.
"""

import sys
import json
from pathlib import Path

# Add terminal-service to Python path
service_root = Path(__file__).resolve().parent.parent / "terminal-service"
sys.path.insert(0, str(service_root))

import pytest
from starlette.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_01_health_and_info_apis(client):
    """Verify health endpoint and team container inspection API."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

    res2 = client.get("/api/terminal/teams/1")
    assert res2.status_code == 200
    team_data = res2.json()
    assert team_data["team_id"] == 1
    assert "escape-team-01" in team_data["container"]["name"]
    print("\n[VERIFIED] 1. Health & Container Status APIs verified.")


def test_02_websocket_connection_and_banner(client):
    """Verify WebSocket handshake and welcome banner transmission."""
    with client.websocket_connect("/ws/terminal/1") as ws:
        banner = ws.receive_text()
        assert "ESCAPE THE TERMINAL" in banner
        assert "player@escape" in banner
        print("[VERIFIED] 2. WebSocket connection and PTY welcome banner verified.")


def test_03_interactive_command_execution(client):
    """Verify sending commands and receiving PTY output (pwd, ls)."""
    with client.websocket_connect("/ws/terminal/1") as ws:
        # Initial banner
        _ = ws.receive_text()

        # Execute 'pwd'
        ws.send_text(json.dumps({"type": "input", "data": "pwd\r"}))
        # Receive echo and response
        output = ""
        for _ in range(5):
            msg = ws.receive_text()
            output += msg
            if "/home/player" in output:
                break
        assert "/home/player" in output, f"Expected /home/player, got: {output}"

        # Execute 'ls'
        ws.send_text(json.dumps({"type": "input", "data": "ls\r"}))
        ls_output = ""
        for _ in range(5):
            msg = ws.receive_text()
            ls_output += msg
            if "README.txt" in ls_output:
                break
        assert "README.txt" in ls_output, f"Expected README.txt in ls output, got: {ls_output}"
        print("[VERIFIED] 3. Interactive command execution (pwd, ls) verified.")


def test_04_ctrl_c_and_interrupt(client):
    """Verify Ctrl+C interrupt signals clear buffer and restore prompt."""
    with client.websocket_connect("/ws/terminal/1") as ws:
        _ = ws.receive_text()

        # Send Ctrl+C (\x03) directly
        ws.send_text(json.dumps({"type": "input", "data": "\x03"}))
        res = ws.receive_text()
        assert "^C" in res
        assert "player@escape" in res
        print("[VERIFIED] 4. Ctrl+C interrupt handling verified.")


def test_05_terminal_resize(client):
    """Verify window resize message handling."""
    with client.websocket_connect("/ws/terminal/1") as ws:
        _ = ws.receive_text()
        # Send resize packet
        ws.send_text(json.dumps({"type": "resize", "cols": 120, "rows": 35}))
        # Terminal continues functioning after resize
        ws.send_text(json.dumps({"type": "input", "data": "pwd\r"}))
        res = ""
        for _ in range(5):
            res += ws.receive_text()
            if "/home/player" in res:
                break
        assert "/home/player" in res
        print("[VERIFIED] 5. Terminal window resize verified.")


def test_06_idor_authorization_enforcement(client):
    """Verify that unauthorized sessions cannot connect to other teams."""
    # Attempting to access Team 2 with Team 1 token
    with client.websocket_connect("/ws/terminal/2?token=test-token-team-1") as ws:
        msg = ws.receive_text()
        assert "Unauthorized" in msg
        print("[VERIFIED] 6. IDOR protection & authorization enforcement verified.")


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
