"""
Terminal Session Manager
========================
Bridges browser WebSocket connections to Docker container PTYs.
Handles ANSI streaming, keystroke forwarding, window resize (SIGWINCH),
and session reconnects.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger("terminal.session")


class TerminalSession:
    def __init__(self, team_id: int, container_name: str, is_simulated: bool = False):
        self.team_id = team_id
        self.container_name = container_name
        self.is_simulated = is_simulated
        self.active_websockets: Set[WebSocket] = set()
        self.docker_socket = None
        self.exec_id = None
        self.read_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.simulated_buffer = ""

    async def connect_client(self, websocket: WebSocket):
        """Register a new player client WebSocket into this team's session."""
        self.active_websockets.add(websocket)
        logger.info(f"Team {self.team_id}: Client connected (total: {len(self.active_websockets)})")

        # Send initial banner/prompt if in simulated mode
        if self.is_simulated and len(self.active_websockets) == 1:
            welcome = (
                "\r\n\x1b[1;32m=====================================================\x1b[0m\r\n"
                "\x1b[1;36m🐧 ESCAPE THE TERMINAL — SESSION ACTIVE\x1b[0m\r\n"
                "   \x1b[33mEmergency Lockdown in Progress. Inspect README.txt\x1b[0m\r\n"
                "\x1b[1;32m=====================================================\x1b[0m\r\n\r\n"
                "\x1b[1;32mplayer@escape\x1b[0m:\x1b[1;34m~\x1b[0m$ "
            )
            await websocket.send_text(welcome)

    def disconnect_client(self, websocket: WebSocket):
        """Unregister a client WebSocket."""
        self.active_websockets.discard(websocket)
        logger.info(f"Team {self.team_id}: Client disconnected (remaining: {len(self.active_websockets)})")

    async def broadcast_output(self, data: str):
        """Send output from the container PTY to all connected team members."""
        dead_sockets = set()
        for ws in self.active_websockets:
            try:
                await ws.send_text(data)
            except Exception:
                dead_sockets.add(ws)
        self.active_websockets.difference_update(dead_sockets)

    async def handle_input(self, data: str):
        """Receive keystrokes from browser and forward to container PTY."""
        if self.is_simulated:
            # Handle simulated shell echo and basic commands for testing
            for char in data:
                if char in ("\r", "\n"):
                    cmd = self.simulated_buffer.strip()
                    self.simulated_buffer = ""
                    response = f"\r\n{self._execute_simulated_command(cmd)}\r\n\x1b[1;32mplayer@escape\x1b[0m:\x1b[1;34m~\x1b[0m$ "
                    await self.broadcast_output(response)
                elif char in ("\x7f", "\b"):  # Backspace
                    if len(self.simulated_buffer) > 0:
                        self.simulated_buffer = self.simulated_buffer[:-1]
                        await self.broadcast_output("\b \b")
                elif char == "\x03":  # Ctrl+C
                    self.simulated_buffer = ""
                    await self.broadcast_output("^C\r\n\x1b[1;32mplayer@escape\x1b[0m:\x1b[1;34m~\x1b[0m$ ")
                else:
                    self.simulated_buffer += char
                    await self.broadcast_output(char)
            return

        # Write directly to Docker exec socket
        if self.docker_socket:
            try:
                if hasattr(self.docker_socket, "_sock"):
                    self.docker_socket._sock.send(data.encode("utf-8"))
                elif hasattr(self.docker_socket, "write"):
                    self.docker_socket.write(data.encode("utf-8"))
            except Exception as e:
                logger.error(f"Error writing to container socket for team {self.team_id}: {e}")

    def _execute_simulated_command(self, cmd: str) -> str:
        """Simulated response for test verification."""
        if not cmd:
            return ""
        if cmd == "pwd":
            return "/home/player"
        elif cmd == "ls" or cmd == "dir":
            return "README.txt  documents  downloads  logs  old  tmp"
        elif cmd == "cat README.txt":
            return "[*] EMERGENCY LOCKDOWN ACTIVE. Investigate /escape sectors."
        elif "find" in cmd:
            return "/escape/room1/sector-alpha/clue.txt\n/escape/room1/sector-beta/status.txt"
        elif cmd == "clear":
            return "\x1b[2J\x1b[H"
        return f"bash: {cmd}: command executed in simulated test sandbox"

    async def resize(self, cols: int, rows: int):
        """Send terminal window resize (SIGWINCH) to container."""
        logger.debug(f"Team {self.team_id}: Resizing terminal to {cols}x{rows}")
        if not self.is_simulated and self.exec_id:
            try:
                import docker
                client = docker.APIClient()
                client.exec_resize(self.exec_id, height=rows, width=cols)
            except Exception as e:
                logger.warning(f"Failed to resize container exec for team {self.team_id}: {e}")


class SessionManager:
    def __init__(self):
        self.sessions: Dict[int, TerminalSession] = {}

    def get_or_create_session(self, team_id: int, container_name: str, is_simulated: bool = False) -> TerminalSession:
        if team_id not in self.sessions:
            logger.info(f"Creating new terminal session for Team {team_id}")
            session = TerminalSession(team_id, container_name, is_simulated=is_simulated)
            self.sessions[team_id] = session
        return self.sessions[team_id]

    def remove_session(self, team_id: int):
        if team_id in self.sessions:
            del self.sessions[team_id]


session_manager = SessionManager()
