"""Tests for books management endpoints."""

import pytest
from fastapi import status


class TestCreateBook:
    """Tests for create/add book endpoint."""

    def test_create_book_success(
        self, authenticated_client, test_book_data, mock_book_ops, monkeypatch
    ):
        """Test successful book creation."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            if asin == test_book_data["asin"]:
                return {**test_book_data, "user_id": authenticated_client.user_id}
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json=test_book_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["asin"] == test_book_data["asin"]
        assert data["title"] == test_book_data["title"]

    def test_create_book_invalid_asin(self, authenticated_client):
        """Test book creation with invalid ASIN."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "TOOSHORT",  # ASIN must be 10 chars
                "title": "Test Book",
                "author": "Test Author",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_missing_title(self, authenticated_client):
        """Test book creation without title."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                # title is missing
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_unauthenticated(self, client, test_book_data):
        """Test book creation without authentication."""
        response = client.post(
            "/api/v1/books/",
            json=test_book_data,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteBook:
    """Tests for delete book endpoint."""

    def test_delete_book_success(
        self, authenticated_client, mock_book_ops, monkeypatch
    ):
        """Test successful book deletion."""
        from src.database.db_books import book_ops

        delete_called = []

        def mock_remove_book(asin):
            delete_called.append(asin)
            return True

        monkeypatch.setattr(book_ops, "remove_book", mock_remove_book)

        response = authenticated_client.delete("/api/v1/books/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()
        assert "B084L6Z6M3" in delete_called

    def test_delete_book_not_found(self, authenticated_client, monkeypatch):
        """Test delete non-existent book."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.delete("/api/v1/books/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_book_unauthorized(self, authenticated_client, monkeypatch):
        """Test delete another user's book."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Some Book",
                "user_id": "different-user-id",  # Different user
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.delete("/api/v1/books/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_book_unauthenticated(self, client):
        """Test book deletion without authentication."""
        response = client.delete("/api/v1/books/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCreateBookWithMetadata:
    """Tests for creating books with comprehensive metadata."""

    def test_create_book_with_optional_fields(
        self, authenticated_client, monkeypatch
    ):
        """Test book creation with all optional fields."""
        from src.database.db_books import book_ops

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "author": "Test Author",
                "narrator": "Test Narrator",
                "series_name": "Test Series",
                "description": "A test book",
                "rating": 4.5,
                "runtime_min": 300,
                "user_id": authenticated_client.user_id,
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
                "author": "Test Author",
                "narrator": "Test Narrator",
                "series_name": "Test Series",
                "description": "A test book",
                "rating": 4.5,
                "runtime_min": 300,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["asin"] == "B084L6Z6M3"
        assert data["narrator"] == "Test Narrator"
        assert data["series_name"] == "Test Series"

    def test_create_book_with_null_optional_fields(
        self, authenticated_client, monkeypatch
    ):
        """Test book creation with null optional fields."""
        from src.database.db_books import book_ops

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Minimal Book",
                "author": None,
                "narrator": None,
                "series_name": None,
                "description": None,
                "rating": None,
                "user_id": authenticated_client.user_id,
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Minimal Book",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["asin"] == "B084L6Z6M3"
        assert data["title"] == "Minimal Book"

    def test_create_book_invalid_rating_too_high(self, authenticated_client):
        """Test book creation with invalid rating (> 5)."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
                "rating": 5.5,  # Invalid
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_invalid_rating_negative(self, authenticated_client):
        """Test book creation with negative rating."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
                "rating": -1.0,  # Invalid
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_invalid_runtime_negative(self, authenticated_client):
        """Test book creation with negative runtime."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
                "runtime_min": -100,  # Invalid
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDuplicateBookHandling:
    """Tests for handling duplicate book entries."""

    def test_create_duplicate_book_upsert(
        self, authenticated_client, test_book_data, monkeypatch
    ):
        """Test that creating duplicate book triggers upsert."""
        from src.database.db_books import book_ops

        add_book_calls = []

        def mock_add_book(asin, user_id, title, **kwargs):
            add_book_calls.append((asin, user_id, title))
            return True

        def mock_get_book_by_asin(asin):
            return {**test_book_data, "user_id": authenticated_client.user_id}

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Create book first time
        response1 = authenticated_client.post(
            "/api/v1/books/",
            json=test_book_data,
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Create same book again (upsert)
        response2 = authenticated_client.post(
            "/api/v1/books/",
            json=test_book_data,
        )
        assert response2.status_code == status.HTTP_201_CREATED

        # Both calls should have been made (upsert behavior)
        assert len(add_book_calls) == 2


class TestBookResponseFormat:
    """Tests for book response format and data integrity."""

    def test_book_response_contains_required_fields(
        self, authenticated_client, monkeypatch
    ):
        """Test that book response includes all required fields."""
        from src.database.db_books import book_ops

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "author": "Test Author",
                "user_id": authenticated_client.user_id,
                "created_at": "2024-12-20T10:00:00",
                "updated_at": "2024-12-20T10:00:00",
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
                "author": "Test Author",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "asin" in data
        assert "title" in data
        assert "author" in data
        assert "user_id" in data

    def test_book_password_not_in_response(
        self, authenticated_client, monkeypatch
    ):
        """Test that sensitive data is not included in response."""
        from src.database.db_books import book_ops

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "Test Book",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Sensitive fields should not be present
        assert "password" not in data
        assert "password_hash" not in data


class TestBookValidation:
    """Tests for book input validation."""

    def test_create_book_empty_title(self, authenticated_client):
        """Test book creation with empty title."""
        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": "",  # Empty
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_book_very_long_title(self, authenticated_client, monkeypatch):
        """Test book creation with very long title."""
        from src.database.db_books import book_ops

        very_long_title = "A" * 1000

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": very_long_title,
                "user_id": authenticated_client.user_id,
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": very_long_title,
            },
        )

        # Should handle long titles gracefully
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_create_book_special_characters_in_title(
        self, authenticated_client, monkeypatch
    ):
        """Test book creation with special characters in title."""
        from src.database.db_books import book_ops

        special_title = "Test Book: Café & Naïve™ 中文"

        def mock_add_book(*args, **kwargs):
            return True

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": special_title,
                "user_id": authenticated_client.user_id,
            }

        monkeypatch.setattr(book_ops, "add_book", mock_add_book)
        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.post(
            "/api/v1/books/",
            json={
                "asin": "B084L6Z6M3",
                "title": special_title,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == special_title
