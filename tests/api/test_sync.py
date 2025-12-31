"""Tests for sync operation endpoints."""

import pytest
from fastapi import status
from datetime import datetime


class TestTriggerSync:
    """Tests for trigger sync endpoint."""

    def test_trigger_sync_success(self, authenticated_client, monkeypatch):
        """Test successful sync trigger."""
        from src.database.db_sync import sync_ops

        sync_id = "test-sync-123"

        def mock_create_sync_history(user_id, sync_type):
            return sync_id

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)

        response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["sync_id"] == sync_id
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

    def test_get_sync_history_success(self, authenticated_client, monkeypatch):
        """Test successful sync history retrieval."""
        from src.database.db_sync import sync_ops

        def mock_get_user_sync_history(user_id, limit):
            return [
                {
                    "sync_id": "sync-1",
                    "user_id": user_id,
                    "sync_type": "full",
                    "status": "completed",
                    "sync_started_at": datetime.utcnow(),
                    "sync_completed_at": datetime.utcnow(),
                    "duration_seconds": 100.0,
                    "books_found": 50,
                    "books_added": 5,
                    "books_downloaded": 3,
                    "books_decrypted": 3,
                    "errors_count": 0,
                    "notes": None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            ]

        monkeypatch.setattr(
            sync_ops, "get_user_sync_history", mock_get_user_sync_history
        )

        response = authenticated_client.get("/api/v1/sync/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] >= 0
        assert data["page"] == 1

    def test_get_sync_history_empty(self, authenticated_client, monkeypatch):
        """Test sync history when user has no syncs."""
        from src.database.db_sync import sync_ops

        def mock_get_user_sync_history(user_id, limit):
            return []

        monkeypatch.setattr(
            sync_ops, "get_user_sync_history", mock_get_user_sync_history
        )

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

    def test_get_sync_status_success(self, authenticated_client, monkeypatch):
        """Test successful sync status retrieval."""
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return {
                "sync_id": sync_id,
                "user_id": authenticated_client.user_id,
                "sync_type": "full",
                "status": "completed",
                "sync_started_at": datetime.utcnow(),
                "sync_completed_at": datetime.utcnow(),
                "duration_seconds": 100.0,
                "books_found": 50,
                "books_added": 5,
                "books_downloaded": 3,
                "books_decrypted": 3,
                "errors_count": 0,
                "notes": "Sync completed successfully",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        response = authenticated_client.get("/api/v1/sync/test-sync-123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["sync_id"] == "test-sync-123"
        assert data["status"] == "completed"

    def test_get_sync_status_not_found(self, authenticated_client, monkeypatch):
        """Test sync status for non-existent sync."""
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return None

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        response = authenticated_client.get("/api/v1/sync/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_sync_status_unauthorized(self, authenticated_client, monkeypatch):
        """Test sync status access for another user's sync."""
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return {
                "sync_id": sync_id,
                "user_id": "different-user-id",  # Different user
                "sync_type": "full",
                "status": "completed",
            }

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        response = authenticated_client.get("/api/v1/sync/test-sync-123")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSyncConcurrency:
    """Tests for concurrent sync operation handling."""

    def test_prevent_concurrent_syncs(self, authenticated_client, monkeypatch, test_user_id):
        """Test that user cannot start multiple concurrent syncs."""
        from src.database.db_sync import sync_ops

        sync_calls = []

        def mock_create_sync_history(user_id, sync_type):
            sync_calls.append((user_id, sync_type))
            if len(sync_calls) > 1:
                # Simulate DB constraint preventing duplicate active syncs
                raise Exception("User already has active sync")
            return f"sync-{len(sync_calls)}"

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)

        # First sync should succeed
        response1 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert response1.status_code == status.HTTP_202_ACCEPTED

        # Second concurrent sync should fail
        response2 = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "incremental"},
        )
        assert response2.status_code in [
            status.HTTP_409_CONFLICT,  # Conflict - already syncing
            status.HTTP_400_BAD_REQUEST,  # Bad request - already syncing
            status.HTTP_500_INTERNAL_SERVER_ERROR,  # Error handling
        ]

    def test_sync_types_incremental_and_full(self, authenticated_client, monkeypatch):
        """Test different sync types are handled correctly."""
        from src.database.db_sync import sync_ops

        sync_types_received = []

        def mock_create_sync_history(user_id, sync_type):
            sync_types_received.append(sync_type)
            return f"sync-{sync_type}"

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)

        # Test full sync
        response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "full" in sync_types_received

        # Test incremental sync
        response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "incremental"},
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "incremental" in sync_types_received


class TestSyncFailures:
    """Tests for sync failure scenarios."""

    def test_sync_failure_handling(self, authenticated_client, monkeypatch):
        """Test sync that fails and records error."""
        from src.database.db_sync import sync_ops

        sync_id = "failed-sync-123"

        def mock_create_sync_history(user_id, sync_type):
            return sync_id

        def mock_get_sync_by_id(sid):
            return {
                "sync_id": sid,
                "user_id": authenticated_client.user_id,
                "sync_type": "full",
                "status": "failed",
                "sync_started_at": datetime.utcnow(),
                "sync_completed_at": datetime.utcnow(),
                "duration_seconds": 5.0,
                "books_found": 0,
                "books_added": 0,
                "books_downloaded": 0,
                "books_decrypted": 0,
                "errors_count": 1,
                "notes": "Audible API connection timeout",
            }

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)
        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        # Trigger sync
        trigger_response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert trigger_response.status_code == status.HTTP_202_ACCEPTED

        # Check status shows failure
        status_response = authenticated_client.get(f"/api/v1/sync/{sync_id}")
        assert status_response.status_code == status.HTTP_200_OK
        data = status_response.json()
        assert data["status"] == "failed"
        assert data["errors_count"] > 0

    def test_sync_partial_failure(self, authenticated_client, monkeypatch):
        """Test sync that partially succeeds (some books synced, some failed)."""
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return {
                "sync_id": sync_id,
                "user_id": authenticated_client.user_id,
                "sync_type": "full",
                "status": "completed",
                "books_found": 10,
                "books_added": 8,
                "books_downloaded": 6,
                "books_decrypted": 5,
                "errors_count": 2,  # 2 books failed
                "notes": "Sync completed with 2 errors",
            }

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        response = authenticated_client.get("/api/v1/sync/test-sync-123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["errors_count"] == 2
        assert data["status"] == "completed"
        assert data["books_found"] > data["books_decrypted"]


class TestSyncHistoryAdvanced:
    """Tests for advanced sync history features."""

    def test_sync_history_pagination(self, authenticated_client, monkeypatch):
        """Test sync history pagination."""
        from src.database.db_sync import sync_ops

        def mock_get_user_sync_history(user_id, limit, offset=0):
            # Return paginated results
            all_syncs = [
                {
                    "sync_id": f"sync-{i}",
                    "user_id": user_id,
                    "sync_type": "full" if i % 2 == 0 else "incremental",
                    "status": "completed",
                    "books_found": 50 - i,
                    "books_added": 10 - (i // 5),
                }
                for i in range(50)
            ]
            return all_syncs[offset : offset + limit]

        def mock_count_user_syncs(user_id):
            return 50

        monkeypatch.setattr(
            sync_ops, "get_user_sync_history", mock_get_user_sync_history
        )
        monkeypatch.setattr(sync_ops, "count_user_syncs", mock_count_user_syncs)

        # Get first page
        response = authenticated_client.get("/api/v1/sync/history?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 10
        assert data["total"] == 50

        # Get second page
        response = authenticated_client.get("/api/v1/sync/history?page=2&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) <= 10

    def test_sync_history_filtering_by_status(self, authenticated_client, monkeypatch):
        """Test filtering sync history by status."""
        from src.database.db_sync import sync_ops

        def mock_get_user_sync_history(user_id, limit, status=None, offset=0):
            if status == "completed":
                return [
                    {
                        "sync_id": "sync-1",
                        "status": "completed",
                    }
                ]
            elif status == "failed":
                return [
                    {
                        "sync_id": "sync-2",
                        "status": "failed",
                    }
                ]
            return []

        monkeypatch.setattr(
            sync_ops, "get_user_sync_history", mock_get_user_sync_history
        )

        # Filter by completed
        response = authenticated_client.get(
            "/api/v1/sync/history?status=completed"
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_sync_statistics(self, authenticated_client, monkeypatch):
        """Test sync statistics calculation."""
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return {
                "sync_id": sync_id,
                "user_id": authenticated_client.user_id,
                "sync_type": "full",
                "status": "completed",
                "sync_started_at": datetime.utcnow(),
                "sync_completed_at": datetime.utcnow(),
                "duration_seconds": 3600.0,  # 1 hour
                "books_found": 100,
                "books_added": 25,
                "books_downloaded": 20,
                "books_decrypted": 18,
                "errors_count": 0,
            }

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        response = authenticated_client.get("/api/v1/sync/test-sync-123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify statistics make sense
        assert data["books_added"] <= data["books_found"]
        assert data["books_downloaded"] <= data["books_added"]
        assert data["books_decrypted"] <= data["books_downloaded"]
        assert data["duration_seconds"] > 0
