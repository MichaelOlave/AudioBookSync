"""Factory for generating generic status service functions for any status model."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.book import Book
from src.database.services.base_service import get_by_id, update_entity


@dataclass
class StatusServiceConfig:
    """Configuration for a status service model."""

    model_class: Type[Any]  # SQLAlchemy model class
    model_name: str  # "download", "decryption"
    id_column: str  # "download_id", "decryption_id"
    started_at_column: str  # "download_started_at", "decryption_started_at"
    completed_at_column: str  # "download_completed_at", "decryption_completed_at"
    pending_status: str = "pending"
    active_status: str = "processing"  # "downloading", "decrypting"
    completed_status: str = "completed"
    failed_status: str = "failed"
    related_key_column: str = "asin"


class StatusServiceFactory:
    """Factory for generating status service functions."""

    def __init__(self, config: StatusServiceConfig):
        """Initialize factory with configuration.

        Args:
            config: StatusServiceConfig describing the model
        """
        self.config = config
        self.model = config.model_class
        self.model_name = config.model_name
        self.id_column = config.id_column
        self.started_at_column = config.started_at_column
        self.completed_at_column = config.completed_at_column

    def generate_service_functions(self) -> Dict[str, Callable]:
        """Generate all service functions for the configured model.

        Returns:
            Dictionary mapping function names to async callables
        """
        return {
            f"create_{self.model_name}_status": self._create_create_function(),
            f"get_{self.model_name}_by_id": self._create_get_by_id_function(),
            f"get_{self.model_name}s_by_asin": self._create_get_by_asin_function(),
            f"get_latest_{self.model_name}": self._create_get_latest_function(),
            f"update_{self.model_name}_status": self._create_update_status_function(),
            f"start_{self.model_name}": self._create_start_function(),
            f"complete_{self.model_name}": self._create_complete_function(),
            f"fail_{self.model_name}": self._create_fail_function(),
            f"get_pending_{self.model_name}s": self._create_get_pending_function(),
            f"get_failed_{self.model_name}s": self._create_get_failed_function(),
            f"delete_{self.model_name}": self._create_delete_function(),
            f"get_{self.model_name}s_by_user": self._create_get_by_user_function(),
            f"count_{self.model_name}s_by_user": self._create_count_by_user_function(),
            f"get_{self.model_name}_by_id_for_user": self._create_get_by_id_for_user_function(),
        }

    def _create_get_by_id_function(self) -> Callable:
        """Create a function to get entity by ID."""

        async def get_by_id_func(db: AsyncSession, entity_id: UUID) -> Optional[Any]:
            return await get_by_id(db, self.model, entity_id, id_column=self.id_column)

        return get_by_id_func

    def _create_get_by_asin_function(self) -> Callable:
        """Create a function to get all entities for a given ASIN."""

        async def get_by_asin_func(db: AsyncSession, asin: str) -> List[Any]:
            try:
                result = await db.execute(
                    select(self.model)
                    .where(self.model.asin == asin)
                    .order_by(self.model.created_at.desc())
                )
                return result.scalars().all()  # type: ignore
            except Exception as e:
                logger.error(f"Failed to get {self.model_name}s for ASIN: {e}")
                return []

        return get_by_asin_func

    def _create_get_latest_function(self) -> Callable:
        """Create a function to get the latest entity for a given ASIN."""

        async def get_latest_func(db: AsyncSession, asin: str) -> Optional[Any]:
            try:
                result = await db.execute(
                    select(self.model)
                    .where(self.model.asin == asin)
                    .order_by(self.model.created_at.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to get latest {self.model_name}: {e}")
                return None

        return get_latest_func

    def _create_get_pending_function(self) -> Callable:
        """Create a function to get all pending entities."""

        async def get_pending_func(db: AsyncSession) -> List[Any]:
            try:
                result = await db.execute(
                    select(self.model)
                    .where(self.model.status == self.config.pending_status)
                    .order_by(self.model.created_at)
                )
                return result.scalars().all()  # type: ignore
            except Exception as e:
                logger.error(f"Failed to get pending {self.model_name}s: {e}")
                return []

        return get_pending_func

    def _create_get_failed_function(self) -> Callable:
        """Create a function to get all failed entities."""

        async def get_failed_func(db: AsyncSession, limit: int = 100) -> List[Any]:
            try:
                result = await db.execute(
                    select(self.model)
                    .where(self.model.status == self.config.failed_status)
                    .order_by(self.model.created_at.desc())
                    .limit(limit)
                )
                return result.scalars().all()  # type: ignore
            except Exception as e:
                logger.error(f"Failed to get failed {self.model_name}s: {e}")
                return []

        return get_failed_func

    def _create_create_function(self) -> Callable:
        """Create a function to create a new entity."""

        async def create_func(
            db: AsyncSession, asin: str, status: Optional[str] = None, **kwargs: Any
        ) -> Optional[Any]:
            try:
                if status is None:
                    status = self.config.pending_status

                entity = self.model(asin=asin, status=status, **kwargs)
                db.add(entity)
                await db.flush()
                await db.refresh(entity)
                entity_id = getattr(entity, self.id_column)
                logger.info(f"Created {self.model_name} status: {asin} (ID: {entity_id})")
                return entity
            except Exception as e:
                logger.error(f"Failed to create {self.model_name} status: {e}")
                return None

        return create_func

    def _create_update_status_function(self) -> Callable:
        """Create a function to update entity status with timestamp management."""

        async def update_status_func(
            db: AsyncSession, entity_id: UUID, status: str, **kwargs: Any
        ) -> bool:
            try:
                entity = await get_by_id(db, self.model, entity_id, id_column=self.id_column)
                if not entity:
                    return False

                # Set status
                entity.status = status  # type: ignore

                # Apply other updates
                for field, value in kwargs.items():
                    if value is not None and hasattr(entity, field):
                        setattr(entity, field, value)

                # Set timestamps based on status
                now = datetime.now(timezone.utc)
                if status == self.config.active_status:
                    setattr(entity, self.started_at_column, now)
                elif status in [self.config.completed_status, self.config.failed_status]:
                    setattr(entity, self.completed_at_column, now)

                await db.flush()
                logger.info(f"Updated {self.model_name} status: {entity_id} -> {status}")
                return True
            except Exception as e:
                logger.error(f"Failed to update {self.model_name} status: {e}")
                return False

        return update_status_func

    def _create_start_function(self) -> Callable:
        """Create a function to mark entity as started."""

        async def start_func(db: AsyncSession, entity_id: UUID, **kwargs: Any) -> bool:
            entity = await get_by_id(db, self.model, entity_id, id_column=self.id_column)
            updates: Dict[str, Any] = {
                "status": self.config.active_status,
                self.started_at_column: datetime.now(timezone.utc),
            }
            updates.update(kwargs)
            return await update_entity(db, entity, updates, entity_id=entity_id)

        return start_func

    def _create_complete_function(self) -> Callable:
        """Create a function to mark entity as completed."""

        async def complete_func(db: AsyncSession, entity_id: UUID, **kwargs: Any) -> bool:
            entity = await get_by_id(db, self.model, entity_id, id_column=self.id_column)
            updates: Dict[str, Any] = {
                "status": self.config.completed_status,
                self.completed_at_column: datetime.now(timezone.utc),
            }
            updates.update(kwargs)
            return await update_entity(db, entity, updates, entity_id=entity_id)

        return complete_func

    def _create_fail_function(self) -> Callable:
        """Create a function to mark entity as failed."""

        async def fail_func(
            db: AsyncSession,
            entity_id: UUID,
            error_message: str,
            error_details: Optional[Dict[str, Any]] = None,
            **kwargs: Any,
        ) -> bool:
            entity = await get_by_id(db, self.model, entity_id, id_column=self.id_column)
            updates: Dict[str, Any] = {
                "status": self.config.failed_status,
                "error_message": error_message,
                self.completed_at_column: datetime.now(timezone.utc),
            }
            if error_details:
                updates["error_details"] = error_details
            updates.update(kwargs)
            return await update_entity(db, entity, updates, entity_id=entity_id)

        return fail_func

    def _create_delete_function(self) -> Callable:
        """Create a function to delete an entity."""

        async def delete_func(db: AsyncSession, entity_id: UUID) -> bool:
            try:
                entity = await get_by_id(db, self.model, entity_id, id_column=self.id_column)
                if not entity:
                    return False

                await db.delete(entity)
                await db.flush()
                logger.info(f"Deleted {self.model_name}: {entity_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete {self.model_name}: {e}")
                return False

        return delete_func

    def _create_get_by_user_function(self) -> Callable:
        """Create a function to get entities for a specific user."""

        async def get_by_user_func(
            db: AsyncSession,
            user_id: str,
            status: Optional[str] = None,
            limit: int = 50,
            offset: int = 0,
        ) -> List[Any]:
            try:
                query = (
                    select(self.model)
                    .join(Book, self.model.asin == Book.asin)
                    .where(Book.user_id == user_id)
                )

                if status:
                    query = query.where(self.model.status == status)  # type: ignore

                query = query.order_by(self.model.created_at.desc()).limit(limit).offset(offset)

                result = await db.execute(query)
                entities = result.scalars().all()
                logger.info(f"Retrieved {len(entities)} {self.model_name}s for user {user_id}")
                return entities  # type: ignore
            except Exception as e:
                logger.error(f"Failed to get {self.model_name}s for user {user_id}: {e}")
                return []

        return get_by_user_func

    def _create_count_by_user_function(self) -> Callable:
        """Create a function to count entities for a specific user."""

        async def count_by_user_func(
            db: AsyncSession,
            user_id: str,
            status: Optional[str] = None,
        ) -> int:
            try:
                id_attr = getattr(self.model, self.id_column)
                query = (
                    select(func.count(id_attr))
                    .join(Book, self.model.asin == Book.asin)
                    .where(Book.user_id == user_id)
                )

                if status:
                    query = query.where(self.model.status == status)  # type: ignore

                result = await db.execute(query)
                count = result.scalar_one_or_none() or 0
                logger.info(f"Counted {count} {self.model_name}s for user {user_id}")
                return int(count)
            except Exception as e:
                logger.error(f"Failed to count {self.model_name}s for user {user_id}: {e}")
                return 0

        return count_by_user_func

    def _create_get_by_id_for_user_function(self) -> Callable:
        """Create a function to get entity by ID and verify user ownership."""

        async def get_by_id_for_user_func(
            db: AsyncSession,
            entity_id: UUID,
            user_id: str,
        ) -> Optional[Any]:
            try:
                result = await db.execute(
                    select(self.model)
                    .join(Book, self.model.asin == Book.asin)
                    .where(
                        and_(
                            getattr(self.model, self.id_column) == entity_id,
                            Book.user_id == user_id,
                        )
                    )
                )
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Failed to get {self.model_name} by ID for user {user_id}: {e}")
                return None

        return get_by_id_for_user_func
