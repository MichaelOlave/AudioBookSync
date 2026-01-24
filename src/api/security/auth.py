"""JWT token creation, validation, and dependency injection for FastAPI."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import Config
from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import user_service

# OAuth2 scheme for automatic Swagger documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token.

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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire,
            "type": "access",  # Token type for validation
            "iat": datetime.now(timezone.utc),  # Issued at
            "jti": str(uuid.uuid4()),  # JWT ID for uniqueness
        }
    )

    # Sign the token
    encoded_jwt = cast(
        str,
        jwt.encode(
            to_encode,
            Config.SECRET_KEY,
            algorithm=Config.ALGORITHM,
        ),
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token.

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
    expire = datetime.now(timezone.utc) + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",  # Token type for validation
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
        }
    )

    encoded_jwt = cast(
        str,
        jwt.encode(
            to_encode,
            Config.SECRET_KEY,
            algorithm=Config.ALGORITHM,
        ),
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary containing the decoded token claims

    Raises:
        HTTPException: If token is invalid, expired, or malformed
    """
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=[Config.ALGORITHM],
            ),
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Fastapi dependency to get the current authenticated user from JWT token.

    This function is used as a dependency injection in route handlers to
    ensure the request is authenticated and extract user information.

    Args:
        token: JWT token from Authorization header (automatically extracted)
        db: Database session (automatically injected)

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
        if token_type != "access":  # nosec B105
            logger.warning(f"Invalid token type: {token_type}")
            raise credentials_exception

    except HTTPException:
        raise

    # Fetch user from database using async service
    user = await user_service.get_user_by_id(db, user_id)

    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user
