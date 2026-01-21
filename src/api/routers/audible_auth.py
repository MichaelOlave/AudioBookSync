"""Audible OAuth-style authentication endpoints.

These endpoints allow a user to authenticate with Audible in the browser and
store the resulting credentials in the database for later use.
"""

from typing import Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ..middleware.error_handler import handle_route_errors
from ..schemas.auth import AuthCompleteRequest, AuthStartRequest, AuthStartResponse
from ..schemas.credentials import AudibleCredentialsUpdate
from ..security.auth import get_current_user
from ..services.audible_auth_service import complete_audible_auth_flow, start_audible_auth_flow
from ..utils.auth_utils import get_user_id

router = APIRouter()


@router.post(
    "/auth/start",
    response_model=AuthStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Audible authentication",
    description="Generate a browser login URL for Audible and start an auth session.",
)
@handle_route_errors("start Audible auth")
async def start_audible_auth(
    request: AuthStartRequest,
    current_user: Dict = Depends(get_current_user),
) -> AuthStartResponse:
    """
    Start the Audible authentication process by generating a login URL.

    The login session is tied to the current user and stored in-memory
    until the flow is completed via `/auth/complete`.
    """
    user_id = get_user_id(current_user)
    return await start_audible_auth_flow(user_id, request.country_code)


@router.post(
    "/auth/complete",
    response_model=AudibleCredentialsUpdate,
    status_code=status.HTTP_200_OK,
    summary="Complete Audible authentication",
    description=(
        "Complete the Audible authentication flow using the browser redirect URL, "
        "save auth.json to disk, and persist credentials in the database."
    ),
)
@handle_route_errors("complete Audible auth")
async def complete_audible_auth(
    request: AuthCompleteRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AudibleCredentialsUpdate:
    """
    Complete the Audible authentication using the redirect URL from the browser.

    This will:
    - Finish the Audible login flow for the current user
    - Save the auth file to `Config.AUTH_FILE` for compatibility with existing tools
    - Store the parsed auth.json and activation bytes in the database
    """
    user_id = get_user_id(current_user)
    return await complete_audible_auth_flow(db, user_id, request.redirect_url)
