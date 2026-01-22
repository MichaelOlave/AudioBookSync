"""Redis pub/sub progress publisher for Celery tasks."""

import json
from datetime import datetime, timezone

import redis
from loguru import logger

from src.core.config import Config

# Sync Redis client for Celery tasks
redis_client = redis.from_url(Config.CELERY_BROKER_URL, decode_responses=True)


def publish_progress(user_id: str, event_type: str, data: dict) -> None:
    """
    Publish progress event to Redis pub/sub channel for WebSocket delivery.

    Args:
        user_id: User ID to publish to
        event_type: Type of event (e.g., 'download.progress', 'sync.completed')
        data: Event data payload
    """
    try:
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).timestamp()

        message = json.dumps({"type": event_type, "data": data})

        redis_client.publish(f"ws:user:{user_id}", message)
        logger.debug(f"Published {event_type} to Redis for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to publish progress to Redis: {e}")
