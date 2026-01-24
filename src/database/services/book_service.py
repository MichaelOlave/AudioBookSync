"""Book database service layer using SQLAlchemy ORM."""

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.book import Book
from src.database.models.book_metadata import BookMetadataJson
from src.database.models.user_book import UserBook
from src.database.services import metadata_service


async def add_book(
    db: AsyncSession,
    asin: str,
    user_id: str,
    title: str,
    purchase_date: Optional[Union[str, date, datetime]] = None,
    runtime_min: Optional[int] = None,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    series_name: Optional[str] = None,
    series_sequence: Optional[str] = None,
    description: Optional[str] = None,
    rating: Optional[Decimal] = None,
    subtitle: Optional[str] = None,
    publisher: Optional[str] = None,
    publication_date: Optional[Union[str, date, datetime]] = None,
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
        purchase_date: Purchase date (YYYY-MM-DD or ISO datetime string)
        runtime_min: Runtime in minutes
        author: Author name
        narrator: Narrator name
        series_name: Series name
        series_sequence: Series sequence identifier
        description: Book description
        rating: Rating (0-5)
        subtitle: Book subtitle
        publisher: Publisher name
        publication_date: Publication date (YYYY-MM-DD or ISO datetime string)
        language: Language code
        review_count: Number of reviews
        cover_art_url: URL to cover art

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if book already exists
        existing_book = await get_book_by_asin(db, asin)

        # Convert date strings/datetimes to date objects if provided
        purchase_date_obj = _parse_date_value(purchase_date)
        publication_date_obj = _parse_date_value(publication_date)

        if existing_book:
            # Update existing book metadata (do not overwrite ownership)
            existing_book.title = title
            if author:
                existing_book.author = author
            if narrator:
                existing_book.narrator = narrator
            if runtime_min is not None:
                existing_book.runtime_min = runtime_min
            if subtitle:
                existing_book.subtitle = subtitle
            if description:
                existing_book.description = description
            if rating is not None:
                existing_book.rating = rating
            if publisher:
                existing_book.publisher = publisher
            if publication_date_obj:
                existing_book.publication_date = publication_date_obj
            if language:
                existing_book.language = language
            if series_name:
                existing_book.series_name = series_name
            if series_sequence:
                existing_book.series_sequence = series_sequence
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
                subtitle=subtitle,
                description=description,
                rating=rating,
                publisher=publisher,
                publication_date=publication_date_obj,
                language=language or "en-US",
                series_name=series_name,
                series_sequence=series_sequence,
                review_count=review_count,
                cover_art_url=cover_art_url,
            )
            db.add(book)
            await db.flush()
            logger.info(f"Added book: {title} (ASIN: {asin})")

        user_book = await get_user_book(db, user_id, asin)
        if user_book:
            if purchase_date_obj:
                user_book.purchase_date = purchase_date_obj
        else:
            user_book = UserBook(
                user_id=user_id,
                asin=asin,
                purchase_date=purchase_date_obj,
            )
            db.add(user_book)
            await db.flush()

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


async def get_user_book(db: AsyncSession, user_id: str, asin: str) -> Optional[UserBook]:
    """
    Get a user book entry by user and ASIN.

    Args:
        db: Database session
        user_id: User UUID
        asin: Amazon Standard Identification Number

    Returns:
        UserBook object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(UserBook).where(and_(UserBook.user_id == user_id, UserBook.asin == asin))
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user book: {e}")
        return None


async def get_user_book_with_book(
    db: AsyncSession, user_id: str, asin: str
) -> Optional[Tuple[UserBook, Book]]:
    """
    Get a user book entry and its book metadata.
    """
    try:
        result = await db.execute(
            select(UserBook, Book)
            .join(Book, UserBook.asin == Book.asin)
            .where(and_(UserBook.user_id == user_id, UserBook.asin == asin))
        )
        row = result.first()
        if not row:
            return None
        return row[0], row[1]
    except Exception as e:
        logger.error(f"Failed to get user book with book: {e}")
        return None


async def get_user_book_for_user_ids(
    db: AsyncSession, user_ids: List[str], asin: str
) -> Optional[Tuple[UserBook, Book]]:
    """
    Get a user book entry for any user in a set of user IDs.
    """
    if not user_ids:
        return None

    try:
        result = await db.execute(
            select(UserBook, Book)
            .join(Book, UserBook.asin == Book.asin)
            .where(and_(UserBook.user_id.in_(user_ids), UserBook.asin == asin))
        )
        row = result.first()
        if not row:
            return None
        return row[0], row[1]
    except Exception as e:
        logger.error(f"Failed to get user book for user list: {e}")
        return None


async def get_books_by_user(db: AsyncSession, user_id: str) -> List[dict]:
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
            select(Book, UserBook)
            .join(UserBook, UserBook.asin == Book.asin)
            .where(UserBook.user_id == user_id)
            .order_by(Book.title)
        )
        return [build_book_response_data(book, user_book) for book, user_book in result.all()]
    except Exception as e:
        logger.error(f"Failed to get books for user: {e}")
        return []


async def get_books_by_user_ids(db: AsyncSession, user_ids: List[str]) -> List[dict]:
    """
    Get all books for a list of users.

    Args:
        db: Database session
        user_ids: List of user UUIDs

    Returns:
        List of Book objects
    """
    if not user_ids:
        return []

    try:
        result = await db.execute(
            select(Book, UserBook)
            .join(UserBook, UserBook.asin == Book.asin)
            .where(UserBook.user_id.in_(user_ids))
            .order_by(Book.title)
        )
        return [build_book_response_data(book, user_book) for book, user_book in result.all()]
    except Exception as e:
        logger.error(f"Failed to get books for user list: {e}")
        return []


async def get_books_with_metadata_by_user(
    db: AsyncSession,
    user_id: str,
    downloaded_only: bool = False,
) -> List[Tuple[UserBook, Book, Optional[BookMetadataJson]]]:
    """
    Get all books for a user with optional metadata.

    Args:
        db: Database session
        user_id: User UUID
        downloaded_only: If True, only return downloaded books

    Returns:
        List of (UserBook, Book, BookMetadataJson|None) tuples
    """
    try:
        stmt = (
            select(UserBook, Book, BookMetadataJson)
            .join(Book, UserBook.asin == Book.asin)
            .outerjoin(BookMetadataJson, BookMetadataJson.asin == Book.asin)
            .where(UserBook.user_id == user_id)
            .order_by(Book.title)
        )
        if downloaded_only:
            stmt = stmt.where(UserBook.is_downloaded)

        result = await db.execute(stmt)
        return result.all()
    except Exception as e:
        logger.error(f"Failed to get books with metadata for user: {e}")
        return []


async def get_books_with_metadata_by_user_ids(
    db: AsyncSession,
    user_ids: List[str],
    downloaded_only: bool = False,
) -> List[Tuple[UserBook, Book, Optional[BookMetadataJson]]]:
    """
    Get all books for a list of users with optional metadata.

    Args:
        db: Database session
        user_ids: List of user UUIDs
        downloaded_only: If True, only return downloaded books

    Returns:
        List of (UserBook, Book, BookMetadataJson|None) tuples
    """
    if not user_ids:
        return []

    try:
        stmt = (
            select(UserBook, Book, BookMetadataJson)
            .join(Book, UserBook.asin == Book.asin)
            .outerjoin(BookMetadataJson, BookMetadataJson.asin == Book.asin)
            .where(UserBook.user_id.in_(user_ids))
            .order_by(Book.title)
        )
        if downloaded_only:
            stmt = stmt.where(UserBook.is_downloaded)

        result = await db.execute(stmt)
        return result.all()
    except Exception as e:
        logger.error(f"Failed to get books with metadata for user list: {e}")
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
            .join(UserBook, UserBook.asin == Book.asin)
            .where(
                and_(
                    UserBook.user_id == user_id,
                    UserBook.is_downloaded,
                )
            )
            .order_by(Book.title)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get downloaded books: {e}")
        return []


async def get_not_downloaded_books(db: AsyncSession, user_id: str) -> List[Book]:
    """
    Get all books that have not been downloaded for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        List of Book objects not marked as downloaded
    """
    try:
        result = await db.execute(
            select(Book)
            .join(UserBook, UserBook.asin == Book.asin)
            .where(
                and_(
                    UserBook.user_id == user_id,
                    UserBook.is_downloaded.is_(False),
                )
            )
            .order_by(Book.title)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get not downloaded books: {e}")
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
            .join(UserBook, UserBook.asin == Book.asin)
            .where(
                and_(
                    UserBook.user_id == user_id,
                    UserBook.is_decrypted,
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
    user_id: Optional[str] = None,
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
        if user_id:
            user_book = await get_user_book(db, user_id, asin)
            if not user_book:
                return False

            user_book.is_downloaded = is_downloaded
            if download_path:
                user_book.download_path = download_path
            if file_size_bytes is not None:
                user_book.file_size_bytes = file_size_bytes
        else:
            book = await get_book_by_asin(db, asin)
            if not book:
                return False

            book.is_downloaded = is_downloaded
            if download_path:
                book.download_path = download_path
            if file_size_bytes is not None:
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
    user_id: Optional[str] = None,
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
        if user_id:
            user_book = await get_user_book(db, user_id, asin)
            if not user_book:
                return False

            user_book.is_decrypted = is_decrypted
            if decrypted_path:
                user_book.decrypted_path = decrypted_path
        else:
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


async def delete_book(db: AsyncSession, asin: str, user_id: str) -> bool:
    """
    Delete a book (cascades to download and decryption records).

    Args:
        db: Database session
        asin: Amazon Standard Identification Number

    Returns:
        True if successful, False otherwise
    """
    try:
        user_book = await get_user_book(db, user_id, asin)
        if not user_book:
            return False

        await db.delete(user_book)
        await db.flush()
        remaining = await db.execute(
            select(UserBook.user_book_id).where(UserBook.asin == asin).limit(1)
        )
        if remaining.scalar_one_or_none() is None:
            book = await get_book_by_asin(db, asin)
            if book:
                await db.delete(book)
                await db.flush()

        logger.info(f"Deleted book for user: {asin}")
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
            .join(UserBook, UserBook.asin == Book.asin)
            .where(
                and_(
                    UserBook.user_id == user_id,
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
            .join(UserBook, UserBook.asin == Book.asin)
            .where(
                and_(
                    UserBook.user_id == user_id,
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
    purchase_date: Optional[Union[str, date, datetime]] = None,
) -> bool:
    """
    Orchestrate adding book with full metadata across all metadata tables.

    This coordinates:
    1. Basic book record
    2. Contributors (authors, narrators) with get-or-create
    3. Book-contributor relationships
    4. Media info (codec, bitrate, duration)
    5. Reading progress initialization
    6. Availability flags
    7. Companion materials (PDFs, transcripts)
    8. Flexible metadata (JSON)

    Args:
        db: Database session
        asin: Amazon Standard Identification Number
        user_id: User UUID
        title: Book title
        book_data: Dictionary containing full book metadata
        purchase_date: Purchase date (YYYY-MM-DD or ISO datetime string)

    Returns:
        True if successful, False otherwise
    """
    try:
        book_data = book_data or {}
        normalized_title = title or book_data.get("title") or "Unknown Title"
        rating_obj = _extract_rating_object(book_data)
        rating_value = _extract_rating_value(rating_obj)
        rating = Decimal(str(rating_value)) if rating_value is not None else None
        review_count = _extract_review_count(rating_obj)
        rating_payload = rating_obj if rating_obj else None
        series_name, series_sequence = _extract_series_info(book_data)
        description = _extract_description(book_data)
        subtitle = book_data.get("subtitle")
        publisher = _first_value(book_data.get("publisher_name"), book_data.get("publisher"))
        language = _first_value(book_data.get("language"), book_data.get("language_name"), "en-US")
        cover_art_url = _extract_cover_art_url(book_data)
        runtime_min = _extract_runtime(book_data)
        purchase_date_value = purchase_date or _extract_purchase_date(book_data)
        publication_date_value = _extract_publication_date(book_data)

        # 1. Add basic book
        book_added = await add_book(
            db,
            asin=asin,
            user_id=user_id,
            title=normalized_title,
            purchase_date=purchase_date_value,
            runtime_min=runtime_min,
            author=_extract_authors_string(book_data),
            narrator=_extract_narrators_string(book_data),
            series_name=series_name,
            series_sequence=series_sequence,
            description=description,
            rating=rating,
            subtitle=subtitle,
            publisher=publisher,
            publication_date=publication_date_value,
            language=language,
            review_count=review_count,
            cover_art_url=cover_art_url,
        )

        if not book_added:
            logger.error(f"Failed to add basic book record: {asin}")
            return False

        # 2. Add contributors (authors, narrators, and other roles)
        contributors_data = _normalize_contributors(book_data)
        for idx, contrib_data in enumerate(contributors_data):
            try:
                contributor_name = _first_value(
                    contrib_data.get("name"),
                    contrib_data.get("display_name"),
                    _combine_name(contrib_data),
                )
                if not contributor_name:
                    continue
                contributor = await metadata_service.get_or_create_contributor(
                    db,
                    name=contributor_name,
                    contributor_type=contrib_data.get("type", "author"),
                    audible_asin=_first_value(
                        contrib_data.get("asin"),
                        contrib_data.get("contributor_asin"),
                    ),
                    description=contrib_data.get("description"),
                    url=contrib_data.get("url") or contrib_data.get("web_url"),
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
        media_data = _extract_media_info(book_data)
        chapters_payload = _extract_chapters(book_data)
        chapters_count = media_data.get("chapters_count") if media_data else None
        if chapters_count is None and chapters_payload is not None:
            chapters_count = len(chapters_payload)
        if media_data or chapters_count is not None:
            await metadata_service.upsert_media_info(
                db,
                asin=asin,
                codec=media_data.get("codec") if media_data else None,
                bitrate=media_data.get("bitrate") if media_data else None,
                sample_rate=media_data.get("sample_rate") if media_data else None,
                channels=media_data.get("channels") if media_data else None,
                format_type=_first_value(
                    media_data.get("format_type") if media_data else None,
                    book_data.get("content_type"),
                ),
                duration_ms=_first_value(
                    media_data.get("duration_ms") if media_data else None,
                    book_data.get("runtime_length_ms"),
                ),
                chapters_count=chapters_count,
                enhanced=_coerce_bool(
                    _first_value(
                        media_data.get("enhanced") if media_data else None,
                        book_data.get("is_audible_enhanced"),
                    )
                )
                or False,
            )

        if chapters_payload is not None:
            await metadata_service.replace_chapters(
                db,
                asin=asin,
                chapters=chapters_payload,
            )

        # 4. Create or update reading progress
        percent_complete = _coerce_int(book_data.get("percent_complete"))
        position_ms = _coerce_int(book_data.get("last_position_heard"))
        is_finished = _coerce_bool(book_data.get("is_finished"))
        existing_progress = await metadata_service.get_reading_progress(db, asin, user_id)
        if existing_progress:
            await metadata_service.update_reading_progress(
                db,
                asin=asin,
                user_id=user_id,
                percent_complete=percent_complete,
                position_ms=position_ms,
                is_finished=is_finished,
            )
        else:
            await metadata_service.create_reading_progress(
                db,
                asin=asin,
                user_id=user_id,
                percent_complete=percent_complete or 0,
                position_ms=position_ms or 0,
                is_finished=is_finished,
            )

        # 5. Add availability flags
        await metadata_service.upsert_book_availability(
            db,
            asin=asin,
            is_playable=_coerce_bool(
                _first_value(book_data.get("is_playable"), book_data.get("is_listenable"))
            ),
            is_returnable=_coerce_bool(book_data.get("is_returnable")),
            is_removable=_coerce_bool(book_data.get("is_removable")),
            is_archived=_coerce_bool(book_data.get("is_archived")),
            is_downloadable=_coerce_bool(book_data.get("is_downloadable")),
            license_status=_first_value(
                book_data.get("license_status"),
                book_data.get("license_status_code"),
            ),
            expires_at=_parse_datetime_value(
                _first_value(
                    book_data.get("expires_at"),
                    book_data.get("license_expiry_date"),
                    book_data.get("license_expiration_date"),
                )
            ),
        )

        # 6. Add companion materials
        for material in _extract_companion_materials(book_data):
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

        # 7. Store flexible metadata
        metadata_payload = _drop_none(
            {
                "title": normalized_title,
                "subtitle": subtitle,
                "language": language,
                "publisher_name": publisher,
                "format_type": book_data.get("format_type"),
                "content_type": book_data.get("content_type"),
                "content_delivery_type": book_data.get("content_delivery_type"),
                "status": _first_value(book_data.get("status"), book_data.get("product_state")),
                "publication_datetime": _parse_datetime_value(
                    _first_value(
                        book_data.get("publication_datetime"),
                        book_data.get("publication_date"),
                        book_data.get("publication_date_string"),
                    )
                ),
                "release_date": _parse_datetime_value(
                    _first_value(book_data.get("release_date"), book_data.get("publication_date"))
                ),
                "issue_date": _parse_datetime_value(book_data.get("issue_date")),
                "purchase_date": _parse_datetime_value(purchase_date_value),
                "runtime_length_min": runtime_min,
                "is_listenable": _coerce_bool(
                    _first_value(book_data.get("is_listenable"), book_data.get("is_playable"))
                ),
                "is_purchasability_suppressed": _coerce_bool(
                    book_data.get("is_purchasability_suppressed")
                ),
                "is_adult_product": _coerce_bool(book_data.get("is_adult_product")),
                "has_children": _coerce_bool(book_data.get("has_children")),
                "origin_asin": book_data.get("origin_asin"),
                "brand": _first_value(book_data.get("brand_name"), book_data.get("brand")),
                "periodical_info": book_data.get("periodical_info"),
                "relationships": book_data.get("relationships"),
                "badges": _first_value(
                    book_data.get("content_badges"),
                    book_data.get("badge_types"),
                    book_data.get("badges"),
                ),
                "claim_code_url": book_data.get("claim_code_url"),
                "parent_asin": book_data.get("parent_asin"),
                "sku": book_data.get("sku"),
                "isbn": book_data.get("isbn"),
                "rating_distribution": _extract_rating_distribution(rating_obj),
                "custom_metadata": _safe_custom_metadata(book_data),
                "authors": book_data.get("authors"),
                "narrators": book_data.get("narrators"),
                "rating": rating_payload,
                "product_images": book_data.get("product_images"),
                "social_media_images": book_data.get("social_media_images"),
                "available_codecs": _first_value(
                    book_data.get("available_codecs"),
                    book_data.get("availability_codecs"),
                ),
                "library_status": _first_value(
                    book_data.get("library_status"),
                    book_data.get("library_status_badges"),
                ),
                "thesaurus_subject_keywords": _first_value(
                    book_data.get("thesaurus_subject_keywords"),
                    book_data.get("subject_keywords"),
                ),
            }
        )
        existing_metadata = await metadata_service.get_book_metadata(db, asin)
        if existing_metadata:
            await metadata_service.update_book_metadata(db, asin=asin, **metadata_payload)
        else:
            await metadata_service.create_book_metadata(db, asin=asin, **metadata_payload)

        logger.info(f"Added book with complete metadata: {normalized_title} ({asin})")
        return True

    except Exception as e:
        logger.error(f"Failed to add book with metadata: {e}")
        return False


def _extract_runtime(book_data: Dict[str, Any]) -> Optional[int]:
    """Extract runtime in minutes from book data."""
    runtime_ms = book_data.get("runtime_length_ms")
    if runtime_ms is not None:
        try:
            return int(int(runtime_ms) / 60000)
        except (ValueError, TypeError):
            return None
    runtime_min = book_data.get("runtime_length_min")
    if runtime_min is None:
        return None
    try:
        return int(runtime_min)
    except (ValueError, TypeError):
        return None


def _extract_authors_string(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract comma-separated authors string."""
    authors = _ensure_list(book_data.get("authors"))
    names = [a.get("name") or a.get("display_name") for a in authors if a]
    names = [name for name in names if name]
    if not names:
        names = _extract_contributors_by_role(book_data, "author")
    return ", ".join(names) if names else None


def _extract_narrators_string(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract comma-separated narrators string."""
    narrators = _ensure_list(book_data.get("narrators"))
    names = [n.get("name") or n.get("display_name") for n in narrators if n]
    names = [name for name in names if name]
    if not names:
        names = _extract_contributors_by_role(book_data, "narrator")
    return ", ".join(names) if names else None


def _extract_rating_object(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract rating object from book data."""
    rating = book_data.get("rating")
    return rating if isinstance(rating, dict) else {}


def _extract_rating_value(rating_obj: Dict[str, Any]) -> Optional[float]:
    """Extract average rating from rating object."""
    if not rating_obj:
        return None
    overall = rating_obj.get("overall_distribution") or {}
    return _first_value(overall.get("average_rating"), rating_obj.get("average_rating"))


def _extract_rating_distribution(rating_obj: Dict[str, Any]) -> Optional[dict]:
    """Extract rating distribution from rating object."""
    if not rating_obj:
        return None
    overall = rating_obj.get("overall_distribution")
    return overall if isinstance(overall, dict) else None


def _extract_review_count(rating_obj: Dict[str, Any]) -> Optional[int]:
    """Extract review count from rating object."""
    if not rating_obj:
        return None
    count = _first_value(rating_obj.get("num_reviews"), rating_obj.get("num_ratings"))
    return _coerce_int(count)


def _extract_series_info(book_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Extract series name and sequence if present."""
    series_data = book_data.get("series")
    series_obj: Dict[str, Any] = {}
    if isinstance(series_data, list):
        series_obj = series_data[0] if series_data else {}
    elif isinstance(series_data, dict):
        series_obj = series_data
    series_name = _first_value(
        book_data.get("series_name"),
        book_data.get("series_title"),
        series_obj.get("title"),
    )
    sequence_value = _first_value(
        book_data.get("series_sequence"),
        book_data.get("series_position"),
        series_obj.get("sequence"),
        series_obj.get("sequence_number"),
        series_obj.get("position"),
    )
    series_sequence = str(sequence_value) if sequence_value is not None else None
    return series_name, series_sequence


def _extract_description(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract best-effort description."""
    return _first_value(
        book_data.get("product_description"),
        book_data.get("description"),
        book_data.get("product_desc"),
        book_data.get("short_description"),
        book_data.get("merchandising_summary"),
        book_data.get("story_summary"),
    )


def _extract_purchase_date(book_data: Dict[str, Any]) -> Optional[Union[str, date, datetime]]:
    """Extract purchase date from possible fields."""
    library_status = book_data.get("library_status") or {}
    if isinstance(library_status, dict):
        library_date = library_status.get("date_added")
    else:
        library_date = None
    return _first_value(book_data.get("purchase_date"), library_date, book_data.get("date_added"))


def _extract_publication_date(book_data: Dict[str, Any]) -> Optional[Union[str, date, datetime]]:
    """Extract publication date from possible fields."""
    return _first_value(
        book_data.get("publication_date_string"),
        book_data.get("publication_date"),
        book_data.get("release_date"),
        book_data.get("publication_datetime"),
    )


def _extract_cover_art_url(book_data: Dict[str, Any]) -> Optional[str]:
    """Extract cover art URL from possible fields."""
    product_images = book_data.get("product_images") or {}
    if isinstance(product_images, dict):
        cover_url = product_images.get("500") or product_images.get("600")
    else:
        cover_url = None
    return _first_value(cover_url, book_data.get("cover_art_url"), book_data.get("image_url"))


def _extract_media_info(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract media info payload."""
    media_data = book_data.get("media_info")
    if isinstance(media_data, dict):
        return media_data
    media_list = book_data.get("media")
    if isinstance(media_list, list) and media_list:
        return media_list[0] if isinstance(media_list[0], dict) else {}
    return {}


def _extract_chapters(book_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract normalized chapter metadata payloads."""
    raw_chapters = _first_value(
        book_data.get("chapters"),
        book_data.get("chapter_info"),
        book_data.get("chapter_list"),
    )
    if raw_chapters is None:
        return None

    if isinstance(raw_chapters, dict):
        raw_chapters = _first_value(
            raw_chapters.get("items"),
            raw_chapters.get("chapters"),
            raw_chapters.get("chapter_list"),
            raw_chapters.get("list"),
        )

    if not isinstance(raw_chapters, list):
        return []

    chapters: List[Dict[str, Any]] = []
    for idx, chapter in enumerate(raw_chapters):
        if not isinstance(chapter, dict):
            continue
        sequence_number = _coerce_int(
            _first_value(
                chapter.get("sequence_number"),
                chapter.get("sequence"),
                chapter.get("index"),
                chapter.get("chapter_index"),
                chapter.get("position"),
            )
        )
        if sequence_number is None:
            sequence_number = idx + 1

        start_offset_ms = _coerce_int(
            _first_value(
                chapter.get("start_offset_ms"),
                chapter.get("start_ms"),
                chapter.get("start_time_ms"),
                chapter.get("start_position_ms"),
            )
        )
        end_offset_ms = _coerce_int(
            _first_value(
                chapter.get("end_offset_ms"),
                chapter.get("end_ms"),
                chapter.get("end_time_ms"),
                chapter.get("end_position_ms"),
            )
        )
        length_ms = _coerce_int(_first_value(chapter.get("length_ms"), chapter.get("duration_ms")))
        if length_ms is None:
            length_seconds = _coerce_int(
                _first_value(chapter.get("length_seconds"), chapter.get("duration_seconds"))
            )
            if length_seconds is not None:
                length_ms = length_seconds * 1000
        if end_offset_ms is None and start_offset_ms is not None and length_ms is not None:
            end_offset_ms = start_offset_ms + length_ms

        chapters.append(
            {
                "sequence_number": sequence_number,
                "title": _first_value(
                    chapter.get("title"),
                    chapter.get("name"),
                    chapter.get("chapter_title"),
                ),
                "start_offset_ms": start_offset_ms,
                "end_offset_ms": end_offset_ms,
                "length_ms": length_ms,
                "raw_metadata": chapter,
            }
        )

    return chapters


def _extract_companion_materials(book_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize companion materials, including pdf_url fallback."""
    materials: List[Dict[str, Any]] = []
    raw_materials = _ensure_list(book_data.get("companion_materials"))
    for material in raw_materials:
        if not isinstance(material, dict):
            continue
        url = material.get("url") or material.get("href")
        if not url:
            continue
        materials.append(
            {
                "material_type": _first_value(
                    material.get("material_type"),
                    material.get("type"),
                    material.get("format"),
                    "document",
                ),
                "url": url,
                "title": _first_value(material.get("title"), material.get("name")),
                "file_size_bytes": _coerce_int(
                    _first_value(material.get("file_size_bytes"), material.get("size"))
                ),
                "mime_type": _first_value(material.get("mime_type"), material.get("mime")),
                "sequence_number": _coerce_int(
                    _first_value(material.get("sequence_number"), material.get("sequence"))
                ),
                "description": material.get("description"),
            }
        )

    pdf_url = book_data.get("pdf_url")
    if pdf_url:
        materials.append(
            {
                "material_type": "pdf",
                "url": pdf_url,
                "title": book_data.get("title"),
                "mime_type": "application/pdf",
            }
        )

    return materials


def _normalize_contributors(book_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize contributor lists with role defaults."""
    normalized: List[Dict[str, Any]] = []
    for author in _ensure_list(book_data.get("authors")):
        if isinstance(author, dict):
            entry = dict(author)
            entry.setdefault("type", "author")
            normalized.append(entry)
    for narrator in _ensure_list(book_data.get("narrators")):
        if isinstance(narrator, dict):
            entry = dict(narrator)
            entry.setdefault("type", "narrator")
            normalized.append(entry)
    for contributor in _ensure_list(book_data.get("contributors")):
        if isinstance(contributor, dict):
            entry = dict(contributor)
            entry.setdefault(
                "type",
                _first_value(
                    contributor.get("type"),
                    contributor.get("role"),
                    contributor.get("contributor_type"),
                    "contributor",
                ),
            )
            normalized.append(entry)
    return normalized


def _extract_contributors_by_role(book_data: Dict[str, Any], role: str) -> List[str]:
    """Extract contributor names by role from contributors list."""
    role_lower = role.lower()
    names: List[str] = []
    for contributor in _ensure_list(book_data.get("contributors")):
        if not isinstance(contributor, dict):
            continue
        contributor_role = _first_value(
            contributor.get("type"),
            contributor.get("role"),
            contributor.get("contributor_type"),
        )
        if contributor_role and contributor_role.lower() != role_lower:
            continue
        contributor_name = _first_value(
            contributor.get("name"),
            contributor.get("display_name"),
            _combine_name(contributor),
        )
        if contributor_name:
            names.append(contributor_name)
    return names


def _combine_name(contributor: Dict[str, Any]) -> Optional[str]:
    """Combine first/last name fields when present."""
    first = contributor.get("first_name")
    last = contributor.get("last_name")
    if first and last:
        return f"{first} {last}"
    return first or last


def _safe_custom_metadata(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure custom metadata is JSON-serializable."""
    try:
        return json.loads(json.dumps(book_data, default=str))
    except (TypeError, ValueError):
        return {}


def _drop_none(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Drop None values while preserving falsy values like 0 or False."""
    return {key: value for key, value in payload.items() if value is not None}


def _first_value(*values: Any) -> Any:
    """Return the first non-empty value."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        return value
    return None


def _ensure_list(value: Any) -> List[Any]:
    """Normalize value to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_int(value: Any) -> Optional[int]:
    """Coerce value to int if possible."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> Optional[bool]:
    """Coerce common truthy/falsey values into bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return bool(value)


def build_book_response_data(book: Book, user_book: UserBook) -> Dict[str, Any]:
    """Build a BookResponse payload from book metadata and user ownership."""
    return {
        "asin": book.asin,
        "title": book.title,
        "author": book.author,
        "narrator": book.narrator,
        "series_name": book.series_name,
        "description": book.description,
        "rating": float(book.rating) if book.rating is not None else None,
        "runtime_min": book.runtime_min,
        "user_id": user_book.user_id,
        "purchase_date": user_book.purchase_date,
        "is_downloaded": user_book.is_downloaded,
        "is_decrypted": user_book.is_decrypted,
        "download_path": user_book.download_path,
        "decrypted_path": user_book.decrypted_path,
        "created_at": user_book.created_at,
        "updated_at": user_book.updated_at,
    }


def build_dashboard_book_data(book: Book, user_book: UserBook) -> Dict[str, Any]:
    """Build a BookDashboardBook payload from book metadata and user ownership."""
    return {
        "asin": book.asin,
        "user_id": user_book.user_id,
        "title": book.title,
        "subtitle": book.subtitle,
        "author": book.author,
        "narrator": book.narrator,
        "series_name": book.series_name,
        "series_sequence": book.series_sequence,
        "publisher": book.publisher,
        "publication_date": book.publication_date,
        "purchase_date": user_book.purchase_date,
        "description": book.description,
        "language": book.language,
        "runtime_min": book.runtime_min,
        "rating": float(book.rating) if book.rating is not None else None,
        "review_count": book.review_count,
        "cover_art_url": book.cover_art_url,
        "file_size_bytes": user_book.file_size_bytes,
        "checksum": user_book.checksum,
        "is_downloaded": user_book.is_downloaded,
        "is_decrypted": user_book.is_decrypted,
        "download_path": user_book.download_path,
        "decrypted_path": user_book.decrypted_path,
        "created_at": user_book.created_at,
        "updated_at": user_book.updated_at,
    }


def _parse_date_value(value: Optional[Union[str, date, datetime]]) -> Optional[date]:
    """Parse a date from ISO strings or datetime values."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
    return None


def _parse_datetime_value(
    value: Optional[Union[str, date, datetime]],
) -> Optional[datetime]:
    """Parse an aware datetime from ISO strings or date values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None
