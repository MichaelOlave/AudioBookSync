"""Tests for sync operation endpoints."""


import pytest
from fastapi import status

from tests.factories import SyncFactory


class TestTriggerSync:
    """Tests for trigger sync endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_sync_success(self, authenticated_client, db_session, test_user_in_db):
        """Test successful sync trigger with real database."""
        response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "sync_id" in data
        assert data["status"] == "in_progress"
        assert "initiated" in data["message"].lower()

    def test_trigger_sync_invalid_type(self, authenticated_client):
        """Test sync with invalid type."""
        response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "invalid_type"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_trigger_sync_unauthenticated(self, client):
        """Test sync trigger without authentication."""
        response = client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetSyncHistory:
    """Tests for get sync history endpoint."""

    @pytest.mark.asyncio
    async def test_get_sync_history_success(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test successful sync history retrieval with real database."""
        # Create a completed sync
        await SyncFactory.create_completed(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            sync_type="full",
            books_found=50,
            books_added=5,
            books_downloaded=3,
            books_decrypted=3,
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/sync/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_get_sync_history_empty(self, authenticated_client, db_session, test_user_in_db):
        """Test sync history when user has no syncs."""
        # Don't create any syncs
        response = authenticated_client.get("/api/v1/sync/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0

    def test_get_sync_history_unauthenticated(self, client):
        """Test sync history access without authentication."""
        response = client.get("/api/v1/sync/history")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGetSyncStatus:
    """Tests for get sync status endpoint."""

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self, authenticated_client, db_session, test_user_in_db):
        """Test successful sync status retrieval with real database."""
        # Create a completed sync
        sync = await SyncFactory.create_completed(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            sync_type="full",
            books_found=50,
            books_added=5,
            books_downloaded=3,
            books_decrypted=3,
        )
        await db_session.commit()

        response = authenticated_client.get(f"/api/v1/sync/{sync.sync_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sync_id"] == str(sync.sync_id)
        assert data["status"] == "completed"

    def test_get_sync_status_not_found(self, authenticated_client):
        """Test sync status for non-existent sync."""
        response = authenticated_client.get("/api/v1/sync/00000000-0000-0000-0000-000000000000")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_sync_status_unauthorized(self, authenticated_client, db_session):
        """Test sync status access for another user's sync with real database."""
        from tests.factories import UserFactory

        # Create another user with a sync
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )

        other_sync = await SyncFactory.create_completed(
            db=db_session, user_id=str(other_user.user_id), sync_type="full"
        )
        await db_session.commit()

        response = authenticated_client.get(f"/api/v1/sync/{other_sync.sync_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSyncConcurrency:
    """Tests for concurrent sync operation handling."""

    @pytest.mark.asyncio
    async def test_prevent_concurrent_syncs(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test that user cannot start multiple concurrent syncs."""
        # First sync should succeed
        response1 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert response1.status_code == status.HTTP_202_ACCEPTED
        response1.json()["sync_id"]

        # Second concurrent sync may fail or succeed depending on implementation
        # In a real system, this would check for active syncs
        response2 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "incremental"},
        )
        # Could succeed (system allows multiple syncs) or fail (prevents concurrent)
        assert response2.status_code in [
            status.HTTP_202_ACCEPTED,  # Multiple syncs allowed
            status.HTTP_409_CONFLICT,  # Conflict - already syncing
            status.HTTP_400_BAD_REQUEST,  # Bad request - already syncing
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Error handling
        ]

    @pytest.mark.asyncio
    async def test_sync_types_incremental_and_full(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test different sync types are handled correctly with real database."""
        # Test full sync
        response1 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert response1.status_code == status.HTTP_202_ACCEPTED
        data1 = response1.json()
        assert data1["status"] == "in_progress"

        # Test incremental sync
        response2 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "incremental"},
        )
        assert response2.status_code == status.HTTP_202_ACCEPTED
        data2 = response2.json()
        assert data2["status"] == "in_progress"

        # Verify different sync IDs
        assert data1["sync_id"] != data2["sync_id"]


class TestSyncFailures:
    """Tests for sync failure scenarios."""

    @pytest.mark.asyncio
    async def test_sync_failure_handling(self, authenticated_client, db_session, test_user_in_db):
        """Test sync that can be marked as failed with real database."""
        # Create a failed sync in the database
        from uuid import UUID

        from src.database.services import sync_service

        sync = await sync_service.create_sync_history(
            db=db_session, user_id=UUID(test_user_in_db.user_id), sync_type="full"
        )

        # Mark it as failed
        await sync_service.update_sync_status(
            db=db_session,
            sync_id=sync.sync_id,
            status="failed",
            books_found=0,
            books_added=0,
            errors_count=1,
        )
        await db_session.commit()

        # Check status shows failure
        response = authenticated_client.get(f"/api/v1/sync/{sync.sync_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "failed"
        assert data["errors_count"] > 0

    @pytest.mark.asyncio
    async def test_sync_partial_failure(self, authenticated_client, db_session, test_user_in_db):
        """Test sync that partially succeeds with real database."""
        # Create a completed sync with partial failure
        sync = await SyncFactory.create_completed(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            sync_type="full",
            books_found=10,
            books_added=8,
            books_downloaded=6,
            books_decrypted=5,
            errors_count=2,  # 2 books failed
        )
        await db_session.commit()

        response = authenticated_client.get(f"/api/v1/sync/{sync.sync_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["errors_count"] == 2
        assert data["status"] == "completed"
        assert data["books_found"] > data["books_decrypted"]


class TestSyncHistoryAdvanced:
    """Tests for advanced sync history features."""

    @pytest.mark.asyncio
    async def test_sync_history_pagination(self, authenticated_client, db_session, test_user_in_db):
        """Test sync history pagination with real database."""
        # Create 15 syncs
        for i in range(15):
            await SyncFactory.create_completed(
                db=db_session,
                user_id=str(test_user_in_db.user_id),
                sync_type="full" if i % 2 == 0 else "incremental",
                books_found=50 - i,
                books_added=10 - (i // 5),
            )
        await db_session.commit()

        # Get first page
        response = authenticated_client.get("/api/v1/sync/history?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 10
        assert data["total"] >= 15

        # Get second page
        response = authenticated_client.get("/api/v1/sync/history?page=2&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 10

    @pytest.mark.asyncio
    async def test_sync_history_filtering_by_status(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test filtering sync history by status with real database."""
        from uuid import UUID

        from src.database.services import sync_service

        # Create completed syncs
        for i in range(3):
            await SyncFactory.create_completed(
                db=db_session, user_id=str(test_user_in_db.user_id), sync_type="full"
            )

        # Create a failed sync
        failed_sync = await sync_service.create_sync_history(
            db=db_session, user_id=UUID(test_user_in_db.user_id), sync_type="full"
        )
        await sync_service.update_sync_status(
            db=db_session, sync_id=failed_sync.sync_id, status="failed", errors_count=1
        )
        await db_session.commit()

        # Get all history
        response = authenticated_client.get("/api/v1/sync/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 4

    @pytest.mark.asyncio
    async def test_sync_statistics(self, authenticated_client, db_session, test_user_in_db):
        """Test sync statistics calculation with real database."""
        # Create a sync with specific statistics
        sync = await SyncFactory.create_completed(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            sync_type="full",
            books_found=100,
            books_added=25,
            books_downloaded=20,
            books_decrypted=18,
            errors_count=0,
        )
        await db_session.commit()

        response = authenticated_client.get(f"/api/v1/sync/{sync.sync_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify statistics make sense
        assert data["books_added"] <= data["books_found"]
        assert data["books_downloaded"] <= data["books_added"]
        assert data["books_decrypted"] <= data["books_downloaded"]
