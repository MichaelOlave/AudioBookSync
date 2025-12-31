"""Integration tests for complete AudioBookSync workflows."""

import pytest
from fastapi import status
import uuid


@pytest.fixture
def workflow_user_id():
    """Generate a workflow user ID."""
    return str(uuid.uuid4())


class TestCompleteUserJourney:
    """Tests for complete user workflows from registration to file streaming."""

    def test_user_registration_and_login(self, client, monkeypatch):
        """Test complete registration and login flow."""
        from src.database.db_users import user_ops
        from src.api.security.password import hash_password

        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        }

        user_id = str(uuid.uuid4())

        def mock_get_user_by_username(username):
            return None  # First time

        def mock_get_user_by_email(email):
            return None  # First time

        def mock_create_user_with_password(username, email, password_hash, **kwargs):
            return user_id

        def mock_get_user_by_id(uid):
            return {
                "user_id": uid,
                "username": username,
                "password_hash": hash_password(user_data["password"]),
                "is_active": True,
            }

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)
        monkeypatch.setattr(user_ops, "get_user_by_email", mock_get_user_by_email)
        monkeypatch.setattr(
            user_ops, "create_user_with_password", mock_create_user_with_password
        )
        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        # Step 1: Register user
        register_response = client.post(
            "/api/v1/auth/register",
            json=user_data,
        )
        assert register_response.status_code == status.HTTP_201_CREATED
        reg_data = register_response.json()
        assert reg_data["username"] == user_data["username"]

        # Step 2: Login user
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": user_data["username"],
                "password": user_data["password"],
            },
        )
        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()
        assert "access_token" in login_data
        access_token = login_data["access_token"]

        # Step 3: Access authenticated endpoint with token
        library_response = client.get(
            "/api/v1/library/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert library_response.status_code == status.HTTP_200_OK

    def test_library_sync_workflow(self, authenticated_client, monkeypatch, test_user_id):
        """Test library sync workflow."""
        from src.database.db_sync import sync_ops

        sync_id = str(uuid.uuid4())

        def mock_create_sync_history(user_id, sync_type):
            assert user_id == test_user_id
            assert sync_type in ["full", "incremental", "manual"]
            return sync_id

        def mock_get_sync_by_id(sid):
            return {
                "sync_id": sid,
                "user_id": test_user_id,
                "sync_type": "full",
                "status": "in_progress",
                "books_found": 0,
            }

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)
        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        # Step 1: Trigger sync
        trigger_response = authenticated_client.post(
            "/api/v1/sync/",
            json={"sync_type": "full"},
        )
        assert trigger_response.status_code == status.HTTP_202_ACCEPTED
        trigger_data = trigger_response.json()
        returned_sync_id = trigger_data["sync_id"]

        # Step 2: Check sync status
        status_response = authenticated_client.get(f"/api/v1/sync/{returned_sync_id}")
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["sync_id"] == returned_sync_id
        assert status_data["status"] == "in_progress"

    def test_book_management_workflow(
        self, authenticated_client, monkeypatch, test_user_id
    ):
        """Test book management workflow."""
        from src.database.db_books import book_ops

        asin = "B084L6Z6M3"
        book_data = {
            "asin": asin,
            "title": "Becoming",
            "author": "Michelle Obama",
        }

        add_book_called = []
        remove_book_called = []

        def mock_add_book(asin, user_id, title, **kwargs):
            add_book_called.append((asin, user_id))
            assert user_id == test_user_id
            return True

        def mock_get_book_by_asin(book_asin):
            if book_asin == asin:
                return {
                    "asin": asin,
                    "title": "Becoming",
                    "user_id": test_user_id,
                    "author": "Michelle Obama",
                }
            return None

        def mock_remove_book(book_asin):
            remove_book_called.append(book_asin)
            assert book_asin == asin
            return True

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr(book_ops, "remove_book", mock_remove_book)

        # Step 1: Add book
        add_response = authenticated_client.post(
            "/api/v1/books/",
            json=book_data,
        )
        assert add_response.status_code == status.HTTP_201_CREATED
        assert len(add_book_called) == 1

        # Step 2: Get book details
        details_response = authenticated_client.get(f"/api/v1/library/{asin}")
        assert details_response.status_code == status.HTTP_200_OK
        details_data = details_response.json()
        assert details_data["asin"] == asin

        # Step 3: Delete book
        delete_response = authenticated_client.delete(f"/api/v1/books/{asin}")
        assert delete_response.status_code == status.HTTP_200_OK
        assert len(remove_book_called) == 1

    def test_download_decrypt_workflow(
        self, authenticated_client, monkeypatch, test_user_id
    ):
        """Test download and decrypt workflow."""
        from src.database.db_downloads import download_ops
        from src.database.db_decryptions import decryption_ops

        asin = "B084L6Z6M3"
        download_id = str(uuid.uuid4())
        decryption_id = str(uuid.uuid4())

        def mock_create_download_status(book_asin, status="pending"):
            assert book_asin == asin
            return download_id

        def mock_get_download_by_asin(book_asin):
            if book_asin == asin:
                return {
                    "asin": asin,
                    "status": "completed",
                    "download_path": f"/audiobooks/downloaded/{asin}.m4b",
                }
            return None

        def mock_create_decryption_status(book_asin, download_id=None, **kwargs):
            assert book_asin == asin
            return decryption_id

        def mock_get_download_by_id(did):
            return {
                "download_id": did,
                "status": "completed",
            }

        monkeypatch.setattr(
            download_ops, "create_download_status", mock_create_download_status
        )
        monkeypatch.setattr(
            download_ops, "get_download_by_asin", mock_get_download_by_asin
        )
        monkeypatch.setattr(
            decryption_ops, "create_decryption_status", mock_create_decryption_status
        )
        monkeypatch.setattr(download_ops, "get_download_by_id", mock_get_download_by_id)

        # Step 1: Trigger download
        download_response = authenticated_client.post(
            "/api/v1/downloads/",
            json={"asin": asin},
        )
        assert download_response.status_code == status.HTTP_202_ACCEPTED

        # Step 2: Trigger decryption (after download is complete)
        decryption_response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": asin},
        )
        assert decryption_response.status_code == status.HTTP_202_ACCEPTED

    def test_unauthorized_access_blocked(self, client):
        """Test that unauthorized access is properly blocked."""
        # Try to access protected endpoints without authentication
        endpoints = [
            "/api/v1/library/",
            "/api/v1/books/",
            "/api/v1/sync/",
            "/api/v1/downloads/",
            "/api/v1/decryptions/",
            "/api/v1/files/audiobook/B084L6Z6M3",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN


class TestErrorHandling:
    """Tests for error handling across workflows."""

    def test_invalid_book_asin_propagates_error(self, authenticated_client):
        """Test that invalid ASIN errors propagate correctly."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "INVALID",  # Too short
                "title": "Test",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "error" in data or "detail" in data

    def test_missing_required_fields_error(self, authenticated_client):
        """Test that missing required fields return proper error."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                # Missing title
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_database_error_handling(self, authenticated_client, monkeypatch):
        """Test that database errors are handled gracefully."""
        from src.database.db_books import book_ops

        def mock_add_book(*args, **kwargs):
            raise Exception("Database connection error")

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
            },
        )

        # Should return 500 Internal Server Error
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
