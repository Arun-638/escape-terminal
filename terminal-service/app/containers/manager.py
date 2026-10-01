"""
Container Lifecycle Manager
===========================
Provisions, monitors, and resets isolated Docker containers per team.
Enforces resource limits, capabilities dropping, and network isolation.
"""

import logging
import os
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("terminal.containers")

try:
    import docker
    from docker.errors import NotFound, APIError
    docker_available = True
except ImportError:
    docker_available = False


class ContainerManager:
    def __init__(self):
        self.client = None
        self._init_docker()

    def _init_docker(self):
        if not docker_available:
            logger.warning("Docker SDK is not available.")
            return

        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Connected to Docker daemon successfully.")
        except Exception as e:
            logger.warning(f"Could not connect to Docker daemon: {e}. Running in simulated mode.")
            self.client = None

    @property
    def is_docker_connected(self) -> bool:
        return self.client is not None

    def get_container_name(self, team_id: int) -> str:
        return f"{settings.CONTAINER_PREFIX}{team_id:02d}"

    def get_or_create_team_container(self, team_id: int) -> Dict[str, Any]:
        """
        Ensure the container for team_id exists and is running.
        Returns metadata dict with container ID, status, and name.
        """
        container_name = self.get_container_name(team_id)

        if not self.is_docker_connected:
            # Simulated container descriptor for testing when Docker daemon is absent
            return {
                "id": f"simulated-{container_name}",
                "name": container_name,
                "status": "running",
                "team_id": team_id,
                "simulated": True
            }

        try:
            # Check if container already exists
            container = self.client.containers.get(container_name)
            if container.status != "running":
                logger.info(f"Restarting stopped container {container_name}...")
                container.start()
            return {
                "id": container.id,
                "name": container_name,
                "status": container.status,
                "team_id": team_id,
                "simulated": False
            }
        except NotFound:
            # Create a brand new isolated sandbox container
            logger.info(f"Creating new hardened sandbox container: {container_name}")
            return self._create_container(team_id, container_name)

    def _create_container(self, team_id: int, container_name: str) -> Dict[str, Any]:
        # Security constraints
        cpu_quota = int(settings.CONTAINER_CPU * 100000)
        
        env_vars = {
            "TEAM_ID": str(team_id),
            "SERVER_SECRET": settings.SERVER_SECRET,
            "COMPETITION_ID": settings.COMPETITION_ID,
            "TERM": "xterm-256color"
        }

        try:
            container = self.client.containers.run(
                image=settings.DOCKER_IMAGE,
                name=container_name,
                detach=True,
                tty=True,
                stdin_open=True,
                environment=env_vars,
                user="player",
                network_mode="none",  # Full network isolation
                mem_limit=settings.CONTAINER_MEMORY,
                cpu_period=100000,
                cpu_quota=cpu_quota,
                pids_limit=settings.CONTAINER_PIDS,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                restart_policy={"Name": "unless-stopped"}
            )
            return {
                "id": container.id,
                "name": container_name,
                "status": "running",
                "team_id": team_id,
                "simulated": False
            }
        except Exception as e:
            logger.error(f"Failed to create team container {container_name}: {e}")
            raise RuntimeError(f"Could not provision team container: {e}")

    def reset_team_container(self, team_id: int) -> bool:
        """
        Safely destroy and recreate the team container, restoring deterministic puzzle state.
        """
        container_name = self.get_container_name(team_id)
        if not self.is_docker_connected:
            return True

        try:
            try:
                container = self.client.containers.get(container_name)
                logger.info(f"Stopping & removing container {container_name} for reset...")
                container.stop(timeout=2)
                container.remove(force=True)
            except NotFound:
                pass

            self._create_container(team_id, container_name)
            logger.info(f"Container {container_name} successfully reset.")
            return True
        except Exception as e:
            logger.error(f"Error resetting container {container_name}: {e}")
            return False

    def stop_team_container(self, team_id: int) -> bool:
        """Stop a specific team container."""
        container_name = self.get_container_name(team_id)
        if not self.is_docker_connected:
            return True

        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=2)
            return True
        except NotFound:
            return True
        except Exception as e:
            logger.error(f"Error stopping container {container_name}: {e}")
            return False


container_manager = ContainerManager()
