"""
State-Based Challenge Validation Engine
======================================
Validates challenge progress server-side based on deterministic team state
rather than brittle command inspection.
Interacts with CTFd to award points and log solves.
"""

import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings

# Import deterministic challenge generator logic
try:
    from app.validation.generate_challenges import ChallengeGenerator
except ImportError:
    import sys
    scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "challenge-environment" / "scripts"
    sys.path.insert(0, str(scripts_dir))
    from generate_challenges import ChallengeGenerator

logger = logging.getLogger("terminal.validation")


class StateValidator:
    def __init__(self, ctfd_url: str = settings.CTFD_URL, server_secret: str = settings.SERVER_SECRET, competition_id: str = settings.COMPETITION_ID):
        self.ctfd_url = ctfd_url
        self.server_secret = server_secret
        self.competition_id = competition_id

    def get_team_answers(self, team_id: int) -> Dict[str, Any]:
        """Reconstruct the deterministic puzzle answers for a specific team."""
        generator = ChallengeGenerator(
            team_id=team_id,
            root_dir=Path("/tmp/dummy"),
            server_secret=self.server_secret,
            competition_id=self.competition_id,
            write_files=False
        )
        generator.generate_all()
        return generator.answers

    def validate_door_submission(self, team_id: int, door_num: int, submission: str) -> Dict[str, Any]:
        """
        Validate whether the player's submission correctly solves the target door.
        Supports both exact flag matching and case-insensitive/space-tolerant formats.
        """
        submission = submission.strip()
        answers = self.get_team_answers(team_id)

        door_key = f"door{door_num}"
        if door_key not in answers:
            return {"valid": False, "message": f"Door {door_num} validation not yet implemented."}

        expected_flag = answers[door_key]["flag"]

        # Check exact or standard flag match (case-insensitive)
        if submission.upper() == expected_flag.upper():
            return {
                "valid": True,
                "door": door_num,
                "team_id": team_id,
                "flag": expected_flag,
                "message": f"Door {door_num} successfully unlocked!"
            }

        # Flexible token matching per door
        if door_num == 2 and "plaintext" in answers["door2"]:
            if submission.upper() == answers["door2"]["plaintext"].upper():
                return {
                    "valid": True,
                    "door": door_num,
                    "team_id": team_id,
                    "flag": expected_flag,
                    "message": "Door 2 hex successfully decoded!"
                }

        if door_num == 3 and "plaintext" in answers["door3"]:
            if submission.upper() == answers["door3"]["plaintext"].upper():
                return {
                    "valid": True,
                    "door": door_num,
                    "team_id": team_id,
                    "flag": expected_flag,
                    "message": "Door 3 log anomaly stream successfully decoded!"
                }

        if door_num in (4, 5, 6) and "token" in answers[door_key]:
            if submission.upper() == answers[door_key]["token"].upper():
                return {
                    "valid": True,
                    "door": door_num,
                    "team_id": team_id,
                    "flag": expected_flag,
                    "message": f"Door {door_num} token verified!"
                }

        return {
            "valid": False,
            "door": door_num,
            "team_id": team_id,
            "message": "Incorrect access key or incomplete solution."
        }

    def award_solve_to_ctfd(self, session_cookie: str, challenge_id: int, flag: str) -> Dict[str, Any]:
        """
        Submit a validated solve to CTFd's attempt endpoint on behalf of the user.
        """
        try:
            cookies = {"session": session_cookie}
            # Obtain CSRF nonce
            page = requests.get(f"{self.ctfd_url}/challenges", cookies=cookies, timeout=3.0)
            nonce = page.cookies.get("nonce", "")

            headers = {"CSRF-Token": nonce} if nonce else {}
            payload = {
                "challenge_id": challenge_id,
                "submission": flag
            }
            resp = requests.post(
                f"{self.ctfd_url}/api/v1/challenges/attempt",
                json=payload,
                cookies=cookies,
                headers=headers,
                timeout=3.0
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to submit solve to CTFd: {e}")
            return {"success": False, "error": str(e)}


validator = StateValidator()
