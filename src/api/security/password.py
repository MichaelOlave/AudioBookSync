"""Password hashing and verification using bcrypt."""

from typing import cast

from passlib.context import CryptContext

# Create bcrypt context with sensible defaults
# cost=12 (default) provides good security-performance tradeoff
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",  # Auto-upgrade deprecated algorithms
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash

    Returns:
        The bcrypt hash string

    Example:
        >>> hash_pwd = hash_password("mypassword123")
        >>> verify_password("mypassword123", hash_pwd)
        True
    """
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password to verify
        hashed_password: The bcrypt hash to verify against

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hash_pwd = hash_password("mypassword123")
        >>> verify_password("mypassword123", hash_pwd)
        True
        >>> verify_password("wrongpassword", hash_pwd)
        False
    """
    return bool(pwd_context.verify(plain_password, hashed_password))
