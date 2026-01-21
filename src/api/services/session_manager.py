"""Session management for authentication flows."""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from ..schemas.credentials import AuthSessionData


class SessionManager:
    """Manages authentication session data persistence."""

    def __init__(self, session_dir: Path = None):
        """
        Initialize SessionManager.

        Args:
            session_dir: Directory to store session files. Defaults to logs/auth_sessions.
        """
        self.session_dir = session_dir or Path("logs") / "auth_sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, user_id: str, session_data: AuthSessionData) -> None:
        """
        Save auth session data to disk.

        Args:
            user_id: The user ID
            session_data: Session data to save

        Raises:
            Exception: If session cannot be saved
        """
        user_id_str = str(user_id)
        session_file = self.session_dir / f"{user_id_str}.json"
        try:
            session_file.write_text(session_data.model_dump_json())
            logger.info(f"Saved auth session for user {user_id_str} to {session_file}")
        except Exception as e:
            logger.error(f"Failed to save session for user {user_id_str}: {e}")
            raise

    def load_session(self, user_id: str) -> Optional[AuthSessionData]:
        """
        Load auth session data from disk.

        Args:
            user_id: The user ID

        Returns:
            AuthSessionData if session exists, None otherwise
        """
        user_id_str = str(user_id)
        session_file = self.session_dir / f"{user_id_str}.json"
        logger.info(
            f"Looking for session file: {session_file} (exists: {session_file.exists()})"
        )
        if not session_file.exists():
            logger.warning(
                f"No session file found for user {user_id_str} at {session_file}"
            )
            # List all session files for debugging
            session_files = list(self.session_dir.glob("*.json"))
            logger.info(f"Available session files: {[f.name for f in session_files]}")
            return None
        try:
            data = json.loads(session_file.read_text())
            logger.info(f"Successfully loaded session for user {user_id_str}")
            return AuthSessionData(**data)
        except Exception as e:
            logger.error(f"Failed to load session for user {user_id_str}: {e}")
            return None

    def delete_session(self, user_id: str) -> None:
        """
        Delete auth session data from disk.

        Args:
            user_id: The user ID
        """
        user_id_str = str(user_id)
        session_file = self.session_dir / f"{user_id_str}.json"
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted auth session for user {user_id_str}")


# Global session manager instance
session_manager = SessionManager()
