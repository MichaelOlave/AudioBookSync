"""Authentication endpoints (register, login, refresh tokens)."""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger

from ...database.db_users import user_ops
from ..schemas.auth import UserRegister, Token, RefreshTokenRequest
from ..schemas.user import UserResponse
from ..security.password import hash_password, verify_password
from ..security.auth import create_access_token, create_refresh_token, decode_token
from ..middleware.error_handler import ConflictError, AuthenticationError

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
async def register(user_data: UserRegister) -> UserResponse:
    """
    Register a new user account.

    Validates that username and email are unique, hashes the password,
    and creates a new user in the database.

    Args:
        user_data: Registration data (username, email, password)

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
    existing_user = user_ops.get_user_by_username(user_data.username)
    if existing_user:
        logger.warning(
            f"Registration failed: Username already exists: {user_data.username}"
        )
        raise ConflictError(f"Username '{user_data.username}' is already taken")

    # Check if email already exists
    existing_email = user_ops.get_user_by_email(user_data.email)
    if existing_email:
        logger.warning(
            f"Registration failed: Email already registered: {user_data.email}"
        )
        raise ConflictError(f"Email '{user_data.email}' is already registered")

    # Hash the password
    try:
        password_hash = hash_password(user_data.password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process registration",
        )

    # Create user in database
    try:
        user_id = user_ops.create_user_with_password(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
        )

        if not user_id:
            logger.error(f"Failed to create user in database: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

        # Fetch and return created user
        user = user_ops.get_user_by_id(user_id)
        if not user:
            logger.error(f"Created user not found in database: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created user",
            )

        logger.info(
            f"User registered successfully: {user_data.username} (ID: {user_id})"
        )
        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


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
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Login with username and password.

    Verifies credentials and returns JWT access and refresh tokens.

    Args:
        form_data: OAuth2 password grant (username, password)

    Returns:
        Token: Access and refresh tokens

    Raises:
        AuthenticationError: If username not found or password incorrec
        HTTPException: If user is inactive

    Example:
        POST /api/v1/auth/login
        Content-Type: application/x-www-form-urlencoded

        username=john_doe&password=securepassword123
    """
    logger.info(f"Login attempt for user: {form_data.username}")

    # Get user by username
    user = user_ops.get_user_by_username(form_data.username)
    if not user:
        logger.warning(f"Login failed: User not found: {form_data.username}")
        raise AuthenticationError("Invalid username or password")

    # Verify password
    password_hash = user.get("password_hash")
    if not password_hash or not verify_password(form_data.password, password_hash):
        logger.warning(f"Login failed: Invalid password for user: {form_data.username}")
        raise AuthenticationError("Invalid username or password")

    # Check if user is active
    if not user.get("is_active", True):
        logger.warning(f"Login failed: User account is inactive: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create tokens
    try:
        access_token = create_access_token(data={"sub": str(user["user_id"])})
        refresh_token = create_refresh_token(data={"sub": str(user["user_id"])})

        logger.info(
            f"User logged in successfully: {form_data.username} (ID: {user['user_id']})"
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tokens",
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
async def refresh(refresh_data: RefreshTokenRequest) -> Token:
    """
    Refresh access token using refresh token.

    Validates the refresh token and returns new access and refresh tokens.

    Args:
        refresh_data: Refresh token reques

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

    try:
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
        user = user_ops.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Token refresh failed: User not found: {user_id}")
            raise AuthenticationError("User not found")

        if not user.get("is_active", True):
            logger.warning(f"Token refresh failed: User is inactive: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Create new tokens
        access_token = create_access_token(data={"sub": user_id})
        new_refresh_token = create_refresh_token(data={"sub": user_id})

        logger.info(f"Token refreshed successfully for user: {user_id}")

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    except AuthenticationError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise AuthenticationError("Failed to refresh token")
