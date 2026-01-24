"""Service for fetching Audible library data and saving to the database."""

import json
from typing import Any, Dict, Tuple

import audible
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import Config
from ...database.services import book_service, user_service
from ..middleware.error_handler import AuthorizationError


def _build_response_groups(raw_groups: str) -> Tuple[str, list[str]]:
    """Build a sanitized response groups string for Audible."""
    groups = [group.strip() for group in raw_groups.split(",") if group.strip()]
    invalid = {
        "cover_art_url",
        "last_position_heard",
        "publisher",
        "publication_date",
        "product_images",
    }
    cleaned: list[str] = []
    removed: list[str] = []
    seen = set()

    for group in groups:
        if group in invalid:
            removed.append(group)
            continue
        if group and group not in seen:
            cleaned.append(group)
            seen.add(group)

    if not cleaned:
        cleaned = ["product_desc", "product_attrs"]

    return ",".join(cleaned), removed


async def fetch_audible_library_to_db(
    db: AsyncSession,
    user_id: str,
    num_results: int = 1000,
    page: int = 1,
) -> Dict[str, Any]:
    """Fetch user's Audible library and save metadata to the database."""
    logger.info(f"Fetching Audible library for user: {user_id}")

    user = await user_service.get_user_by_id(db, user_id)
    if not user or user.audible_auth_json is None:
        logger.error(f"No Audible credentials found for user {user_id}")
        raise AuthorizationError(
            "Audible credentials not configured. Please authenticate with Audible first."
        )

    auth_data = json.loads(str(user.audible_auth_json))
    auth = audible.Authenticator.from_dict(auth_data)

    response_groups_param, removed_groups = _build_response_groups(
        Config.AUDIBLE_RESPONSE_GROUPS
    )
    if removed_groups:
        logger.warning(
            f"Skipping unsupported Audible response groups: {', '.join(removed_groups)}"
        )

    logger.info(
        f"Fetching library from Audible (num_results={num_results}, page={page}, "
        f"response_groups={len(response_groups_param.split(','))})"
    )
    async with audible.AsyncClient(auth=auth) as client:
        library_response = await client.get(
            "library",
            num_results=num_results,
            page=page,
            response_groups=response_groups_param,
            sort_by=Config.AUDIBLE_SORT_BY,
        )

    items = library_response.get("items", [])
    logger.info(f"Successfully fetched {len(items)} books from Audible for user {user_id}")

    books_saved = 0
    books_failed = 0

    for item in items:
        try:
            asin = item.get("asin")
            if not asin:
                logger.warning("Item missing ASIN, skipping")
                books_failed += 1
                continue

            title = item.get("title") or "Unknown Title"
            success = await book_service.add_book_with_metadata(
                db=db,
                asin=asin,
                user_id=user_id,
                title=title,
                book_data=item,
            )

            if success:
                books_saved += 1
                logger.info(f"Saved book metadata: {title} (ASIN: {asin})")
            else:
                books_failed += 1
                logger.warning(f"Failed to save book metadata: {title} (ASIN: {asin})")
        except Exception as e:
            books_failed += 1
            logger.error(f"Error processing book item: {e}")

    await db.commit()

    logger.info(
        f"Audible library fetch complete for user {user_id}: "
        f"{books_saved} saved, {books_failed} failed"
    )

    return {
        "books_saved": books_saved,
        "books_failed": books_failed,
        "total_fetched": len(items),
        "user_id": user_id,
    }
