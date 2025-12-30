"""JWT token creation, validation, and dependency injection for FastAPI."""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger

from ...core.config import Config
from ...database.db_users import user_ops

# OAuth2 scheme for automatic Swagger documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing token claims (typically {"sub": user_id})
        expires_delta: Optional timedelta for token expiration

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "user-uuid"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire,
            "type": "access",  # Token type for validation
            "iat": datetime.utcnow(),  # Issued at
            "jti": str(uuid.uuid4()),  # JWT ID for uniqueness
        }
    )

    # Sign the token
    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Dictionary containing token claims (typically {"sub": user_id})

    Returns:
        Encoded JWT refresh token string

    Tokens:
        Refresh tokens are long-lived and used to obtain new access tokens
        without requiring the user to log in again.
    """
    to_encode = data.copy()

    # Refresh tokens are longer-lived
    expire = datetime.utcnow() + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",  # Token type for validation
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM,
    )

    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary containing the decoded token claims

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency to get the current authenticated user from JWT token.

    This function is used as a dependency injection in route handlers to
    ensure the request is authenticated and extract user information.

    Args:
        token: JWT token from Authorization header (automatically extracted)

    Returns:
        User dictionary from database

    Raises:
        HTTPException: If token is invalid, expired, or user not found

    Example:
        ```python
        @app.get("/me")
        async def get_profile(current_user: dict = Depends(get_current_user)):
            return current_user
        ```
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode token
        payload = decode_token(token)

        # Extract user_id from 'sub' claim
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception

        # Verify token type
        token_type: Optional[str] = payload.get("type")
        if token_type != "access":
            logger.warning(f"Invalid token type: {token_type}")
            raise credentials_exception

    except HTTPException:
        raise

    # Fetch user from database
    user = user_ops.get_user_by_id(user_id)

    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise credentials_exception

    # Check if user is active
    if not user.get("is_active", True):
        logger.warning(f"Inactive user attempted access: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Dependency to ensure current user is active.

    This is a convenience wrapper around get_current_user for routes that
    specifically need to verify the user is active.

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Current user if active

    Raises:
        HTTPException: If user is inactive
    """
    return current_user
