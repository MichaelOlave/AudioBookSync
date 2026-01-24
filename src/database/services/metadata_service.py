"""Metadata operations consolidated service layer using SQLAlchemy ORM."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.database.models.book_availability import BookAvailability
from src.database.models.book_metadata import BookMetadataJson
from src.database.models.chapter import Chapter
from src.database.models.companion_material import CompanionMaterial
from src.database.models.contributor import BookContributor, Contributor
from src.database.models.media_info import MediaInfo
from src.database.models.reading_progress import ReadingProgress

# ============================================================================
# CONTRIBUTOR OPERATIONS
# ============================================================================


async def create_contributor(
    db: AsyncSession,
    name: str,
    contributor_type: Optional[str] = None,
    audible_asin: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[Contributor]:
    """Create a new contributor."""
    try:
        contributor = Contributor(
            name=name,
            type=contributor_type,
            audible_asin=audible_asin,
            description=description,
            url=url,
        )
        db.add(contributor)
        await db.flush()
        await db.refresh(contributor)
        logger.info(f"Created contributor: {name} (ID: {contributor.contributor_id})")
        return contributor
    except Exception as e:
        logger.error(f"Failed to create contributor: {e}")
        return None


async def get_contributor_by_id(db: AsyncSession, contributor_id: UUID) -> Optional[Contributor]:
    """Get contributor by ID."""
    try:
        result = await db.execute(
            select(Contributor).where(Contributor.contributor_id == contributor_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get contributor: {e}")
        return None


async def get_contributor_by_name(db: AsyncSession, name: str) -> Optional[Contributor]:
    """Get contributor by name."""
    try:
        result = await db.execute(select(Contributor).where(Contributor.name == name))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get contributor by name: {e}")
        return None


async def add_book_contributor(
    db: AsyncSession,
    asin: str,
    contributor_id: UUID,
    role: str,
    sequence_number: Optional[int] = None,
) -> Optional[BookContributor]:
    """Add a contributor to a book."""
    try:
        stmt = insert(BookContributor).values(
            asin=asin,
            contributor_id=contributor_id,
            role=role,
            sequence_number=sequence_number,
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["asin", "contributor_id", "role"],
        )
        result = await db.execute(stmt)
        await db.flush()

        if result.rowcount:
            logger.info(f"Added contributor {contributor_id} to book {asin}")
        else:
            logger.debug(f"Contributor already linked: {contributor_id} -> {asin} ({role})")

        existing = await db.execute(
            select(BookContributor).where(
                and_(
                    BookContributor.asin == asin,
                    BookContributor.contributor_id == contributor_id,
                    BookContributor.role == role,
                )
            )
        )
        return existing.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to add book contributor: {e}")
        return None


async def get_or_create_contributor(
    db: AsyncSession,
    name: str,
    contributor_type: str,
    audible_asin: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
) -> Optional[Contributor]:
    """
    Get existing contributor or create new one.

    Uses name and type as unique identifier to prevent duplicates.
    """
    try:
        if audible_asin:
            result = await db.execute(
                select(Contributor).where(Contributor.audible_asin == audible_asin)
            )
            contributor = result.scalar_one_or_none()
            if contributor:
                if name and contributor.name != name:
                    contributor.name = name
                if contributor_type and not contributor.type:
                    contributor.type = contributor_type
                if description and not contributor.description:
                    contributor.description = description
                if url and not contributor.url:
                    contributor.url = url
                await db.flush()
                logger.debug(f"Found existing contributor by audible_asin: {audible_asin}")
                return contributor

        # Try to find existing contributor
        result = await db.execute(
            select(Contributor).where(
                and_(
                    Contributor.name == name,
                    Contributor.type == contributor_type,
                )
            )
        )
        contributor = result.scalar_one_or_none()

        if contributor:
            logger.debug(f"Found existing contributor: {name} ({contributor_type})")
            if audible_asin and not contributor.audible_asin:
                contributor.audible_asin = audible_asin
                await db.flush()
            return contributor

        # Create new contributor if not found
        logger.debug(f"Creating new contributor: {name} ({contributor_type})")
        return await create_contributor(
            db=db,
            name=name,
            contributor_type=contributor_type,
            audible_asin=audible_asin,
            description=description,
            url=url,
        )
    except Exception as e:
        logger.error(f"Failed to get or create contributor: {e}")
        return None


# ============================================================================
# MEDIA INFO OPERATIONS
# ============================================================================


async def create_media_info(
    db: AsyncSession,
    asin: str,
    codec: Optional[str] = None,
    bitrate: Optional[int] = None,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    format_type: Optional[str] = None,
    duration_ms: Optional[int] = None,
    chapters_count: Optional[int] = None,
    enhanced: bool = False,
) -> Optional[MediaInfo]:
    """Create media info record."""
    try:
        media = MediaInfo(
            asin=asin,
            codec=codec,
            bitrate=bitrate,
            sample_rate=sample_rate,
            channels=channels,
            format_type=format_type,
            duration_ms=duration_ms,
            chapters_count=chapters_count,
            enhanced=enhanced,
        )
        db.add(media)
        await db.flush()
        await db.refresh(media)
        logger.info(f"Created media info for {asin}")
        return media
    except Exception as e:
        logger.error(f"Failed to create media info: {e}")
        return None


async def get_media_info(db: AsyncSession, asin: str) -> Optional[MediaInfo]:
    """Get media info for a book."""
    try:
        result = await db.execute(select(MediaInfo).where(MediaInfo.asin == asin))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get media info: {e}")
        return None


async def upsert_media_info(
    db: AsyncSession,
    asin: str,
    codec: Optional[str] = None,
    bitrate: Optional[int] = None,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None,
    format_type: Optional[str] = None,
    duration_ms: Optional[int] = None,
    chapters_count: Optional[int] = None,
    enhanced: bool = False,
) -> bool:
    """
    Insert or update media info using PostgreSQL upsert.

    If media info exists for the asin, updates the provided fields.
    If not, creates a new record.
    """
    try:
        # Build update dict with non-None values
        update_fields = {
            "codec": codec,
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "channels": channels,
            "format_type": format_type,
            "duration_ms": duration_ms,
            "chapters_count": chapters_count,
            "enhanced": enhanced,
        }
        # Remove None values to avoid overwriting with nulls
        update_fields = {k: v for k, v in update_fields.items() if v is not None}

        # Create insert statement
        stmt = insert(MediaInfo).values(
            asin=asin,
            codec=codec,
            bitrate=bitrate,
            sample_rate=sample_rate,
            channels=channels,
            format_type=format_type,
            duration_ms=duration_ms,
            chapters_count=chapters_count,
            enhanced=enhanced,
        )

        # Add on_conflict_do_update for upsert
        stmt = stmt.on_conflict_do_update(
            index_elements=["asin"],
            set_=update_fields,
        )

        await db.execute(stmt)
        await db.flush()
        logger.info(f"Upserted media info for {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert media info: {e}")
        return False


# ============================================================================
# READING PROGRESS OPERATIONS
# ============================================================================


async def create_reading_progress(
    db: AsyncSession,
    asin: str,
    user_id: UUID,
    percent_complete: int = 0,
    position_ms: int = 0,
    is_finished: Optional[bool] = None,
) -> Optional[ReadingProgress]:
    """Create reading progress record."""
    try:
        progress = ReadingProgress(
            asin=asin,
            user_id=user_id,
            percent_complete=percent_complete,
            position_ms=position_ms,
            is_finished=is_finished if is_finished is not None else False,
        )
        if is_finished:
            progress.date_finished = datetime.now(timezone.utc)
        db.add(progress)
        await db.flush()
        await db.refresh(progress)
        logger.info(f"Created reading progress for {asin} by user {user_id}")
        return progress
    except Exception as e:
        logger.error(f"Failed to create reading progress: {e}")
        return None


async def get_reading_progress(
    db: AsyncSession,
    asin: str,
    user_id: UUID,
) -> Optional[ReadingProgress]:
    """Get reading progress for a user and book."""
    try:
        result = await db.execute(
            select(ReadingProgress).where(
                and_(
                    ReadingProgress.asin == asin,
                    ReadingProgress.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get reading progress: {e}")
        return None


async def update_reading_progress(
    db: AsyncSession,
    asin: str,
    user_id: UUID,
    percent_complete: Optional[int] = None,
    position_ms: Optional[int] = None,
    is_finished: Optional[bool] = None,
) -> bool:
    """Update reading progress."""
    try:
        progress = await get_reading_progress(db, asin, user_id)
        if not progress:
            return False

        if percent_complete is not None:
            progress.percent_complete = percent_complete
        if position_ms is not None:
            progress.position_ms = position_ms
        if is_finished is not None:
            progress.is_finished = is_finished
            if is_finished:
                progress.date_finished = datetime.now(timezone.utc)

        progress.last_position_update = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Updated reading progress for {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to update reading progress: {e}")
        return False


# ============================================================================
# BOOK AVAILABILITY OPERATIONS
# ============================================================================


async def create_book_availability(
    db: AsyncSession,
    asin: str,
    is_playable: bool = True,
    is_returnable: bool = True,
    is_removable: bool = True,
    is_archived: bool = False,
    is_downloadable: bool = True,
    license_status: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> Optional[BookAvailability]:
    """Create book availability record."""
    try:
        availability = BookAvailability(
            asin=asin,
            is_playable=is_playable,
            is_returnable=is_returnable,
            is_removable=is_removable,
            is_archived=is_archived,
            is_downloadable=is_downloadable,
            license_status=license_status,
            expires_at=expires_at,
        )
        db.add(availability)
        await db.flush()
        await db.refresh(availability)
        logger.info(f"Created availability for {asin}")
        return availability
    except Exception as e:
        logger.error(f"Failed to create book availability: {e}")
        return None


async def get_book_availability(db: AsyncSession, asin: str) -> Optional[BookAvailability]:
    """Get book availability."""
    try:
        result = await db.execute(select(BookAvailability).where(BookAvailability.asin == asin))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get book availability: {e}")
        return None


async def upsert_book_availability(
    db: AsyncSession,
    asin: str,
    is_playable: Optional[bool] = None,
    is_returnable: Optional[bool] = None,
    is_removable: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    is_downloadable: Optional[bool] = None,
    license_status: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> bool:
    """Create or update book availability without clobbering missing fields."""
    try:
        availability = await get_book_availability(db, asin)
        if availability:
            if is_playable is not None:
                availability.is_playable = is_playable
            if is_returnable is not None:
                availability.is_returnable = is_returnable
            if is_removable is not None:
                availability.is_removable = is_removable
            if is_archived is not None:
                availability.is_archived = is_archived
            if is_downloadable is not None:
                availability.is_downloadable = is_downloadable
            if license_status is not None:
                availability.license_status = license_status
            if expires_at is not None:
                availability.expires_at = expires_at
            await db.flush()
            logger.info(f"Updated availability for {asin}")
            return True

        created = await create_book_availability(
            db=db,
            asin=asin,
            is_playable=is_playable if is_playable is not None else True,
            is_returnable=is_returnable if is_returnable is not None else True,
            is_removable=is_removable if is_removable is not None else True,
            is_archived=is_archived if is_archived is not None else False,
            is_downloadable=is_downloadable if is_downloadable is not None else True,
            license_status=license_status,
            expires_at=expires_at,
        )
        return created is not None
    except Exception as e:
        logger.error(f"Failed to upsert book availability: {e}")
        return False


# ============================================================================
# COMPANION MATERIAL OPERATIONS
# ============================================================================


async def create_companion_material(
    db: AsyncSession,
    asin: str,
    material_type: str,
    url: str,
    title: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    mime_type: Optional[str] = None,
    sequence_number: Optional[int] = None,
    description: Optional[str] = None,
) -> Optional[CompanionMaterial]:
    """Create companion material record."""
    try:
        stmt = insert(CompanionMaterial).values(
            asin=asin,
            material_type=material_type,
            url=url,
            title=title,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            sequence_number=sequence_number,
            description=description,
        )
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["asin", "url"],
        )
        result = await db.execute(stmt)
        await db.flush()

        if result.rowcount:
            logger.info(f"Created companion material for {asin}: {title}")
        else:
            logger.debug(f"Companion material already exists for {asin}: {url}")

        existing = await db.execute(
            select(CompanionMaterial).where(
                and_(
                    CompanionMaterial.asin == asin,
                    CompanionMaterial.url == url,
                )
            )
        )
        return existing.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to create companion material: {e}")
        return None


async def get_companion_materials(db: AsyncSession, asin: str) -> List[CompanionMaterial]:
    """Get all companion materials for a book."""
    try:
        result = await db.execute(
            select(CompanionMaterial)
            .where(CompanionMaterial.asin == asin)
            .order_by(CompanionMaterial.sequence_number)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get companion materials: {e}")
        return []


# ============================================================================
# CHAPTER OPERATIONS
# ============================================================================


async def get_chapters_by_asin(db: AsyncSession, asin: str) -> List[Chapter]:
    """Get chapters for a book ordered by sequence."""
    try:
        result = await db.execute(
            select(Chapter).where(Chapter.asin == asin).order_by(Chapter.sequence_number)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get chapters for {asin}: {e}")
        return []


async def replace_chapters(
    db: AsyncSession,
    asin: str,
    chapters: List[Dict[str, Any]],
) -> int:
    """Replace all chapters for a book with the provided list."""
    try:
        await db.execute(delete(Chapter).where(Chapter.asin == asin))

        if not chapters:
            logger.info(f"Cleared chapters for {asin}")
            return 0

        deduped: Dict[int, Dict[str, Any]] = {}
        for chapter in chapters:
            seq = chapter.get("sequence_number")
            if seq is None:
                continue
            payload = dict(chapter)
            payload["asin"] = asin
            deduped[seq] = payload

        payload = list(deduped.values())
        if not payload:
            logger.info(f"No valid chapter sequence numbers for {asin}")
            return 0

        stmt = insert(Chapter).values(payload)
        await db.execute(stmt)
        await db.flush()
        logger.info(f"Replaced chapters for {asin} ({len(payload)} rows)")
        return len(payload)
    except Exception as e:
        logger.error(f"Failed to replace chapters for {asin}: {e}")
        return 0


# ============================================================================
# BOOK METADATA JSON OPERATIONS
# ============================================================================


async def create_book_metadata(
    db: AsyncSession,
    asin: str,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    language: Optional[str] = None,
    publisher_name: Optional[str] = None,
    format_type: Optional[str] = None,
    content_type: Optional[str] = None,
    content_delivery_type: Optional[str] = None,
    status: Optional[str] = None,
    publication_datetime: Optional[datetime] = None,
    release_date: Optional[datetime] = None,
    issue_date: Optional[datetime] = None,
    purchase_date: Optional[datetime] = None,
    runtime_length_min: Optional[int] = None,
    is_listenable: Optional[bool] = None,
    is_purchasability_suppressed: Optional[bool] = None,
    is_adult_product: Optional[bool] = None,
    has_children: Optional[bool] = None,
    origin_asin: Optional[str] = None,
    brand: Optional[str] = None,
    periodical_info: Optional[dict] = None,
    relationships: Optional[dict] = None,
    badges: Optional[dict] = None,
    claim_code_url: Optional[str] = None,
    parent_asin: Optional[str] = None,
    sku: Optional[str] = None,
    isbn: Optional[str] = None,
    rating_distribution: Optional[dict] = None,
    custom_metadata: Optional[dict] = None,
    authors: Optional[list] = None,
    narrators: Optional[list] = None,
    rating: Optional[dict] = None,
    product_images: Optional[dict] = None,
    social_media_images: Optional[dict] = None,
    available_codecs: Optional[list] = None,
    library_status: Optional[dict] = None,
    thesaurus_subject_keywords: Optional[list] = None,
) -> Optional[BookMetadataJson]:
    """Create book metadata JSON record."""
    try:
        metadata = BookMetadataJson(
            asin=asin,
            title=title,
            subtitle=subtitle,
            language=language,
            publisher_name=publisher_name,
            format_type=format_type,
            content_type=content_type,
            content_delivery_type=content_delivery_type,
            status=status,
            publication_datetime=publication_datetime,
            release_date=release_date,
            issue_date=issue_date,
            purchase_date=purchase_date,
            runtime_length_min=runtime_length_min,
            is_listenable=is_listenable,
            is_purchasability_suppressed=is_purchasability_suppressed,
            is_adult_product=is_adult_product,
            has_children=has_children,
            origin_asin=origin_asin,
            brand=brand,
            periodical_info=periodical_info,
            relationships=relationships,
            badges=badges,
            claim_code_url=claim_code_url,
            parent_asin=parent_asin,
            sku=sku,
            isbn=isbn,
            rating_distribution=rating_distribution,
            custom_metadata=custom_metadata,
            authors=authors,
            narrators=narrators,
            rating=rating,
            product_images=product_images,
            social_media_images=social_media_images,
            available_codecs=available_codecs,
            library_status=library_status,
            thesaurus_subject_keywords=thesaurus_subject_keywords,
        )
        db.add(metadata)
        await db.flush()
        await db.refresh(metadata)
        logger.info(f"Created metadata for {asin}")
        return metadata
    except Exception as e:
        logger.error(f"Failed to create book metadata: {e}")
        return None


async def get_book_metadata(db: AsyncSession, asin: str) -> Optional[BookMetadataJson]:
    """Get book metadata."""
    try:
        result = await db.execute(select(BookMetadataJson).where(BookMetadataJson.asin == asin))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get book metadata: {e}")
        return None


async def update_book_metadata(
    db: AsyncSession,
    asin: str,
    custom_metadata: Optional[dict] = None,
    relationships: Optional[dict] = None,
    **kwargs,
) -> bool:
    """Update book metadata."""
    try:
        metadata = await get_book_metadata(db, asin)
        if not metadata:
            return False

        if custom_metadata is not None:
            metadata.custom_metadata = custom_metadata
        if relationships is not None:
            metadata.relationships = relationships

        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)

        await db.flush()
        logger.info(f"Updated metadata for {asin}")
        return True
    except Exception as e:
        logger.error(f"Failed to update book metadata: {e}")
        return False


async def add_custom_metadata(
    db: AsyncSession,
    asin: str,
    key: str,
    value: Any,
) -> bool:
    """
    Add or update custom metadata field using JSON operations.

    Creates or updates a specific key in the custom_metadata JSON object.
    """
    try:
        metadata = await get_book_metadata(db, asin)

        if not metadata:
            # Create new metadata record with initial custom_metadata
            metadata = BookMetadataJson(
                asin=asin,
                custom_metadata={key: value},
            )
            db.add(metadata)
            logger.info(f"Created metadata with custom field for {asin}")
        else:
            # Update existing - initialize dict if None
            if metadata.custom_metadata is None:
                metadata.custom_metadata = {}
            metadata.custom_metadata[key] = value
            # CRITICAL: Mark as modified for JSON tracking
            flag_modified(metadata, "custom_metadata")
            logger.info(f"Added custom metadata field '{key}' to {asin}")

        await db.flush()
        return True
    except Exception as e:
        logger.error(f"Failed to add custom metadata: {e}")
        return False


async def add_badge(
    db: AsyncSession,
    asin: str,
    badge_name: str,
    badge_info: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Append badge to JSON array.

    Adds a new badge object to the badges array in book metadata.
    """
    try:
        metadata = await get_book_metadata(db, asin)
        badge_obj = {"name": badge_name, **(badge_info or {})}

        if not metadata:
            # Create new metadata with initial badges array
            metadata = BookMetadataJson(asin=asin, badges=[badge_obj])
            db.add(metadata)
            logger.info(f"Created metadata with badge for {asin}")
        else:
            # Update existing - initialize array if None
            if metadata.badges is None:
                metadata.badges = []
            metadata.badges.append(badge_obj)
            # CRITICAL: Mark as modified for JSON tracking
            flag_modified(metadata, "badges")
            logger.info(f"Added badge '{badge_name}' to {asin}")

        await db.flush()
        return True
    except Exception as e:
        logger.error(f"Failed to add badge: {e}")
        return False
