"""User database operations."""

from typing import Dict, Optional
import json

import psycopg2
from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class UserOperations:
    """Database operations for user management."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_user(
        self,
        username: str,
        email: str,
        auth_file_path: str,
        activation_bytes: str,
    ) -> Optional[str]:
        """
        Create a new user.

        Args:
            username: User's username
            email: User's email address
            auth_file_path: Path to Audible authentication file
            activation_bytes: DRM activation bytes

        Returns:
            user_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, auth_file_path, activation_bytes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id
                """,
                    (username, email, auth_file_path, activation_bytes),
                )
                result = cursor.fetchone()

                user_id_value = None
                if result is not None:
                    # Support both mapping-style rows and plain tuples for easier testing.
                    if isinstance(result, dict):
                        user_id_value = result.get("user_id")
                    else:
                        try:
                            user_id_value = result[0]
                        except (TypeError, IndexError):
                            user_id_value = None

                user_id = str(user_id_value) if user_id_value is not None else None
                logger.info(f"Created user: {username} (ID: {user_id})")
                return user_id
        except psycopg2.IntegrityError as e:
            logger.error(f"User creation failed (duplicate): {e}")
            return None
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            User dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def update_user_last_sync(self, user_id: str) -> None:
        """
        Update user's last sync timestamp.

        Args:
            user_id: User's UUID
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET last_sync_date = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """,
                    (user_id,),
                )
                logger.info(f"Updated last sync for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update last sync: {e}")

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        Get user by user_id (UUID).

        Args:
            user_id: User's UUID

        Returns:
            User dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            User dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE email = %s",
                    (email,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    def create_user_with_password(
        self,
        username: str,
        email: str,
        password_hash: str,
        auth_file_path: Optional[str] = None,
        activation_bytes: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new user with password authentication.

        Args:
            username: User's username
            email: User's email address
            password_hash: Hashed password (from bcrypt)
            auth_file_path: Optional path to Audible authentication file
            activation_bytes: Optional DRM activation bytes

        Returns:
            user_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, auth_file_path, activation_bytes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING user_id
                """,
                    (username, email, password_hash, auth_file_path, activation_bytes),
                )
                result = cursor.fetchone()

                user_id_value = None
                if result is not None:
                    if isinstance(result, dict):
                        user_id_value = result.get("user_id")
                    else:
                        try:
                            user_id_value = result[0]
                        except (TypeError, IndexError):
                            user_id_value = None

                user_id = str(user_id_value) if user_id_value is not None else None
                logger.info(
                    f"Created user with password: {username} " f"(ID: {user_id})"
                )
                return user_id
        except psycopg2.IntegrityError as e:
            logger.error(f"User creation failed (duplicate): {e}")
            return None
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return None

    def update_user_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update user's password.

        Args:
            user_id: User's UUID
            password_hash: New password hash (from bcrypt)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """,
                    (password_hash, user_id),
                )
                logger.info(f"Updated password for user: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return False

    def update_audible_auth_json(
        self,
        user_id: str,
        auth_json: Dict,
        activation_bytes: Optional[str] = None,
    ) -> bool:
        """
        Update user's Audible auth.json data (parsed from file).

        Stores the complete auth.json structure along with activation bytes.
        Also extracts and stores commonly accessed fields for quick lookup.

        Args:
            user_id: User's UUID
            auth_json: Parsed auth.json dictionary with access_token, refresh_token, etc.
            activation_bytes: DRM activation bytes (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract commonly used fields
            audible_email = None
            device_name = None

            if "customer_info" in auth_json:
                audible_email = auth_json["customer_info"].get("account_email")

            if "device_info" in auth_json:
                device_name = auth_json["device_info"].get("device_name")

            # Store auth.json as JSON string
            auth_json_str = json.dumps(auth_json)

            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET
                        audible_auth_json = %s,
                        audible_email = %s,
                        audible_device_name = %s,
                        activation_bytes = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """,
                    (
                        auth_json_str,
                        audible_email,
                        device_name,
                        activation_bytes,
                        user_id,
                    ),
                )
                logger.info(
                    f"Updated Audible auth.json for user: {user_id} "
                    f"(email={audible_email}, device={device_name}, "
                    f"activation_bytes={bool(activation_bytes)})"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update auth.json for user {user_id}: {e}")
            return False

    def clear_audible_auth(self, user_id: str) -> bool:
        """
        Clear user's Audible authentication data.

        Sets all Audible-related fields to NULL.

        Args:
            user_id: User's UUID

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET
                        audible_auth_json = NULL,
                        audible_email = NULL,
                        audible_device_name = NULL,
                        activation_bytes = NULL,
                        auth_file_path = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """,
                    (user_id,),
                )
                logger.info(f"Cleared Audible authentication for user: {user_id}")
                return True
        except Exception as e:
            logger.error(
                f"Failed to clear Audible authentication for user {user_id}: {e}"
            )
            return False

    def get_audible_auth_json(self, user_id: str) -> Optional[Dict]:
        """
        Get user's stored Audible auth.json data (with tokens redacted).

        Args:
            user_id: User's UUID

        Returns:
            Dictionary with auth.json data or None if not found
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT audible_auth_json, audible_email, audible_device_name, activation_bytes
                    FROM users
                    WHERE user_id = %s
                """,
                    (user_id,),
                )
                result = cursor.fetchone()

                if not result:
                    return None

                auth_json_str = (
                    result.get("audible_auth_json")
                    if isinstance(result, dict)
                    else result[0]
                )

                if auth_json_str:
                    auth_json = json.loads(auth_json_str)
                    # Redact sensitive tokens
                    if "access_token" in auth_json:
                        auth_json["access_token"] = "****REDACTED****"
                    if "refresh_token" in auth_json:
                        auth_json["refresh_token"] = "****REDACTED****"
                    return auth_json

                return None
        except Exception as e:
            logger.error(f"Failed to get auth.json for user {user_id}: {e}")
            return None


# Singleton instance
user_ops = UserOperations()
