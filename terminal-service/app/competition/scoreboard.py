"""
Escape Progress Scoreboard & Leaderboard Engine
===============================================
Computes live escape room rankings, per-door unlock progress,
penalty deductions, and completion times for big-screen projection and team dashboard.
"""

import time
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("terminal.competition.scoreboard")


class ScoreboardManager:
    def __init__(self):
        # team_id -> { "team_name": str, "doors_cleared": set, "solves": [...], "last_solve_ts": float }
        self.teams_state: Dict[int, Dict[str, Any]] = {}
        # Global announcement
        self.emergency_announcement: Optional[str] = None
        self.announcement_level: str = "info"  # info | warning | alert

    def record_solve(self, team_id: int, team_name: str, door_num: int, points: int = 100):
        """Record that a team cleared a door."""
        now = time.time()
        if team_id not in self.teams_state:
            self.teams_state[team_id] = {
                "team_name": team_name or f"Team {team_id:02d}",
                "doors_cleared": set(),
                "base_score": 0,
                "last_solve_ts": 0.0,
                "escaped_at": None
            }

        state = self.teams_state[team_id]
        if team_name:
            state["team_name"] = team_name

        if door_num not in state["doors_cleared"]:
            state["doors_cleared"].add(door_num)
            state["base_score"] += points
            state["last_solve_ts"] = now
            if len(state["doors_cleared"]) >= 6:
                state["escaped_at"] = now
                logger.info(f"🎉 TEAM {team_id} ({state['team_name']}) HAS COMPLETED ESCAPE ROOM!")

    def set_announcement(self, message: Optional[str], level: str = "info"):
        """Broadcast emergency alert banner to all participants."""
        self.emergency_announcement = message
        self.announcement_level = level
        logger.info(f"Admin broadcast set: [{level.upper()}] {message}")

    def clear_announcement(self):
        """Clear broadcast banner."""
        self.emergency_announcement = None

    def get_leaderboard(self, hints_penalties_fn=None) -> List[Dict[str, Any]]:
        """
        Generate ranked leaderboard with doors 1..6 statuses and net scores.
        """
        leaderboard = []

        for team_id, data in self.teams_state.items():
            doors_cleared = sorted(list(data["doors_cleared"]))
            doors_count = len(doors_cleared)
            current_door = min(6, doors_count + 1) if doors_count < 6 else 6
            escaped = doors_count >= 6

            penalties = 0
            if hints_penalties_fn:
                pen_data = hints_penalties_fn(team_id)
                penalties = pen_data.get("total_points_deducted", 0)

            net_score = max(0, data["base_score"] - penalties)

            door_statuses = {}
            for d in range(1, 7):
                if d in data["doors_cleared"]:
                    door_statuses[f"door_{d}"] = "cleared"
                elif d == current_door and not escaped:
                    door_statuses[f"door_{d}"] = "in_progress"
                else:
                    door_statuses[f"door_{d}"] = "locked"

            # Check proctor anti-cheat status
            from app.competition.proctor import proctor_manager
            proctor_info = proctor_manager.get_team_status(team_id)
            disqualified = proctor_info.get("disqualified", False)
            warnings = proctor_info.get("warnings", 0)

            leaderboard.append({
                "team_id": team_id,
                "team_name": data["team_name"],
                "doors_cleared_count": doors_count,
                "doors_cleared": doors_cleared,
                "current_door": current_door,
                "door_statuses": door_statuses,
                "base_score": data["base_score"],
                "penalties": penalties,
                "net_score": net_score,
                "escaped": escaped,
                "disqualified": disqualified,
                "warnings": warnings,
                "last_solve_ts": data["last_solve_ts"],
            })

        # Rank by:
        # 1. Not disqualified first (0 if active, 1 if disqualified)
        # 2. doors_cleared_count (descending)
        # 3. net_score (descending)
        # 4. last_solve_ts (ascending)
        leaderboard.sort(key=lambda x: (
            1 if x["disqualified"] else 0,
            -x["doors_cleared_count"],
            -x["net_score"],
            x["last_solve_ts"]
        ))

        # Assign rank numbers
        for idx, entry in enumerate(leaderboard, start=1):
            entry["rank"] = idx

        return leaderboard

    def reset(self):
        """Reset scoreboard state."""
        self.teams_state.clear()
        self.emergency_announcement = None


scoreboard_manager = ScoreboardManager()
