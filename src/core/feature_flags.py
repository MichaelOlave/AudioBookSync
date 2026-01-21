"""Feature flag management for ORM migration rollout.

This module provides a centralized way to manage feature flags for the ORM migration
with support for monitoring, logging, and fallback patterns.
"""

from enum import Enum
from typing import Any, Callable, Dict

from loguru import logger

from .config import Config


class FeatureFlag(Enum):
    """ORM migration feature flags."""

    METADATA = "USE_ORM_METADATA"
    USERS = "USE_ORM_USERS"
    SYNC = "USE_ORM_SYNC"
    BOOKS = "USE_ORM_BOOKS"
    GLOBAL = "USE_ORM_GLOBAL"


class FeatureFlagManager:
    """Manage feature flags with monitoring and logging support."""

    def __init__(self):
        """Initialize feature flag manager."""
        self._usage_stats: Dict[FeatureFlag, Dict[str, int]] = {
            flag: {"enabled": 0, "disabled": 0} for flag in FeatureFlag
        }
        self._errors: Dict[FeatureFlag, int] = {flag: 0 for flag in FeatureFlag}

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """Check if a feature flag is enabled.

        Args:
            flag: Feature flag to check

        Returns:
            True if enabled, False otherwise
        """
        # Global master switch takes precedence
        if not self._get_config_value(FeatureFlag.GLOBAL):
            self._record_usage(flag, False)
            return False

        is_enabled = self._get_config_value(flag)
        self._record_usage(flag, is_enabled)

        if Config.LOG_FEATURE_FLAGS:
            status = "enabled" if is_enabled else "disabled"
            logger.debug(f"Feature flag {flag.value} is {status}")

        return is_enabled

    def is_disabled(self, flag: FeatureFlag) -> bool:
        """Check if a feature flag is disabled (inverse of is_enabled).

        Args:
            flag: Feature flag to check

        Returns:
            True if disabled, False otherwise
        """
        return not self.is_enabled(flag)

    def with_fallback(
        self,
        flag: FeatureFlag,
        orm_func: Callable[..., Any],
        sql_func: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Create a function that uses ORM or SQL based on feature flag.

        This decorator pattern allows graceful fallback from ORM to raw SQL
        if needed during gradual rollout.

        Args:
            flag: Feature flag to check
            orm_func: Function to call if flag is enabled (ORM implementation)
            sql_func: Function to call if flag is disabled (SQL implementation)

        Returns:
            A wrapper function that delegates to appropriate implementation
        """

        async def async_wrapper(*args, **kwargs):
            """Async wrapper for fallback pattern."""
            try:
                if self.is_enabled(flag):
                    return await orm_func(*args, **kwargs)
                else:
                    return await sql_func(*args, **kwargs)
            except Exception as e:
                self._record_error(flag)
                logger.error(f"Error in {flag.value}: {str(e)}. Attempting fallback...")
                # If ORM failed, try SQL fallback
                if self.is_enabled(flag):
                    logger.warning(f"ORM failed for {flag.value}, falling back to SQL")
                    return await sql_func(*args, **kwargs)
                else:
                    raise

        def sync_wrapper(*args, **kwargs):
            """Sync wrapper for fallback pattern."""
            try:
                if self.is_enabled(flag):
                    return orm_func(*args, **kwargs)
                else:
                    return sql_func(*args, **kwargs)
            except Exception as e:
                self._record_error(flag)
                logger.error(f"Error in {flag.value}: {str(e)}. Attempting fallback...")
                # If ORM failed, try SQL fallback
                if self.is_enabled(flag):
                    logger.warning(f"ORM failed for {flag.value}, falling back to SQL")
                    return sql_func(*args, **kwargs)
                else:
                    raise

        # Return appropriate wrapper based on orm_func type
        if hasattr(orm_func, "__await__") or hasattr(orm_func, "__aenter__"):
            return async_wrapper
        else:
            return sync_wrapper

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get feature flag usage statistics.

        Returns:
            Dictionary with usage stats for each flag
        """
        stats = {}
        for flag in FeatureFlag:
            total = self._usage_stats[flag]["enabled"] + self._usage_stats[flag]["disabled"]
            if total > 0:
                enabled_pct = (self._usage_stats[flag]["enabled"] / total) * 100
            else:
                enabled_pct = 0
            stats[flag.value] = {
                "enabled_count": self._usage_stats[flag]["enabled"],
                "disabled_count": self._usage_stats[flag]["disabled"],
                "total_checks": total,
                "enabled_percentage": enabled_pct,
                "errors": self._errors[flag],
            }
        return stats

    def get_status_summary(self) -> Dict[str, Any]:
        """Get current feature flag status summary.

        Returns:
            Dictionary with current status of all flags
        """
        return {
            "global_enabled": self._get_config_value(FeatureFlag.GLOBAL),
            "flags": {
                "metadata": self._get_config_value(FeatureFlag.METADATA),
                "users": self._get_config_value(FeatureFlag.USERS),
                "sync": self._get_config_value(FeatureFlag.SYNC),
                "books": self._get_config_value(FeatureFlag.BOOKS),
            },
            "rollout_stage": self._get_rollout_stage(),
        }

    def reset_stats(self) -> None:
        """Reset usage statistics for monitoring."""
        for flag in FeatureFlag:
            self._usage_stats[flag] = {"enabled": 0, "disabled": 0}
            self._errors[flag] = 0

    def _get_config_value(self, flag: FeatureFlag) -> bool:
        """Get feature flag value from config.

        Args:
            flag: Feature flag to get

        Returns:
            Feature flag value
        """
        if flag == FeatureFlag.GLOBAL:
            return Config.USE_ORM_GLOBAL
        elif flag == FeatureFlag.METADATA:
            return Config.USE_ORM_METADATA
        elif flag == FeatureFlag.USERS:
            return Config.USE_ORM_USERS
        elif flag == FeatureFlag.SYNC:
            return Config.USE_ORM_SYNC
        elif flag == FeatureFlag.BOOKS:
            return Config.USE_ORM_BOOKS
        return False

    def _record_usage(self, flag: FeatureFlag, is_enabled: bool) -> None:
        """Record feature flag usage for monitoring.

        Args:
            flag: Feature flag being used
            is_enabled: Whether the flag is enabled
        """
        key = "enabled" if is_enabled else "disabled"
        self._usage_stats[flag][key] += 1

    def _record_error(self, flag: FeatureFlag) -> None:
        """Record error for feature flag.

        Args:
            flag: Feature flag that errored
        """
        self._errors[flag] += 1

    def _get_rollout_stage(self) -> str:
        """Determine current rollout stage based on enabled flags.

        Returns:
            Current rollout stage name
        """
        if not self._get_config_value(FeatureFlag.GLOBAL):
            return "DISABLED"
        if self._get_config_value(FeatureFlag.METADATA) and not self._get_config_value(
            FeatureFlag.USERS
        ):
            return "STAGE_1_METADATA"
        if (
            self._get_config_value(FeatureFlag.USERS)
            and self._get_config_value(FeatureFlag.SYNC)
            and not self._get_config_value(FeatureFlag.BOOKS)
        ):
            return "STAGE_2_USERS_SYNC"
        if self._get_config_value(FeatureFlag.BOOKS):
            return "STAGE_3_FULL_ORM"
        return "MIXED"


# Global feature flag manager instance
feature_flags = FeatureFlagManager()


# Convenience functions for checking flags
def is_orm_metadata_enabled() -> bool:
    """Check if ORM metadata operations are enabled."""
    return feature_flags.is_enabled(FeatureFlag.METADATA)


def is_orm_users_enabled() -> bool:
    """Check if ORM user operations are enabled."""
    return feature_flags.is_enabled(FeatureFlag.USERS)


def is_orm_sync_enabled() -> bool:
    """Check if ORM sync operations are enabled."""
    return feature_flags.is_enabled(FeatureFlag.SYNC)


def is_orm_books_enabled() -> bool:
    """Check if ORM book operations are enabled."""
    return feature_flags.is_enabled(FeatureFlag.BOOKS)


def is_orm_disabled() -> bool:
    """Check if ORM is globally disabled."""
    return feature_flags.is_disabled(FeatureFlag.GLOBAL)
