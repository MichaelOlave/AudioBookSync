"""Book database service layer using SQLAlchemy ORM."""

from typing import Optional, List
from datetime import date
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models.book import Book
from src.database.models.download import DownloadStatus
from src.database.models.decryption import DecryptionStatus


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
        result = await db.execute(
            select(Book).where(Book.asin == asin)
        )
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
        result = await db.execute(
            select(Book).where(Book.user_id == user_id).order_by(Book.title)
        )
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
            select(Book).where(
                and_(
                    Book.user_id == user_id,
                    Book.is_downloaded == True,
                )
            ).order_by(Book.title)
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
            select(Book).where(
                and_(
                    Book.user_id == user_id,
                    Book.is_decrypted == True,
                )
            ).order_by(Book.title)
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
            select(Book).where(
                and_(
                    Book.user_id == user_id,
                    (
                        Book.title.ilike(query_lower)
                        | Book.author.ilike(query_lower)
                        | Book.narrator.ilike(query_lower)
                    ),
                )
            ).order_by(Book.title)
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
            select(Book).where(
                and_(
                    Book.user_id == user_id,
                    Book.series_name == series_name,
                )
            ).order_by(Book.series_sequence)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get books by series: {e}")
        return []
