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
