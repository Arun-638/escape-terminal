"""
Anti-Cheat & Proctoring Engine
==============================
Tracks fullscreen exits, tab switches, and window blur events per team.
Enforces a 3-strike disqualification rule.
Persists proctor state server-side so page refreshes cannot bypass warnings.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("terminal.competition.proctor")


class ProctorManager:
    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (Path(__file__).parent.parent.parent / "proctor_state.json")
        # team_id -> { "warnings": int, "disqualified": bool, "log": [...] }
        self.teams: Dict[int, Dict[str, Any]] = {}
        self._load_state()

    def _save_state(self):
        try:
            self.state_file.write_text(json.dumps(self.teams, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist proctor state: {e}")

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.teams = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Could not load proctor state: {e}")

    def get_team_status(self, team_id: int) -> Dict[str, Any]:
        """Get current warning count and disqualification status."""
        if team_id not in self.teams:
            self.teams[team_id] = {
                "warnings": 0,
                "disqualified": False,
                "violations": []
            }
        return self.teams[team_id]

    def record_violation(self, team_id: int, reason: str = "tab_switch") -> Dict[str, Any]:
        """
        Record a proctoring violation (tab switch or fullscreen exit).
        Increments warning count. If 3 strikes reached, marks team as disqualified.
        """
        status = self.get_team_status(team_id)

        if status["disqualified"]:
            return status

        status["warnings"] += 1
        now = time.strftime("%H:%M:%S")
        status["violations"].append({
            "timestamp": now,
            "reason": reason,
            "warning_number": status["warnings"]
        })

        if status["warnings"] >= 3:
            status["disqualified"] = True
            logger.warning(f"🚨 TEAM {team_id} HAS BEEN DISQUALIFIED (3 proctoring strikes)")
        else:
            logger.warning(f"⚠️ Team {team_id} received proctoring warning #{status['warnings']} ({reason})")

        self._save_state()
        return status

    def pardon_team(self, team_id: int) -> Dict[str, Any]:
        """Admin pardon: resets warnings and lifts disqualification."""
        if team_id in self.teams:
            self.teams[team_id] = {
                "warnings": 0,
                "disqualified": False,
                "violations": []
            }
            self._save_state()
            logger.info(f"Team {team_id} has been pardoned by admin.")
        return self.get_team_status(team_id)

    def is_disqualified(self, team_id: int) -> bool:
        return self.get_team_status(team_id).get("disqualified", False)

    def reset_all(self):
        """Reset all proctoring states."""
        self.teams.clear()
        self._save_state()


proctor_manager = ProctorManager()
