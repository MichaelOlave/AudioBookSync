"""Test data factories using async ORM services.

Provides factory classes for creating test data with the ORM.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.services import (
    book_service,
    metadata_service,
    sync_service,
    user_service,
)


class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    async def create(
        db: AsyncSession,
        username: str = "testuser",
        email: str = "test@example.com",
        auth_file_path: Optional[str] = None,
        activation_bytes: Optional[str] = None,
    ):
        """Create a test user.

        Args:
            db: Database session
            username: Username
            email: Email address
            auth_file_path: Path to auth file (optional)
            activation_bytes: Activation bytes (optional)

        Returns:
            Created User ORM object
        """
        user = await user_service.create_user(
            db=db,
            username=username,
            email=email,
            auth_file_path=auth_file_path,
            activation_bytes=activation_bytes,
        )
        await db.flush()
        return user

    @staticmethod
    async def create_with_auth_json(
        db: AsyncSession,
        username: str = "testuser",
        auth_json: Optional[Dict[str, Any]] = None,
        activation_bytes: Optional[str] = None,
    ):
        """Create a test user with Audible authentication.

        Args:
            db: Database session
            username: Username
            auth_json: Audible auth.json data
            activation_bytes: DRM activation bytes

        Returns:
            Created User ORM object
        """
        user = await UserFactory.create(db, username=username)

        if auth_json or activation_bytes:
            await user_service.update_audible_auth_json(
                db=db,
                user_id=str(user.user_id),
                auth_json=auth_json or {},
                activation_bytes=activation_bytes,
            )
            await db.flush()

        return user


class BookFactory:
    """Factory for creating test books."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        asin: str = "B084L6Z6M3",
        title: str = "Test Book",
        author: str = "Test Author",
        narrator: str = "Test Narrator",
        runtime_min: int = 600,
        purchase_date: Optional[str] = None,
        **kwargs,
    ):
        """Create a test book.

        Args:
            db: Database session
            user_id: User UUID
            asin: Amazon Standard Identification Number
            title: Book title
            author: Author name
            narrator: Narrator name
            runtime_min: Runtime in minutes
            purchase_date: Purchase date (YYYY-MM-DD)
            **kwargs: Additional book fields

        Returns:
            Created Book ORM object
        """
        success = await book_service.add_book(
            db=db,
            asin=asin,
            user_id=user_id,
            title=title,
            author=author,
            narrator=narrator,
            runtime_min=runtime_min,
            purchase_date=purchase_date,
            **kwargs,
        )
        if success:
            await db.flush()
            return await book_service.get_book_by_asin(db=db, asin=asin)
        return None

    @staticmethod
    async def create_with_metadata(
        db: AsyncSession,
        user_id: str,
        asin: str = "B084L6Z6M3",
        title: str = "Test Book",
        book_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Create a test book with full metadata.

        Args:
            db: Database session
            user_id: User UUID
            asin: Amazon Standard Identification Number
            title: Book title
            book_data: Full Audible API response
            **kwargs: Additional fields

        Returns:
            Created Book ORM object
        """
        if book_data is None:
            book_data = {
                "authors": [{"name": "Test Author", "type": "author"}],
                "narrators": [{"name": "Test Narrator", "type": "narrator"}],
                "runtime_length_min": 600,
                "media_info": {
                    "codec": "AAC",
                    "bitrate": 128,
                    "duration_ms": 3600000,
                },
            }

        success = await book_service.add_book_with_metadata(
            db=db,
            asin=asin,
            user_id=user_id,
            title=title,
            book_data=book_data,
            **kwargs,
        )
        if success:
            await db.flush()
            return await book_service.get_book_by_asin(db=db, asin=asin)
        return None


class SyncFactory:
    """Factory for creating test sync records."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        sync_type: str = "full",
        notes: Optional[str] = None,
    ):
        """Create a test sync record.

        Args:
            db: Database session
            user_id: User UUID
            sync_type: Type of sync (full, incremental, manual)
            notes: Optional notes

        Returns:
            Created SyncHistory ORM object
        """
        sync_history = await sync_service.create_sync_history(
            db=db,
            user_id=UUID(user_id),
            sync_type=sync_type,
            notes=notes,
        )
        await db.flush()
        return sync_history

    @staticmethod
    async def create_completed(
        db: AsyncSession,
        user_id: str,
        sync_type: str = "full",
        books_found: int = 5,
        books_added: int = 5,
        books_downloaded: int = 3,
        books_decrypted: int = 2,
        errors_count: int = 0,
    ):
        """Create and complete a test sync record.

        Args:
            db: Database session
            user_id: User UUID
            sync_type: Type of sync
            books_found: Number of books found
            books_added: Number of books added
            books_downloaded: Number of books downloaded
            books_decrypted: Number of books decrypted
            errors_count: Number of errors

        Returns:
            Completed SyncHistory ORM object
        """
        sync_history = await SyncFactory.create(
            db=db,
            user_id=user_id,
            sync_type=sync_type,
        )

        if sync_history:
            success = await sync_service.update_sync_status(
                db=db,
                sync_id=sync_history.sync_id,
                status="completed",
                books_found=books_found,
                books_added=books_added,
                books_downloaded=books_downloaded,
                books_decrypted=books_decrypted,
                errors_count=errors_count,
            )
            if success:
                await db.flush()
                return await sync_service.get_sync_by_id(db=db, sync_id=sync_history.sync_id)

        return None


class MetadataFactory:
    """Factory for creating test metadata."""

    @staticmethod
    async def create_contributor(
        db: AsyncSession,
        name: str = "Test Author",
        contributor_type: str = "author",
        audible_asin: Optional[str] = None,
    ):
        """Create a test contributor.

        Args:
            db: Database session
            name: Contributor name
            contributor_type: Type of contributor (author, narrator, etc.)
            audible_asin: Audible ASIN (optional)

        Returns:
            Created Contributor ORM object
        """
        return await metadata_service.get_or_create_contributor(
            db=db,
            name=name,
            contributor_type=contributor_type,
            audible_asin=audible_asin,
        )

    @staticmethod
    async def add_media_info(
        db: AsyncSession,
        asin: str,
        codec: str = "AAC",
        bitrate: int = 128,
        duration_ms: int = 3600000,
    ):
        """Add media info for a book.

        Args:
            db: Database session
            asin: Book ASIN
            codec: Audio codec
            bitrate: Bitrate in kbps
            duration_ms: Duration in milliseconds

        Returns:
            True if successful
        """
        return await metadata_service.upsert_media_info(
            db=db,
            asin=asin,
            codec=codec,
            bitrate=bitrate,
            duration_ms=duration_ms,
        )

    @staticmethod
    async def add_custom_metadata(
        db: AsyncSession,
        asin: str,
        key: str,
        value: Any,
    ):
        """Add custom metadata to a book.

        Args:
            db: Database session
            asin: Book ASIN
            key: Metadata key
            value: Metadata value

        Returns:
            True if successful
        """
        return await metadata_service.add_custom_metadata(
            db=db,
            asin=asin,
            key=key,
            value=value,
        )

    @staticmethod
    async def add_badge(
        db: AsyncSession,
        asin: str,
        badge_name: str,
        badge_info: Optional[Dict[str, Any]] = None,
    ):
        """Add a badge to a book.

        Args:
            db: Database session
            asin: Book ASIN
            badge_name: Badge name
            badge_info: Additional badge info

        Returns:
            True if successful
        """
        return await metadata_service.add_badge(
            db=db,
            asin=asin,
            badge_name=badge_name,
            badge_info=badge_info,
        )


__all__ = [
    "UserFactory",
    "BookFactory",
    "SyncFactory",
    "MetadataFactory",
]
