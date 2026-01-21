"""Book database service layer using SQLAlchemy ORM."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.book import Book
from src.database.services import metadata_service


async def add_book(
    db: AsyncSession,
    asin: str,
    user_id: str,
    title: str,
    purchase_date: Optional[str] = None,
    runtime_min: Optional[int] = None,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    series_name: Optional[str] = None,
    description: Optional[str] = None,
    rating: Optional[Decimal] = None,
    subtitle: Optional[str] = None,
    publisher: Optional[str] = None,
    publication_date: Optional[str] = None,
    language: Optional[str] = None,
    review_count: Optional[int] = None,
    cover_art_url: Optional[str] = None,
    **kwargs,
) -> bool:
    """
    Add or update a book in the library.

    Args:
        db: Database session
        asin: Amazon Standard Identification Number
        user_id: User UUID
        title: Book title
        purchase_date: Purchase date (YYYY-MM-DD format string)
        runtime_min: Runtime in minutes
        author: Author name
        narrator: Narrator name
        series_name: Series name
        description: Book description
        rating: Rating (0-5)
        subtitle: Book subtitle
        publisher: Publisher name
        publication_date: Publication date (YYYY-MM-DD format string)
        language: Language code
        review_count: Number of reviews
        cover_art_url: URL to cover art

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if book already exists
        existing_book = await get_book_by_asin(db, asin)

        # Convert string dates to date objects if provided
        purchase_date_obj = None
        if purchase_date:
            try:
                purchase_date_obj = date.fromisoformat(purchase_date)
            except (ValueError, TypeError):
                pass

        publication_date_obj = None
        if publication_date:
            try:
                publication_date_obj = date.fromisoformat(publication_date)
            except (ValueError, TypeError):
                pass

        if existing_book:
            # Update existing book
            existing_book.title = title
            existing_book.user_id = user_id
            if author:
                existing_book.author = author
            if narrator:
                existing_book.narrator = narrator
            if runtime_min:
                existing_book.runtime_min = runtime_min
            if purchase_date_obj:
                existing_book.purchase_date = purchase_date_obj
            if subtitle:
                existing_book.subtitle = subtitle
            if description:
                existing_book.description = description
            if rating:
                existing_book.rating = rating
            if publisher:
                existing_book.publisher = publisher
            if publication_date_obj:
                existing_book.publication_date = publication_date_obj
            if language:
                existing_book.language = language
            if series_name:
                existing_book.series_name = series_name
            if review_count is not None:
                existing_book.review_count = review_count
            if cover_art_url:
                existing_book.cover_art_url = cover_art_url

            await db.flush()
            logger.info(f"Updated book: {title} (ASIN: {asin})")
        else:
            # Create new book
            book = Book(
                asin=asin,
                user_id=user_id,
                title=title,
                author=author,
                narrator=narrator,
                runtime_min=runtime_min,
                purchase_date=purchase_date_obj,
                subtitle=subtitle,
                description=description,
                rating=rating,
                publisher=publisher,
                publication_date=publication_date_obj,
                language=language or "en-US",
                series_name=series_name,
                review_count=review_count,
                cover_art_url=cover_art_url,
            )
            db.add(book)
            await db.flush()
            logger.info(f"Added book: {title} (ASIN: {asin})")

        return True
    except Exception as e:
        logger.error(f"Failed to add/update book: {e}")
        return False


async def get_book_by_asin(db: AsyncSession, asin: str) -> Optional[Book]:
    """
    Get book by ASIN.

    Args:
        db: Database session
        asin: Amazon Standard Identification Number

    Returns:
        Book object if found, None otherwise
    """
    try:
        result = await db.execute(select(Book).where(Book.asin == asin))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get book by ASIN: {e}")
        return None


async def get_books_by_user(db: AsyncSession, user_id: str) -> List[Book]:
    """
    Get all books for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of Book objects
    """
    try:
        result = await db.execute(select(Book).where(Book.user_id == user_id).order_by(Book.title))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get books for user: {e}")
        return []


async def get_downloaded_books(db: AsyncSession, user_id: str) -> List[Book]:
    """
    Get all downloaded books for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of downloaded Book objects
    """
    try:
        result = await db.execute(
            select(Book)
            .where(
                and_(
                    Book.user_id == user_id,
                    Book.is_downloaded,
                )
            )
            .order_by(Book.title)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get downloaded books: {e}")
        return []


async def get_decrypted_books(db: AsyncSession, user_id: str) -> List[Book]:
    """
    Get all decrypted books for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of decrypted Book objects
    """
    try:
        result = await db.execute(
            select(Book)
            .where(
                and_(
                    Book.user_id == user_id,
                    Book.is_decrypted,
                )
            )
            .order_by(Book.title)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get decrypted books: {e}")
        return []


async def update_book_download_status(
    db: AsyncSession,
    asin: str,
    is_downloaded: bool,
    download_path: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
) -> bool:
    """
    Update book's download status.

    Args:
        db: Database session
        asin: Amazon Standard Identification Number
        is_downloaded: Download status
        download_path: Path to downloaded file
        file_size_bytes: Size of downloaded file in bytes

    Returns:
        True if successful, False otherwise
    """
    try:
        book = await get_book_by_asin(db, asin)
        if not book:
            return False

        book.is_downloaded = is_downloaded
        if download_path:
            book.download_path = download_path
        if file_size_bytes:
            book.file_size_bytes = file_size_bytes

        await db.flush()
        logger.info(f"Updated download status for book: {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to update book download status: {e}")
        return False


async def update_book_decryption_status(
    db: AsyncSession,
    asin: str,
    is_decrypted: bool,
    decrypted_path: Optional[str] = None,
) -> bool:
    """
    Update book's decryption status.

    Args:
        db: Database session
        asin: Amazon Standard Identification Number
        is_decrypted: Decryption status
        decrypted_path: Path to decrypted file

    Returns:
        True if successful, False otherwise
    """
    try:
        book = await get_book_by_asin(db, asin)
        if not book:
            return False

        book.is_decrypted = is_decrypted
        if decrypted_path:
            book.decrypted_path = decrypted_path

        await db.flush()
        logger.info(f"Updated decryption status for book: {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to update book decryption status: {e}")
        return False


async def delete_book(db: AsyncSession, asin: str) -> bool:
    """
    Delete a book (cascades to download and decryption records).

    Args:
        db: Database session
        asin: Amazon Standard Identification Number

    Returns:
        True if successful, False otherwise
    """
    try:
        book = await get_book_by_asin(db, asin)
        if not book:
            return False

        await db.delete(book)
        await db.flush()
        logger.info(f"Deleted book: {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete book: {e}")
        return False


async def search_books(
    db: AsyncSession,
    user_id: str,
    query: str,
) -> List[Book]:
    """
    Search books by title, author, or narrator.

    Args:
        db: Database session
        user_id: User UUID
        query: Search query string

    Returns:
        List of matching Book objects
    """
    try:
        query_lower = f"%{query.lower()}%"
        result = await db.execute(
            select(Book)
            .where(
                and_(
                    Book.user_id == user_id,
                    (
                        Book.title.ilike(query_lower)
                        | Book.author.ilike(query_lower)
                        | Book.narrator.ilike(query_lower)
                    ),
                )
            )
            .order_by(Book.title)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to search books: {e}")
        return []


async def get_books_by_series(
    db: AsyncSession,
    user_id: str,
    series_name: str,
) -> List[Book]:
    """
    Get all books in a series for a user.

    Args:
        db: Database session
        user_id: User UUID
        series_name: Series name

    Returns:
        List of Book objects in the series
    """
    try:
        result = await db.execute(
            select(Book)
            .where(
                and_(
                    Book.user_id == user_id,
                    Book.series_name == series_name,
                )
            )
            .order_by(Book.series_sequence)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get books by series: {e}")
        return []


async def add_book_with_metadata(
    db: AsyncSession,
    asin: str,
    user_id: str,
    title: str,
    book_data: Dict[str, Any],
    purchase_date: Optional[str] = None,
) -> bool:
    """
    Orchestrate adding book with full metadata across 7 tables.

    This coordinates:
    1. Basic book record
    2. Contributors (authors, narrators) with get-or-create
    3. Book-contributor relationships
    4. Media info (codec, bitrate, duration)
    5. Reading progress initialization
    6. Companion materials (PDFs, transcripts)
    7. Flexible metadata (JSON)

    Args:
        db: Database session
        asin: Amazon Standard Identification Number
        user_id: User UUID
        title: Book title
        book_data: Dictionary containing full book metadata
        purchase_date: Purchase date (YYYY-MM-DD format string)

    Returns:
        True if successful, False otherwise
    """
    try:
        # 1. Add basic book
        book_added = await add_book(
            db,
            asin=asin,
            user_id=user_id,
            title=title,
            purchase_date=purchase_date,
            runtime_min=_extract_runtime(book_data),
            author=_extract_authors_string(book_data),
            narrator=_extract_narrators_string(book_data),
            series_name=book_data.get("series_name"),
            description=book_data.get("description"),
            rating=book_data.get("rating"),
            subtitle=book_data.get("subtitle"),
            publisher=book_data.get("publisher"),
            publication_date=book_data.get("publication_date"),
            language=book_data.get("language", "en-US"),
            review_count=book_data.get("review_count"),
            cover_art_url=book_data.get("cover_art_url"),
        )

        if not book_added:
            logger.error(f"Failed to add basic book record: {asin}")
            return False

        # 2. Add contributors (authors, narrators)
        contributors_data = book_data.get("authors", []) + book_data.get("narrators", [])
        for idx, contrib_data in enumerate(contributors_data):
            try:
                contributor = await metadata_service.get_or_create_contributor(
                    db,
                    name=contrib_data.get("name"),
                    contributor_type=contrib_data.get("type", "author"),
                    audible_asin=contrib_data.get("asin"),
                    description=contrib_data.get("description"),
                    url=contrib_data.get("url"),
                )
                if contributor:
                    await metadata_service.add_book_contributor(
                        db,
                        asin=asin,
                        contributor_id=contributor.contributor_id,
                        role=contrib_data.get("type", "author"),
                        sequence_number=idx,
                    )
            except Exception as e:
                logger.warning(f"Failed to add contributor to book: {e}")
                # Continue with other contributors

        # 3. Add media info
        media_data = book_data.get("media_info", {})
        if media_data:
            await metadata_service.upsert_media_info(
                db,
                asin=asin,
                codec=media_data.get("codec"),
                bitrate=media_data.get("bitrate"),
                sample_rate=media_data.get("sample_rate"),
                channels=media_data.get("channels"),
                format_type=media_data.get("format_type"),
                duration_ms=media_data.get("duration_ms"),
                chapters_count=media_data.get("chapters_count"),
                enhanced=media_data.get("enhanced", False),
            )

        # 4. Create reading progress
        await metadata_service.create_reading_progress(
            db,
            asin=asin,
            user_id=user_id,
            percent_complete=book_data.get("percent_complete", 0),
            position_ms=book_data.get("last_position_heard", 0),
        )

        # 5. Add companion materials
        for material in book_data.get("companion_materials", []):
            try:
                await metadata_service.create_companion_material(
                    db,
                    asin=asin,
                    material_type=material.get("material_type", "document"),
                    url=material.get("url"),
                    title=material.get("title"),
                    file_size_bytes=material.get("file_size_bytes"),
                    mime_type=material.get("mime_type"),
                    sequence_number=material.get("sequence_number"),
                    description=material.get("description"),
                )
            except Exception as e:
                logger.warning(f"Failed to add companion material: {e}")
                # Continue with other materials

        # 6. Store flexible metadata
        await metadata_service.create_book_metadata(
            db,
            asin=asin,
            origin_asin=book_data.get("origin_asin"),
            brand=book_data.get("brand_name"),
            periodical_info=book_data.get("periodical_info"),
            relationships=book_data.get("relationships"),
            badges=book_data.get("badges"),
            claim_code_url=book_data.get("claim_code_url"),
            parent_asin=book_data.get("parent_asin"),
            sku=book_data.get("sku"),
            rating_distribution=book_data.get("rating_distribution"),
            custom_metadata=book_data.get("custom_metadata"),
        )

        logger.info(f"Added book with complete metadata: {title} ({asin})")
        return True

    except Exception as e:
        logger.error(f"Failed to add book with metadata: {e}")
        return False


def _extract_runtime(book_data: Dict[str, Any]) -> Optional[int]:
    """Extract runtime in minutes from book data."""
    runtime_ms = book_data.get("runtime_length_min")
    return int(runtime_ms) if runtime_ms else None


def _extract_authors_string(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract comma-separated authors string."""
    authors = book_data.get("authors", [])
    if not authors:
        return None
    return ", ".join([a.get("name", "") for a in authors if a.get("name")])


def _extract_narrators_string(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract comma-separated narrators string."""
    narrators = book_data.get("narrators", [])
    if not narrators:
        return None
    return ", ".join([n.get("name", "") for n in narrators if n.get("name")])
