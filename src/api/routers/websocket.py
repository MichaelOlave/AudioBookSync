"""WebSocket endpoints for real-time updates."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from ..security.auth import decode_token
from ..websockets import ws_manager

router = APIRouter()


@router.websocket("/updates")
async def websocket_updates(  # noqa: C901
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
) -> None:
    """Websocket endpoint for real-time sync and operation updates.

    Maintains a persistent WebSocket connection to receive real-time events
    including sync progress, download progress, and system notifications.

    Authentication:
        - Must provide valid JWT access token via query parameter
        - Token is validated before accepting the connection

    Events Received:
        - sync.started: Sync operation has started
        - sync.progress: Sync progress update
        - sync.completed: Sync operation completed successfully
        - sync.failed: Sync operation failed
        - download.progress: File download progress
        - error: Error even
        - message: System message

    Connection Management:
        - Connection is kept alive indefinitely until client disconnects
        - Server broadcasts events to all connected clients for a user
        - Disconnection is handled gracefully

    Example:
        ws://localhost:8000/api/v1/ws/updates?token=eyJ0eXAiOiJKV1QiLCJhbGc...

    Connection Flow:
        1. Client connects with valid JWT token
        2. Server authenticates token
        3. Connection is registered with connection manager
        4. Client receives real-time events
        5. Connection closes on client disconnect or error
    """
    user_id: str | None = None
    try:
        # Authenticate user via JWT token
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")

            if not user_id:
                logger.warning("WebSocket connection attempt: Missing user ID in token")
                await websocket.close(code=1008, reason="Invalid token")
                return

        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return

        logger.info(f"WebSocket connection established for user {user_id}")

        # Accept the connection and register with manager
        await ws_manager.connect(websocket, user_id)

        try:
            # Keep connection alive and wait for client messages
            while True:
                # Receive data from client (heartbeat or commands)
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "ping":
                        # Respond to heartbeat
                        await ws_manager.send_to_connection(
                            websocket,
                            "pong",
                            {"timestamp": datetime.now(timezone.utc).timestamp()},
                        )
                        logger.debug(f"WebSocket ping/pong for user {user_id}")

                    elif message_type == "heartbeat":
                        # Simple keep-alive
                        logger.debug(f"WebSocket heartbeat from user {user_id}")

                    else:
                        logger.debug(f"WebSocket message from user {user_id}: type={message_type}")

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from WebSocket user {user_id}")
                    await ws_manager.send_to_connection(
                        websocket,
                        "error",
                        {
                            "error": "Invalid message format",
                            "timestamp": datetime.now(timezone.utc).timestamp(),
                        },
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
            ws_manager.disconnect(websocket, user_id)

    except Exception as e:
        logger.error(f"WebSocket error for user: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception as close_error:
            logger.warning(f"Error closing WebSocket: {close_error}")
        finally:
            # Ensure connection is cleaned up
            if user_id is not None:
                try:
                    ws_manager.disconnect(websocket, user_id)
                except Exception as cleanup_error:
                    logger.warning(f"Error cleaning up WebSocket: {cleanup_error}")
