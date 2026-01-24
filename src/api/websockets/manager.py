"""WebSocket connection manager for real-time updates."""

import asyncio
import json
from typing import Any, Dict, Optional, Set

import redis.asyncio as aioredis
from fastapi import WebSocket
from loguru import logger

from src.core.config import Config


class ConnectionManager:
    """Manages WebSocket connections for real-time updates.

    Maintains active connections per user and provides methods to
    broadcast events to specific users or all connected users.
    """

    def __init__(self):
        """Initialize connection manager with empty active connections."""
        # active_connections[user_id] = Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        self.subscription_tasks: Dict[str, asyncio.Task] = {}  # user_id -> Task

    async def initialize_redis(self) -> None:
        """Initialize Redis connection for pub/sub."""
        if Config.USE_CELERY_TASKS and self.redis_client is None:
            try:
                self.redis_client = await aioredis.from_url(
                    Config.CELERY_BROKER_URL, decode_responses=True
                )
                logger.info("Redis pub/sub connection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")

    async def _subscribe_to_user_channel(self, user_id: str) -> None:  # noqa: C901
        """
        Subscribe to Redis pub/sub channel for user and forward to WebSockets.

        Args:
            user_id: The user ID to subscribe for
        """
        if self.redis_client is None:
            await self.initialize_redis()

        if self.redis_client is None:
            logger.error("Redis client not available for subscription")
            return

        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(f"ws:user:{user_id}")
            logger.info(f"Subscribed to Redis channel: ws:user:{user_id}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        await self._send_to_user_websockets(
                            user_id=user_id,
                            event_type=event_data.get("type"),
                            data=event_data.get("data"),
                        )
                    except Exception as e:
                        logger.error(f"Failed to process Redis message: {e}")
        except asyncio.CancelledError:
            logger.info(f"Unsubscribing from Redis channel: ws:user:{user_id}")
            try:
                await pubsub.unsubscribe(f"ws:user:{user_id}")
                await pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing pubsub: {e}")
        except Exception as e:
            logger.error(f"Error in Redis subscription: {e}")

    async def _send_to_user_websockets(self, user_id: str, event_type: str, data: dict) -> None:
        """
        Send message to all WebSocket connections for user.

        Args:
            user_id: The user ID
            event_type: Type of event
            data: Event data payload
        """
        if user_id not in self.active_connections:
            return

        message = {"type": event_type, "data": data}
        disconnected = set()

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)

        for websocket in disconnected:
            self.disconnect(websocket, user_id)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection object
            user_id: The user ID associated with this connection

        Raises:
            Exception: If accept() fails or other connection errors
        """
        await websocket.accept()

        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": None,  # Timestamp would be set by caller
        }

        logger.info(
            f"WebSocket connection established for user {user_id} "
            f"(active connections: {len(self.active_connections[user_id])})"
        )

        # Start Redis subscription task if not already running
        if Config.USE_CELERY_TASKS and user_id not in self.subscription_tasks:
            task = asyncio.create_task(self._subscribe_to_user_channel(user_id))
            self.subscription_tasks[user_id] = task

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            websocket: The WebSocket connection object
            user_id: The user ID associated with this connection
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Clean up empty user sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

                # Cancel subscription task if no more connections for user
                if user_id in self.subscription_tasks:
                    self.subscription_tasks[user_id].cancel()
                    del self.subscription_tasks[user_id]

        # Clean up metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        logger.info(f"WebSocket connection closed for user {user_id}")

    async def broadcast_to_user(
        self,
        user_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Broadcast an event to all connections for a specific user.

        Args:
            user_id: The user ID to broadcast to
            event_type: Type of event (e.g., 'sync.started', 'sync.progress')
            data: Event data payload

        Example:
            await manager.broadcast_to_user(
                user_id="user-123",
                event_type="sync.started",
                data={"sync_id": "sync-456", "sync_type": "full"}
            )
        """
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return

        message = {
            "type": event_type,
            "data": data,
        }

        # Send to all connections for this user
        disconnected = set()
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message)
                logger.debug(f"Sent {event_type} event to user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                disconnected.add(websocket)

        # Clean up disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket, user_id)

    async def broadcast_to_all(
        self,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Broadcast an event to all connected users.

        Args:
            event_type: Type of event
            data: Event data payload

        Example:
            await manager.broadcast_to_all(
                event_type="system.maintenance",
                data={"message": "System maintenance starting"}
            )
        """
        message = {
            "type": event_type,
            "data": data,
        }

        disconnected = []
        for user_id, connections in list(self.active_connections.items()):
            for websocket in list(connections):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    disconnected.append((websocket, user_id))

        # Clean up disconnected connections
        for websocket, user_id in disconnected:
            self.disconnect(websocket, user_id)

    async def send_to_connection(
        self,
        websocket: WebSocket,
        event_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Send an event to a specific connection.

        Args:
            websocket: The WebSocket connection
            event_type: Type of event
            data: Event data payload

        Returns:
            True if successful, False if connection failed

        Example:
            await manager.send_to_connection(
                websocket=ws,
                event_type="pong",
                data={"timestamp": time.time()}
            )
        """
        try:
            message = {
                "type": event_type,
                "data": data,
            }
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send message to connection: {e}")
            return False

    def get_user_connection_count(self, user_id: str) -> int:
        """
        Get the number of active connections for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections.get(user_id, set()))

    def get_total_connection_count(self) -> int:
        """
        Get the total number of active connections.

        Returns:
            Total number of active WebSocket connections across all users
        """
        return sum(len(conns) for conns in self.active_connections.values())

    def get_active_users(self) -> list[str]:
        """
        Get list of user IDs with active connections.

        Returns:
            List of user IDs with at least one active connection
        """
        return list(self.active_connections.keys())


# Global connection manager instance
ws_manager = ConnectionManager()
