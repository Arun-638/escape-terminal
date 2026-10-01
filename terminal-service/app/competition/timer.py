"""
Server-Side Competition Timer & State Engine
============================================
Guarantees deterministic, server-authoritative countdown timing for LAN competitions.
Browser refreshes, clock skew, or client tampering cannot alter the remaining time.
Persists state to disk so service restarts retain the exact remaining duration.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("terminal.competition.timer")


class CompetitionTimer:
    def __init__(self, state_file: Optional[Path] = None, default_duration: int = 3000):
        """
        :param state_file: Path to persist timer state
        :param default_duration: Competition duration in seconds (default 3000 = 50 min)
        """
        self.state_file = state_file or (Path(__file__).parent.parent.parent / "competition_timer.json")
        self.default_duration = default_duration

        # State fields
        self.state = "not_started"  # not_started | running | paused | finished
        self.duration_seconds = default_duration
        self.start_timestamp: Optional[float] = None
        self.paused_timestamp: Optional[float] = None
        self.time_consumed_before_pause = 0.0

        self._load_state()

    def _save_state(self):
        """Save current timer state to persistent JSON file."""
        try:
            data = {
                "state": self.state,
                "duration_seconds": self.duration_seconds,
                "start_timestamp": self.start_timestamp,
                "paused_timestamp": self.paused_timestamp,
                "time_consumed_before_pause": self.time_consumed_before_pause,
            }
            self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist competition timer state: {e}")

    def _load_state(self):
        """Load state from persistent file if present."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.state = data.get("state", "not_started")
                self.duration_seconds = data.get("duration_seconds", self.default_duration)
                self.start_timestamp = data.get("start_timestamp")
                self.paused_timestamp = data.get("paused_timestamp")
                self.time_consumed_before_pause = data.get("time_consumed_before_pause", 0.0)
                logger.info(f"Loaded existing competition timer state: {self.state}")
            except Exception as e:
                logger.warning(f"Could not load timer state: {e}. Starting fresh.")

    def start(self, duration: Optional[int] = None) -> Dict[str, Any]:
        """Start or restart the competition timer."""
        if duration:
            self.duration_seconds = duration
        now = time.time()
        self.state = "running"
        self.start_timestamp = now
        self.paused_timestamp = None
        self.time_consumed_before_pause = 0.0
        self._save_state()
        logger.info(f"Competition timer started: {self.duration_seconds} seconds")
        return self.get_status()

    def pause(self) -> Dict[str, Any]:
        """Pause the competition timer."""
        if self.state != "running":
            return self.get_status()

        now = time.time()
        if self.start_timestamp:
            elapsed = now - self.start_timestamp
            self.time_consumed_before_pause += elapsed

        self.state = "paused"
        self.paused_timestamp = now
        self.start_timestamp = None
        self._save_state()
        logger.info(f"Competition timer paused. Consumed: {self.time_consumed_before_pause:.1f}s")
        return self.get_status()

    def resume(self) -> Dict[str, Any]:
        """Resume a paused competition timer."""
        if self.state != "paused":
            return self.get_status()

        self.state = "running"
        self.start_timestamp = time.time()
        self.paused_timestamp = None
        self._save_state()
        logger.info("Competition timer resumed.")
        return self.get_status()

    def adjust_time(self, seconds_delta: int) -> Dict[str, Any]:
        """Add (positive) or deduct (negative) time in seconds."""
        self.duration_seconds = max(0, self.duration_seconds + seconds_delta)
        self._save_state()
        logger.info(f"Adjusted competition duration by {seconds_delta}s. New total: {self.duration_seconds}s")
        return self.get_status()

    def reset(self, new_duration: Optional[int] = None) -> Dict[str, Any]:
        """Reset the timer to initial non-started state."""
        self.duration_seconds = new_duration or self.default_duration
        self.state = "not_started"
        self.start_timestamp = None
        self.paused_timestamp = None
        self.time_consumed_before_pause = 0.0
        self._save_state()
        logger.info("Competition timer reset to initial state.")
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """
        Compute authoritative current countdown status.
        """
        now = time.time()

        if self.state == "not_started":
            remaining = self.duration_seconds
            elapsed = 0.0
        elif self.state == "paused":
            elapsed = self.time_consumed_before_pause
            remaining = max(0.0, self.duration_seconds - elapsed)
        elif self.state == "running":
            current_leg = (now - self.start_timestamp) if self.start_timestamp else 0.0
            elapsed = self.time_consumed_before_pause + current_leg
            remaining = max(0.0, self.duration_seconds - elapsed)
            if remaining <= 0:
                self.state = "finished"
                remaining = 0.0
                self._save_state()
        else:  # finished
            elapsed = float(self.duration_seconds)
            remaining = 0.0

        mins = int(remaining) // 60
        secs = int(remaining) % 60
        formatted = f"{mins:02d}:{secs:02d}"

        return {
            "state": self.state,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(elapsed, 1),
            "remaining_seconds": int(remaining),
            "formatted_remaining": formatted,
            "is_active": self.state == "running",
            "is_finished": self.state == "finished" or remaining <= 0
        }


# Global singleton timer instance
competition_timer = CompetitionTimer()
