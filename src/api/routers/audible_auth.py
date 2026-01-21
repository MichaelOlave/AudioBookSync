"""Audible OAuth-style authentication endpoints.

These endpoints allow a user to authenticate with Audible in the browser and
store the resulting credentials in the database for later use.
"""

from typing import Dict
from urllib.parse import parse_qs

import audible
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from ...database.db_users import user_ops
from ..schemas.auth import AuthStartRequest, AuthStartResponse, AuthCompleteRequest
from ..schemas.credentials import AudibleCredentialsUpdate, AuthSessionData
from ..security.auth import get_current_user
from ..middleware.error_handler import AuthenticationError, InternalServerError, handle_route_errors
from ..services.session_manager import session_manager
from ..utils.auth_utils import normalize_activation_bytes, get_user_id
from audible.localization import Locale
from audible.login import build_oauth_url, create_code_verifier
from audible.register import register

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
    if not user_id:
        raise AuthenticationError("User context is required to start Audible authentication")

    logger.info(f"Starting auth for user_id: {user_id} (type: {type(user_id)})")

    # Get locale information
    locale = Locale(country_code=request.country_code)

    # Generate code verifier and OAuth URL
    code_verifier = create_code_verifier()
    oauth_url, serial = build_oauth_url(
        country_code=locale.country_code,
        domain=locale.domain,
        market_place_id=locale.market_place_id,
        code_verifier=code_verifier,
    )

    # Store session data (keep code_verifier as bytes)
    session_data = AuthSessionData(
        country_code=request.country_code,
        code_verifier=code_verifier.decode("utf-8"),
        serial=serial,
    )
    session_manager.save_session(user_id, session_data)

    logger.info(
        f"Stored auth session for user {user_id} "
        f"(locale={request.country_code}, serial={serial})"
    )

    logger.info(
        f"Started Audible auth session for user {user_id} "
        f"(locale={request.country_code}), login_url generated."
    )
    return AuthStartResponse(login_url=oauth_url)


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
) -> AudibleCredentialsUpdate:
    """
    Complete the Audible authentication using the redirect URL from the browser.

    This will:
    - Finish the Audible login flow for the current user
    - Save the auth file to `Config.AUTH_FILE` for compatibility with existing tools
    - Store the parsed auth.json and activation bytes in the database
    """
    user_id = get_user_id(current_user)
    if not user_id:
        raise AuthenticationError("User context is required to complete Audible authentication")

    logger.info(f"Looking for auth session for user_id: {user_id}")

    session_data = session_manager.load_session(user_id)
    if not session_data:
        logger.error(
            f"No auth session found for user {user_id}. "
            f"Please call /auth/start first."
        )
        raise AuthenticationError("Authentication process not started. Please call /auth/start first")

    logger.info(f"Session data loaded successfully for user {user_id}")

    # Double-check session_data is not None
    if session_data is None:
        raise InternalServerError("Session data is unexpectedly None")

    # Get locale information
    logger.info(f"Getting locale for country_code: {session_data.country_code}")
    locale = Locale(country_code=session_data.country_code)

    # Parse the authorization code from the redirect URL
    logger.info(
        f"Parsing authorization code from redirect_url: "
        f"{request.redirect_url[:100]}..."
    )
    try:
        response_url = httpx.URL(request.redirect_url)
        parsed_url = parse_qs(response_url.query.decode())
        authorization_code = parsed_url["openid.oa2.authorization_code"][0]
        logger.info(
            f"Successfully extracted authorization code "
            f"(length: {len(authorization_code)})"
        )
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to parse authorization code from URL: {e}")
        raise AuthenticationError("Invalid redirect URL. Missing authorization code")

    # Prepare login device data using stored code_verifier
    login_device = {
        "authorization_code": authorization_code,
        "code_verifier": session_data.code_verifier.encode("utf-8"),
        "domain": locale.domain,
        "serial": session_data.serial,
    }
    logger.info("Login device data prepared")

    # Register the device and create Authenticator
    logger.info("Registering device...")
    register_device = register(
        with_username=False,  # Assuming not using username login for external flow
        **login_device,
    )
    logger.info("Device registration completed")

    authenticator = audible.Authenticator()
    authenticator.locale = locale  # Set the locale before saving
    authenticator._update_attrs(
        with_username=False,
        **register_device,
    )

    logger.info("Getting activation bytes...")
    activation_bytes_raw = None
    try:
        activation_bytes_raw = authenticator.get_activation_bytes()
    except Exception as exc:  # pragma: no cover - library-specific behavior
        logger.warning(f"Could not get activation bytes for user {user_id}: {exc}")

    activation_bytes = normalize_activation_bytes(activation_bytes_raw)
    if activation_bytes:
        logger.info(
            f"Retrieved activation bytes for user {user_id}: "
            f"{bool(activation_bytes)}"
        )

    # Get auth data directly from authenticator
    auth_json = authenticator.to_dict()
    logger.info("Converting authenticator to dict for database storage")

    # Save to database
    success = user_ops.update_audible_auth_json(
        user_id=user_id,
        auth_json=auth_json,
        activation_bytes=activation_bytes,
    )
    if not success:
        logger.error(f"Failed to persist Audible auth.json for user {user_id}")
        raise InternalServerError("Failed to save authentication data to database")

    logger.info(
        f"Completed Audible authentication for user {user_id}; "
        f"credentials saved to database"
    )

    try:
        return AudibleCredentialsUpdate(
            message="Authentication successful. Credentials saved to database.",
            auth_configured=True,
            auth_file_path=None,
        )
    finally:
        # Only clean up the session file if it was successfully loaded
        if session_data is not None:
            session_manager.delete_session(user_id)
        else:
            logger.warning(
                f"Session data was None, not deleting session file for user {user_id}"
            )
