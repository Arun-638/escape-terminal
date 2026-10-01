"""
Escape The Terminal — Terminal Service Configuration
"""

import os
from pydantic import BaseModel


class Settings(BaseModel):
    APP_NAME: str = "Escape The Terminal Service"
    SERVER_SECRET: str = os.getenv("SERVER_SECRET", "escape_master_secret_lan")
    COMPETITION_ID: str = os.getenv("COMPETITION_ID", "escape2026")
    CTFD_URL: str = os.getenv("CTFD_URL", "http://ctfd:8000")
    
    # Docker sandbox specifications
    DOCKER_IMAGE: str = os.getenv("DOCKER_IMAGE", "escape-sandbox:latest")
    CONTAINER_PREFIX: str = "escape-team-"
    CONTAINER_CPU: float = float(os.getenv("CONTAINER_CPU", "0.5"))
    CONTAINER_MEMORY: str = os.getenv("CONTAINER_MEMORY", "256m")
    CONTAINER_PIDS: int = int(os.getenv("CONTAINER_PIDS", "100"))
    
    # Timeouts & limits
    SESSION_TIMEOUT_SECONDS: int = int(os.getenv("SESSION_TIMEOUT_SECONDS", "3600"))
    MAX_TEAMS: int = int(os.getenv("MAX_TEAMS", "40"))


settings = Settings()
