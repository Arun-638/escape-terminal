"""
Rate Limiter & Abuse Prevention Module
======================================
In-memory sliding window rate limiter to guard challenge validation endpoints
against brute-force dictionary attacks during LAN competitions.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger("terminal.security.ratelimit")


class RateLimiter:
    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        """
        :param max_requests: Maximum allowed validation attempts in window
        :param window_seconds: Time window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # key: team_id or client_ip -> list of timestamps
        self.records: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if the request is permitted under rate limit.
        Returns:
            (allowed: bool, retry_after: int)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean timestamps older than window
        timestamps = [t for t in self.records[identifier] if t > window_start]
        self.records[identifier] = timestamps

        if len(timestamps) >= self.max_requests:
            oldest_in_window = timestamps[0]
            retry_after = int(oldest_in_window + self.window_seconds - now) + 1
            logger.warning(f"Rate limit exceeded for '{identifier}'. Attempts: {len(timestamps)}/{self.max_requests}")
            return False, max(1, retry_after)

        self.records[identifier].append(now)
        return True, 0

    def reset(self, identifier: str = None):
        """Reset rate limit history for a specific identifier or all."""
        if identifier:
            self.records.pop(identifier, None)
        else:
            self.records.clear()


# Global rate limiter instance for challenge validations
validation_limiter = RateLimiter(max_requests=15, window_seconds=60)
