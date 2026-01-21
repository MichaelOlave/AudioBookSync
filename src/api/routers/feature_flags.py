"""Feature flag monitoring endpoints.

Provides endpoints for monitoring ORM migration rollout status and statistics.
"""

from fastapi import APIRouter, Depends, status

from src.api.security.auth import get_current_user
from src.core.feature_flags import feature_flags
from src.database.models import User

router = APIRouter(
    prefix="/api/v1/feature-flags",
    tags=["feature-flags"],
)


@router.get(
    "/status",
    summary="Get feature flag status",
    description="Get current status of all ORM feature flags",
    status_code=status.HTTP_200_OK,
)
async def get_feature_flag_status(current_user: User = Depends(get_current_user)):
    """Get current feature flag status.

    Returns current enabled/disabled status of all ORM feature flags and
    the current rollout stage.

    Args:
        current_user: Current authenticated user (admin only recommended)

    Returns:
        Feature flag status dictionary
    """
    return feature_flags.get_status_summary()


@router.get(
    "/stats",
    summary="Get feature flag usage statistics",
    description="Get detailed statistics on feature flag usage",
    status_code=status.HTTP_200_OK,
)
async def get_feature_flag_stats(current_user: User = Depends(get_current_user)):
    """Get feature flag usage statistics.

    Returns detailed usage statistics including:
    - Number of times each flag was enabled/disabled
    - Percentage of enabled usage
    - Error counts

    Args:
        current_user: Current authenticated user (admin only recommended)

    Returns:
        Usage statistics dictionary
    """
    return feature_flags.get_usage_stats()


@router.post(
    "/stats/reset",
    summary="Reset feature flag statistics",
    description="Reset usage statistics (admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_feature_flag_stats(current_user: User = Depends(get_current_user)):
    """Reset feature flag usage statistics.

    This resets all collected statistics counters. Useful for benchmarking
    specific operations during testing.

    Args:
        current_user: Current authenticated user (admin only recommended)

    Returns:
        No content
    """
    feature_flags.reset_stats()
