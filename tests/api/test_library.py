"""Tests for library endpoints."""

import pytest
from fastapi import status


class TestGetLibrary:
    """Tests for get library endpoint."""

    def test_get_library_success(self, authenticated_client, mock_book_ops):
        """Test successful library retrieval."""
        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert data["page"] == 1

    def test_get_library_pagination(self, authenticated_client, mock_book_ops):
        """Test library pagination."""
        response = authenticated_client.get("/api/v1/library/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_get_library_unauthorized(self, client):
        """Test library access without authentication."""
        response = client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_library_empty(self, authenticated_client, monkeypatch):
        """Test library retrieval when user has no books."""
        from src.database.db_books import book_ops

        def mock_get_user_books(user_id):
            return []

        monkeypatch.setattr(book_ops, "get_user_books", mock_get_user_books)

        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


class TestGetBookDetails:
    """Tests for get book details endpoint."""

    def test_get_book_details_success(self, authenticated_client, mock_book_ops):
        """Test successful book details retrieval."""
        response = authenticated_client.get("/api/v1/library/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["asin"] == "B084L6Z6M3"
        assert data["title"] == "Becoming"
        assert data["author"] == "Michelle Obama"

    def test_get_book_details_not_found(self, authenticated_client, monkeypatch):
        """Test book details for non-existent book."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/library/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_book_details_unauthorized(self, authenticated_client, monkeypatch):
        """Test book details access for another user's book."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Some Book",
                "user_id": "different-user-id",  # Different user
                "author": "Some Author",
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/library/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_book_details_unauthenticated(self, client):
        """Test book details access without authentication."""
        response = client.get("/api/v1/library/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN
