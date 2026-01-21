"""Helper functions for common CRUD operations with SQLAlchemy ORM."""

from typing import Optional, Type, TypeVar, Callable, Any, Dict
from loguru import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def get_by_id(
    db: AsyncSession,
    model: Type[T],
    entity_id: Any,
    id_column: str = "id",
) -> Optional[T]:
    """
    Get an entity by its primary ID.

    Args:
        db: Database session
        model: SQLAlchemy model class
        entity_id: The ID value to search for
        id_column: Name of the ID column (default: 'id')

    Returns:
        Entity object if found, None otherwise
    """
    try:
        id_attr = getattr(model, id_column)
        result = await db.execute(
            select(model).where(id_attr == entity_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get {model.__name__} by {id_column}: {e}")
        return None


async def update_entity(
    db: AsyncSession,
    entity: T,
    updates: Dict[str, Any],
    entity_name: Optional[str] = None,
    entity_id: Optional[Any] = None,
) -> bool:
    """
    Update an entity's fields and commit changes.

    Args:
        db: Database session
        entity: SQLAlchemy entity to update
        updates: Dictionary of field names to new values
        entity_name: Name for logging (defaults to model class name)
        entity_id: ID for logging (auto-detected if not provided)

    Returns:
        True if successful, False otherwise
    """
    try:
        if not entity:
            return False

        entity_name = entity_name or entity.__class__.__name__

        # Apply updates to entity
        for field, value in updates.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
            else:
                logger.warning(
                    f"Field '{field}' does not exist on {entity_name}"
                )

        await db.flush()

        # Extract ID for logging if not provided
        if entity_id is None:
            entity_id = getattr(entity, "id", None) or getattr(
                entity, f"{entity_name.lower()}_id", "unknown"
            )

        logger.info(f"Updated {entity_name}: {entity_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update {entity_name}: {e}")
        return False


async def delete_entity(
    db: AsyncSession,
    entity: T,
    entity_name: Optional[str] = None,
    entity_id: Optional[Any] = None,
) -> bool:
    """
    Delete an entity from the database.

    Args:
        db: Database session
        entity: SQLAlchemy entity to delete
        entity_name: Name for logging (defaults to model class name)
        entity_id: ID for logging (auto-detected if not provided)

    Returns:
        True if successful, False otherwise
    """
    try:
        if not entity:
            return False

        entity_name = entity_name or entity.__class__.__name__

        # Extract ID for logging if not provided
        if entity_id is None:
            entity_id = getattr(entity, "id", None) or getattr(
                entity, f"{entity_name.lower()}_id", "unknown"
            )

        await db.delete(entity)
        await db.flush()

        logger.info(f"Deleted {entity_name}: {entity_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete {entity_name}: {e}")
        return False


async def conditional_update(
    db: AsyncSession,
    entity: T,
    updates: Dict[str, Any],
    condition_check: Callable[[T], bool],
    entity_name: Optional[str] = None,
    entity_id: Optional[Any] = None,
) -> bool:
    """
    Update an entity only if a condition is met.

    Args:
        db: Database session
        entity: SQLAlchemy entity to update
        updates: Dictionary of field names to new values
        condition_check: Callable that returns True if update should proceed
        entity_name: Name for logging
        entity_id: ID for logging

    Returns:
        True if successful, False otherwise
    """
    if not entity or not condition_check(entity):
        return False

    return await update_entity(db, entity, updates, entity_name, entity_id)
