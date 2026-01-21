"""Metadata operations consolidated service layer using SQLAlchemy ORM."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models.contributor import Contributor, BookContributor
from src.database.models.media_info import MediaInfo
from src.database.models.reading_progress import ReadingProgress
from src.database.models.book_availability import BookAvailability
from src.database.models.companion_material import CompanionMaterial
from src.database.models.book_metadata import BookMetadataJson


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
        result = await db.execute(
            select(Contributor).where(Contributor.name == name)
        )
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
        book_contrib = BookContributor(
            asin=asin,
            contributor_id=contributor_id,
            role=role,
            sequence_number=sequence_number,
        )
        db.add(book_contrib)
        await db.flush()
        await db.refresh(book_contrib)
        logger.info(f"Added contributor {contributor_id} to book {asin}")
        return book_contrib
    except Exception as e:
        logger.error(f"Failed to add book contributor: {e}")
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
        result = await db.execute(
            select(MediaInfo).where(MediaInfo.asin == asin)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get media info: {e}")
        return None


# ============================================================================
# READING PROGRESS OPERATIONS
# ============================================================================


async def create_reading_progress(
    db: AsyncSession,
    asin: str,
    user_id: UUID,
    percent_complete: int = 0,
    position_ms: int = 0,
) -> Optional[ReadingProgress]:
    """Create reading progress record."""
    try:
        progress = ReadingProgress(
            asin=asin,
            user_id=user_id,
            percent_complete=percent_complete,
            position_ms=position_ms,
        )
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
    is_downloadable: bool = True,
    license_status: Optional[str] = None,
) -> Optional[BookAvailability]:
    """Create book availability record."""
    try:
        availability = BookAvailability(
            asin=asin,
            is_playable=is_playable,
            is_returnable=is_returnable,
            is_removable=is_removable,
            is_downloadable=is_downloadable,
            license_status=license_status,
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
        result = await db.execute(
            select(BookAvailability).where(BookAvailability.asin == asin)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get book availability: {e}")
        return None


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
        material = CompanionMaterial(
            asin=asin,
            material_type=material_type,
            url=url,
            title=title,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            sequence_number=sequence_number,
            description=description,
        )
        db.add(material)
        await db.flush()
        await db.refresh(material)
        logger.info(f"Created companion material for {asin}: {title}")
        return material
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
# BOOK METADATA JSON OPERATIONS
# ============================================================================


async def create_book_metadata(
    db: AsyncSession,
    asin: str,
    origin_asin: Optional[str] = None,
    brand: Optional[str] = None,
    periodical_info: Optional[dict] = None,
    relationships: Optional[dict] = None,
    badges: Optional[dict] = None,
    claim_code_url: Optional[str] = None,
    parent_asin: Optional[str] = None,
    sku: Optional[str] = None,
    rating_distribution: Optional[dict] = None,
    custom_metadata: Optional[dict] = None,
) -> Optional[BookMetadataJson]:
    """Create book metadata JSON record."""
    try:
        metadata = BookMetadataJson(
            asin=asin,
            origin_asin=origin_asin,
            brand=brand,
            periodical_info=periodical_info,
            relationships=relationships,
            badges=badges,
            claim_code_url=claim_code_url,
            parent_asin=parent_asin,
            sku=sku,
            rating_distribution=rating_distribution,
            custom_metadata=custom_metadata,
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
        result = await db.execute(
            select(BookMetadataJson).where(BookMetadataJson.asin == asin)
        )
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
