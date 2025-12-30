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
