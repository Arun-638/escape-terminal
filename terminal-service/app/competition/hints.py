"""
Progressive Hints Engine
========================
Provides tiered hints with point or time deductions per team.
Guarantees un-unlocked hint contents remain masked server-side until purchased.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("terminal.competition.hints")

HINTS_CATALOG = [
    # Door 1: Filesystem Navigation & Clue Discovery
    {
        "id": "d1_h1",
        "door": 1,
        "level": 1,
        "title": "Directory Exploration",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Use the 'find' command to locate clues in sectors: find /escape/room1 -name '*.txt' -o -name '*key*'"
    },
    {
        "id": "d1_h2",
        "door": 1,
        "level": 2,
        "title": "Sector Key Location",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "Look inside /escape/room1/sector-alpha/clue.txt. The format to submit is ESCAPE{DOOR1_SECTOR_...}"
    },
    # Door 2: Hidden Files & Hex Decoding
    {
        "id": "d2_h1",
        "door": 2,
        "level": 1,
        "title": "Revealing Dotfiles",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Hidden files in Unix systems start with a dot ('.'). Run 'ls -la /escape/room2/' to view them."
    },
    {
        "id": "d2_h2",
        "door": 2,
        "level": 2,
        "title": "Hexadecimal Decoding",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "The file .shadow_token contains hex codes. You can decode it with: xxd -r -p < filename or python3 -c 'print(bytes.fromhex(open(\".shadow_token\").read()).decode())'"
    },
    # Door 3: Log Extraction & Base64
    {
        "id": "d3_h1",
        "door": 3,
        "level": 1,
        "title": "Log Grepping",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Search for critical alert codes or ACCESS_GRANTED strings in /var/log/syslog using grep -E 'FLAG|TOKEN|KEY'"
    },
    {
        "id": "d3_h2",
        "door": 3,
        "level": 2,
        "title": "Base64 Stream Decoding",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "Base64 encoded strings often end with '=' or '=='. Pipe the string into: echo '<encoded>' | base64 -d"
    },
    # Door 4: Permissions & Executable Analysis
    {
        "id": "d4_h1",
        "door": 4,
        "level": 1,
        "title": "Permission Audit",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Use 'ls -l' to check file permissions, or find executable files with: find /escape/room4 -perm -111 -type f"
    },
    {
        "id": "d4_h2",
        "door": 4,
        "level": 2,
        "title": "Execution Extraction",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "Only one utility is marked executable (+x). Execute it directly: ./generator --token to emit the door unlock code."
    },
    # Door 5: Process & Environment Forensics
    {
        "id": "d5_h1",
        "door": 5,
        "level": 1,
        "title": "Environment Variable Inspection",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Run 'env' or 'printenv' to inspect environment variables. Search specifically for keys: env | grep -i token"
    },
    {
        "id": "d5_h2",
        "door": 5,
        "level": 2,
        "title": "Procfs & Background Daemons",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "Inspect active processes with 'ps aux' or cat the process environment under /proc/<pid>/environ."
    },
    # Door 6: Forensic Timestamp & SHA-256 Audit
    {
        "id": "d6_h1",
        "door": 6,
        "level": 1,
        "title": "Timestamp Forensics",
        "cost": 15,
        "time_penalty_seconds": 60,
        "content": "Identify the most recently modified configuration file using: ls -lt /escape/room6 | head -n 5"
    },
    {
        "id": "d6_h2",
        "door": 6,
        "level": 2,
        "title": "Checksum Verification",
        "cost": 25,
        "time_penalty_seconds": 120,
        "content": "Compute the SHA-256 digest of the altered file using: sha256sum /escape/room6/critical.conf"
    }
]


class HintsManager:
    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or (Path(__file__).parent.parent.parent / "unlocked_hints.json")
        # team_id -> set of unlocked hint IDs
        self.unlocked: Dict[int, List[str]] = {}
        self._load_state()

    def _save_state(self):
        try:
            self.state_file.write_text(json.dumps(self.unlocked, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist unlocked hints: {e}")

    def _load_state(self):
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.unlocked = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Could not load hints state: {e}")

    def get_hints_for_door(self, team_id: int, door: int) -> List[Dict[str, Any]]:
        """Return all hints for a door. Mask content if not yet unlocked by team."""
        team_unlocked = set(self.unlocked.get(team_id, []))
        results = []

        for h in HINTS_CATALOG:
            if h["door"] == door:
                is_unlocked = h["id"] in team_unlocked
                results.append({
                    "id": h["id"],
                    "door": h["door"],
                    "level": h["level"],
                    "title": h["title"],
                    "cost": h["cost"],
                    "time_penalty_seconds": h["time_penalty_seconds"],
                    "unlocked": is_unlocked,
                    "content": h["content"] if is_unlocked else None
                })
        return results

    def unlock_hint(self, team_id: int, hint_id: str) -> Dict[str, Any]:
        """Unlock a hint for a team, recording the cost penalty."""
        hint = next((h for h in HINTS_CATALOG if h["id"] == hint_id), None)
        if not hint:
            return {"success": False, "message": "Hint not found"}

        if team_id not in self.unlocked:
            self.unlocked[team_id] = []

        if hint_id in self.unlocked[team_id]:
            return {
                "success": True,
                "already_unlocked": True,
                "hint": hint,
                "message": "Hint was already unlocked."
            }

        self.unlocked[team_id].append(hint_id)
        self._save_state()
        logger.info(f"Team {team_id} unlocked hint {hint_id} (-{hint['cost']} pts / -{hint['time_penalty_seconds']}s)")

        return {
            "success": True,
            "already_unlocked": False,
            "hint": hint,
            "cost": hint["cost"],
            "time_penalty_seconds": hint["time_penalty_seconds"],
            "message": f"Hint unlocked! Deduction: {hint['cost']} points."
        }

    def get_team_total_penalties(self, team_id: int) -> Dict[str, int]:
        """Calculate total points and time deducted from hints for a team."""
        team_unlocked = set(self.unlocked.get(team_id, []))
        total_cost = 0
        total_time_penalty = 0

        for h in HINTS_CATALOG:
            if h["id"] in team_unlocked:
                total_cost += h["cost"]
                total_time_penalty += h["time_penalty_seconds"]

        return {
            "total_points_deducted": total_cost,
            "total_seconds_deducted": total_time_penalty,
            "unlocked_count": len(team_unlocked)
        }

    def reset(self):
        """Reset all hint states."""
        self.unlocked.clear()
        self._save_state()


hints_manager = HintsManager()
