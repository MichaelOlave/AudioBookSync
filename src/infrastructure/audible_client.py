"""Audible API client wrapper with async support."""

import asyncio
import concurrent.futures

import audible
from loguru import logger

from ..core.config import Config


def sync_get_library(client, num_results: int, response_groups: str, sort_by: str):
    """Synchronous method to get library from Audible."""
    return client.get(
        "1.0/library",
        num_results=num_results,
        response_groups=response_groups,
        sort_by=sort_by,
    )


class AsyncAudibleClient:
    """Wrapper for Audible client to ensure proper async context management."""

    def __init__(self, auth):
        """Initialize with Audible authentication."""
        self.auth = auth
        self.client = None
        self.executor = concurrent.futures.ThreadPoolExecutor()

    async def __aenter__(self):
        """Async context entry - create client in executor."""
        self.client = await asyncio.get_event_loop().run_in_executor(
            self.executor, audible.Client, self.auth
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Async context exit - cleanup executor."""
        if self.executor:
            self.executor.shutdown()
        return False

    async def get_library(self):
        """Async method to get library using thread executor."""
        return await asyncio.get_event_loop().run_in_executor(
            self.executor,
            sync_get_library,
            self.client,
            Config.AUDIBLE_NUM_RESULTS,
            Config.AUDIBLE_RESPONSE_GROUPS,
            Config.AUDIBLE_SORT_BY,
        )


def authenticate():
    """Authenticate with Audible using stored credentials."""
    try:
        auth = audible.Authenticator.from_file(Config.AUTH_FILE)
        return AsyncAudibleClient(auth)
    except FileNotFoundError:
        logger.error(f"Authentication file {Config.AUTH_FILE} not found.")
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise


async def login_and_save_auth(email: str, password: str, locale: str = "us") -> AsyncAudibleClient:
    """
    Perform interactive login with Audible and save auth file.

    Uses credential-based authentication flow.

    Args:
        email: Audible account email
        password: Audible account password
        locale: Audible locale code (default: "us")

    Returns:
        AsyncAudibleClient: Authenticated client instance

    Raises:
        Exception: If authentication fails
    """
    try:
        logger.info(f"Starting Audible login for locale: {locale}")
        # Use credential-based authentication
        auth = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: audible.Authenticator.from_login(email, password, locale=locale),
        )
        # Save auth file for future use
        auth.to_file(Config.AUTH_FILE)
        logger.info(f"Authentication successful. Auth file saved to {Config.AUTH_FILE}")
        return AsyncAudibleClient(auth)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise


async def get_activation_bytes(client: AsyncAudibleClient) -> str:
    """
    Retrieve activation bytes from Audible account.

    Activation bytes are required for DRM-protected audiobooks.

    Args:
        client: AsyncAudibleClient instance (must be authenticated)

    Returns:
        str: Activation bytes as hexadecimal string

    Raises:
        Exception: If activation bytes cannot be retrieved
    """
    try:
        if not client.client:
            logger.error("Client not initialized. Please use context manager.")
            raise RuntimeError("Client not initialized")

        logger.info("Retrieving activation bytes from Audible...")
        audible_client = client.client
        activation_bytes = await asyncio.get_event_loop().run_in_executor(
            client.executor,
            lambda: audible_client.get("1.0/content/activation/audible"),
        )

        if activation_bytes and "activation_bytes" in activation_bytes:
            bytes_hex = activation_bytes["activation_bytes"]
            logger.info("Successfully retrieved activation bytes")
            return bytes_hex
        else:
            logger.error("No activation bytes found in response")
            raise ValueError("Activation bytes not found in Audible response")
    except Exception as e:
        logger.error(f"Failed to retrieve activation bytes: {e}")
        raise
