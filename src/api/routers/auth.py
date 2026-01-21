"""Authentication endpoints (register, login, refresh tokens, Audible auth)."""

from typing import Dict, Optional
from urllib.parse import parse_qs

import audible
import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ...database.db_users import user_ops
from ...database.services import user_service
from ...database.engine import get_db_session
from ..schemas.auth import UserRegister, Token, RefreshTokenRequest, AuthStartRequest, AuthStartResponse, AuthCompleteRequest
from ..schemas.credentials import AudibleCredentialsUpdate, AuthSessionData
from ..schemas.user import UserResponse
from ..security.password import hash_password, verify_password
from ..security.auth import create_access_token, create_refresh_token, decode_token, get_current_user
from ..middleware.error_handler import ConflictError, AuthenticationError, InternalServerError, AuthorizationError, handle_route_errors
from ..services.session_manager import session_manager
from ..utils.auth_utils import normalize_activation_bytes, get_user_id
from audible.localization import Locale
from audible.login import build_oauth_url, create_code_verifier
from audible.register import register

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=("Create a new user account with username, email, and password"),
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "Username or email already exists"},
        422: {"description": "Validation error"},
    },
)
@handle_route_errors("register user")
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Register a new user account.

    Validates that username and email are unique, hashes the password,
    and creates a new user in the database.

    Args:
        user_data: Registration data (username, email, password)
        db: Database session

    Returns:
        UserResponse: Created user details (without password)

    Raises:
        ConflictError: If username or email already exists
        ValidationError: If input validation fails

    Example:
        POST /api/v1/auth/register
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "securepassword123"
        }
    """
    logger.info(
        f"Registration attempt for username: {user_data.username}, email: {user_data.email}"
    )

    # Check if username already exists
    existing_user = await user_service.get_user_by_username(db, user_data.username)
    if existing_user:
        logger.warning(
            f"Registration failed: Username already exists: {user_data.username}"
        )
        raise ConflictError(f"Username '{user_data.username}' is already taken")

    # Check if email already exists
    existing_email = await user_service.get_user_by_email(db, user_data.email)
    if existing_email:
        logger.warning(
            f"Registration failed: Email already registered: {user_data.email}"
        )
        raise ConflictError(f"Email '{user_data.email}' is already registered")

    # Hash the password
    password_hash = hash_password(user_data.password)

    # Create user in database
    user = await user_service.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
    )

    if not user:
        logger.error(f"Failed to create user in database: {user_data.username}")
        raise InternalServerError("Failed to create user")

    await db.commit()
    logger.info(
        f"User registered successfully: {user_data.username} (ID: {user.user_id})"
    )
    return UserResponse.from_orm(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Login with username and password",
    description=("Authenticate user and receive access and refresh tokens"),
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid credentials"},
    },
)
@handle_route_errors("login user")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
) -> Token:
    """
    Login with username and password.

    Verifies credentials and returns JWT access and refresh tokens.

    Args:
        form_data: OAuth2 password grant (username, password)
        db: Database session

    Returns:
        Token: Access and refresh tokens

    Raises:
        AuthenticationError: If username not found or password incorrect
        HTTPException: If user is inactive

    Example:
        POST /api/v1/auth/login
        Content-Type: application/x-www-form-urlencoded

        username=john_doe&password=securepassword123
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    # Get user by username
    user = await user_service.get_user_by_username(db, form_data.username)
    if not user:
        logger.warning(f"Login failed: User not found: {form_data.username}")
        raise AuthenticationError("Invalid username or password")

    # Verify password
    password_hash = user.password_hash
    if not password_hash or not verify_password(form_data.password, password_hash):
        logger.warning(f"Login failed: Invalid password for user: {form_data.username}")
        raise AuthenticationError("Invalid username or password")

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login failed: User account is inactive: {form_data.username}")
        raise AuthorizationError("User account is inactive")

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

    logger.info(
        f"User logged in successfully: {form_data.username} (ID: {user.user_id})"
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token",
    responses={
        200: {"description": "Token refresh successful"},
        401: {"description": "Invalid refresh token"},
    },
)
@handle_route_errors("refresh token")
async def refresh(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Token:
    """
    Refresh access token using refresh token.

    Validates the refresh token and returns new access and refresh tokens.

    Args:
        refresh_data: Refresh token request
        db: Database session

    Returns:
        Token: New access and refresh tokens

    Raises:
        AuthenticationError: If refresh token is invalid or expired
        HTTPException: If user not found or inactive

    Example:
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
    """
    logger.info("Token refresh attempt")

    # Decode and validate refresh token
    payload = decode_token(refresh_data.refresh_token)

    # Verify token type
    token_type = payload.get("type")
    if token_type != "refresh":
        logger.warning("Token refresh failed: Invalid token type")
        raise AuthenticationError("Invalid token type")

    # Extract user_id
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Token refresh failed: Missing user ID in token")
        raise AuthenticationError("Invalid token payload")

    # Verify user exists and is active
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        logger.warning(f"Token refresh failed: User not found: {user_id}")
        raise AuthenticationError("User not found")

    if not user.is_active:
        logger.warning(f"Token refresh failed: User is inactive: {user_id}")
        raise AuthorizationError("User account is inactive")

    # Create new tokens
    access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})

    logger.info(f"Token refreshed successfully for user: {user_id}")

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post(
    "/start",
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
    "/complete",
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
