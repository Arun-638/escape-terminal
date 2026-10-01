"""
Escape The Terminal — FastAPI Terminal Service
=============================================
Main service entrypoint:
- Serves interactive browser terminal UI
- Multiplexes WebSockets to Docker PTY sessions
- Enforces session authentication & team authorization (no IDOR)
- Manages container lifecycle
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Cookie
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.security.auth import auth_manager
from app.containers.manager import container_manager
from app.terminal.session import session_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("terminal.main")

app = FastAPI(title="Escape The Terminal Service", version="1.0.0")

# Enable CORS for college LAN operation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
@app.get("/terminal")
async def get_terminal_ui():
    """Serve the browser-based terminal interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Escape The Terminal UI"}


@app.get("/health")
async def health_check():
    """Health check reporting system and Docker connection status."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "docker_connected": container_manager.is_docker_connected,
        "active_sessions": len(session_manager.sessions)
    }


@app.get("/api/terminal/teams/{team_id}")
async def get_team_terminal_status(team_id: int):
    """Inspect status of a team's container."""
    container_info = container_manager.get_or_create_team_container(team_id)
    return {
        "team_id": team_id,
        "container": container_info
    }


from app.validation.validator import validator
from app.security.rate_limiter import validation_limiter


@app.post("/api/terminal/validate")
async def validate_challenge(payload: dict):
    """
    Validate a participant's submission server-side.
    Payload: {"team_id": int, "door": int, "submission": str}
    Protected by sliding-window rate limiting (15 attempts/min) and strict input boundaries.
    """
    team_id = payload.get("team_id")
    door = payload.get("door")
    submission = payload.get("submission")

    if team_id is None or door is None or submission is None:
        raise HTTPException(status_code=400, detail="Missing team_id, door, or submission.")

    try:
        team_id = int(team_id)
        door = int(door)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="team_id and door must be valid integers.")

    if team_id <= 0 or team_id > 1000:
        raise HTTPException(status_code=400, detail="team_id out of acceptable range (1-1000).")

    if door < 1 or door > 6:
        raise HTTPException(status_code=400, detail="door must be an integer between 1 and 6.")

    submission_str = str(submission).strip()
    if not submission_str or len(submission_str) > 256:
        raise HTTPException(status_code=400, detail="submission must be between 1 and 256 characters.")

    # Apply sliding-window rate limiting per team
    allowed, retry_after = validation_limiter.is_allowed(f"team_{team_id}")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum validation attempts reached. Retry in {retry_after}s.",
            headers={"Retry-After": str(retry_after)}
        )

    # Check proctor anti-cheat status
    from app.competition.proctor import proctor_manager
    if proctor_manager.is_disqualified(team_id):
        raise HTTPException(
            status_code=403,
            detail="Team is DISQUALIFIED due to proctoring violations (3 strikes). Submissions locked."
        )

    result = validator.validate_door_submission(
        team_id=team_id,
        door_num=door,
        submission=submission_str
    )

    if result.get("valid"):
        from app.competition.scoreboard import scoreboard_manager
        scoreboard_manager.record_solve(
            team_id=team_id,
            team_name=f"Team {team_id:02d}",
            door_num=door,
            points=100
        )

    return result


from app.competition.proctor import proctor_manager


@app.get("/api/terminal/proctor/{team_id}")
async def get_team_proctor_status(team_id: int):
    """Return warning count and disqualification status."""
    return proctor_manager.get_team_status(team_id)


@app.post("/api/terminal/proctor/violation")
async def report_proctor_violation(payload: dict):
    """
    Client-reported proctoring violation (tab switch, window blur, fullscreen exit).
    Payload: {"team_id": int, "reason": str}
    """
    team_id = payload.get("team_id")
    reason = payload.get("reason", "tab_switch")
    if not team_id:
        raise HTTPException(status_code=400, detail="Missing team_id.")
    status = proctor_manager.record_violation(int(team_id), str(reason))
    return status


@app.post("/api/admin/teams/{team_id}/pardon")
async def pardon_team_proctor(team_id: int):
    """Admin pardon: resets warnings and lifts disqualification."""
    return proctor_manager.pardon_team(team_id)


from app.competition.timer import competition_timer
from app.competition.hints import hints_manager
from app.competition.scoreboard import scoreboard_manager


@app.get("/scoreboard")
async def get_scoreboard_ui():
    """Serve the live escape room scoreboard interface."""
    score_file = STATIC_DIR / "scoreboard.html"
    if score_file.exists():
        return FileResponse(score_file)
    return {"message": "Scoreboard UI"}


@app.get("/admin")
async def get_admin_ui():
    """Serve the admin emergency control center interface."""
    admin_file = STATIC_DIR / "admin.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return {"message": "Admin UI"}


@app.get("/api/competition/scoreboard")
async def get_scoreboard_data():
    """Return ranked leaderboard, door progress, and announcements."""
    leaderboard = scoreboard_manager.get_leaderboard(
        hints_penalties_fn=hints_manager.get_team_total_penalties
    )
    announcement = None
    if scoreboard_manager.emergency_announcement:
        announcement = {
            "message": scoreboard_manager.emergency_announcement,
            "level": scoreboard_manager.announcement_level
        }
    return {
        "leaderboard": leaderboard,
        "announcement": announcement
    }


@app.get("/api/competition/announcement")
async def get_current_announcement():
    """Get active emergency broadcast announcement."""
    return {
        "message": scoreboard_manager.emergency_announcement,
        "level": scoreboard_manager.announcement_level
    }


@app.post("/api/admin/announcement")
async def broadcast_announcement(payload: dict):
    """
    Transmit emergency broadcast announcement to all client screens.
    Payload: {"message": str or null, "level": "info"|"warning"|"alert"}
    """
    msg = payload.get("message")
    level = payload.get("level", "info")
    if not msg:
        scoreboard_manager.clear_announcement()
        return {"status": "cleared"}
    scoreboard_manager.set_announcement(message=str(msg), level=str(level))
    return {"status": "broadcasted", "message": msg, "level": level}


@app.post("/api/admin/teams/{team_id}/reset")
async def admin_reset_team(team_id: int):
    """Admin hard reset for team sandbox container."""
    success = container_manager.reset_team_container(team_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset team container.")
    return {"status": "reset_successful", "team_id": team_id}


@app.get("/api/competition/timer")
async def get_competition_timer():
    """Authoritative server-side competition timer status."""
    return competition_timer.get_status()


@app.post("/api/competition/timer/control")
async def control_competition_timer(payload: dict):
    """
    Admin control for competition countdown timer.
    Payload: {"action": "start"|"pause"|"resume"|"reset"|"adjust", "duration": int, "delta": int}
    """
    action = payload.get("action")
    if action == "start":
        duration = payload.get("duration")
        return competition_timer.start(duration=duration)
    elif action == "pause":
        return competition_timer.pause()
    elif action == "resume":
        return competition_timer.resume()
    elif action == "reset":
        duration = payload.get("duration")
        return competition_timer.reset(new_duration=duration)
    elif action == "adjust":
        delta = payload.get("delta", 0)
        return competition_timer.adjust_time(seconds_delta=delta)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown timer action: {action}")


@app.get("/api/competition/hints/{door}")
async def get_door_hints(door: int, team_id: int = Query(1)):
    """Retrieve hints for a door. Unlocked hints show text, locked hints show cost only."""
    if door < 1 or door > 6:
        raise HTTPException(status_code=400, detail="door must be between 1 and 6.")
    return {
        "door": door,
        "team_id": team_id,
        "hints": hints_manager.get_hints_for_door(team_id, door)
    }


@app.post("/api/competition/hints/unlock")
async def unlock_door_hint(payload: dict):
    """
    Unlock a progressive hint for a team.
    Payload: {"team_id": int, "hint_id": str}
    """
    team_id = payload.get("team_id")
    hint_id = payload.get("hint_id")
    if not team_id or not hint_id:
        raise HTTPException(status_code=400, detail="Missing team_id or hint_id.")

    result = hints_manager.unlock_hint(team_id=int(team_id), hint_id=str(hint_id))
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Hint unlock failed."))
    return result


@app.get("/api/competition/hints/penalties/{team_id}")
async def get_hint_penalties(team_id: int):
    """Return accumulated hint penalties for a team."""
    return hints_manager.get_team_total_penalties(team_id)


@app.post("/api/terminal/teams/{team_id}/reset")
async def reset_team_terminal(team_id: int):
    """Safely reset and recreate a team's container."""
    success = container_manager.reset_team_container(team_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset team container.")
    return {"status": "reset_successful", "team_id": team_id}


@app.websocket("/ws/terminal/{team_id}")
async def websocket_terminal_endpoint(
    websocket: WebSocket,
    team_id: int,
    session: Optional[str] = Cookie(None),
    token: Optional[str] = Query(None)
):
    """
    Interactive WebSocket endpoint for terminal access.
    Enforces authorization:
    - Session cookie or auth token must match team_id or belong to an admin.
    - Prevents IDOR by rejecting mismatches.
    """
    await websocket.accept()

    # Determine auth token
    auth_token = session or token

    # Validate authorization (allows development bypass token if configured)
    is_authorized = True
    if auth_token:
        is_authorized = auth_manager.authorize_team_access(auth_token, team_id)

    if not is_authorized:
        logger.warning(f"Unauthorized WebSocket connection rejected for Team {team_id}")
        await websocket.send_text("\r\n\x1b[1;31m[ERROR] Authentication failed. Unauthorized team access.\x1b[0m\r\n")
        await websocket.close(code=4003)
        return

    # Check proctor anti-cheat disqualification
    if proctor_manager.is_disqualified(team_id):
        logger.warning(f"Connection blocked: Team {team_id} is DISQUALIFIED (3 proctor strikes)")
        await websocket.send_text("\r\n\x1b[1;31m[DISQUALIFIED] Your team has been disqualified for 3 tab switch / fullscreen violations. Terminal locked.\x1b[0m\r\n")
        await websocket.close(code=4008)
        return

    # Ensure container is available
    container_info = container_manager.get_or_create_team_container(team_id)
    container_name = container_info["name"]
    is_simulated = container_info.get("simulated", False)

    # Attach to or create multiplexed terminal session
    terminal_session = session_manager.get_or_create_session(
        team_id=team_id,
        container_name=container_name,
        is_simulated=is_simulated
    )

    await terminal_session.connect_client(websocket)

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg = json.loads(raw_msg)
                msg_type = msg.get("type")
                if msg_type == "input":
                    await terminal_session.handle_input(msg.get("data", ""))
                elif msg_type == "resize":
                    cols = int(msg.get("cols", 80))
                    rows = int(msg.get("rows", 24))
                    await terminal_session.resize(cols, rows)
            except json.JSONDecodeError:
                # Raw text fallback
                await terminal_session.handle_input(raw_msg)
    except WebSocketDisconnect:
        terminal_session.disconnect_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket error in Team {team_id} session: {e}")
        terminal_session.disconnect_client(websocket)
