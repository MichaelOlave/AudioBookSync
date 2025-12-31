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


class TestPaginationEdgeCases:
    """Tests for pagination edge cases."""

    def test_pagination_page_zero(self, authenticated_client, mock_book_ops):
        """Test pagination with page 0 (invalid)."""
        response = authenticated_client.get("/api/v1/library/?page=0")

        # Page 0 is invalid (pages start at 1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_negative_page(self, authenticated_client, mock_book_ops):
        """Test pagination with negative page number."""
        response = authenticated_client.get("/api/v1/library/?page=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_page_exceeds_max(self, authenticated_client, mock_book_ops):
        """Test pagination when page number exceeds available pages."""
        response = authenticated_client.get("/api/v1/library/?page=9999")

        # Should succeed but return empty or adjust to last page
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    def test_pagination_zero_page_size(self, authenticated_client, mock_book_ops):
        """Test pagination with page_size=0."""
        response = authenticated_client.get("/api/v1/library/?page_size=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_negative_page_size(self, authenticated_client, mock_book_ops):
        """Test pagination with negative page_size."""
        response = authenticated_client.get("/api/v1/library/?page_size=-10")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_page_size_exceeds_max(self, authenticated_client, mock_book_ops):
        """Test pagination when page_size exceeds maximum."""
        response = authenticated_client.get("/api/v1/library/?page_size=1000")

        # Max is 100
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_page_size_one(self, authenticated_client, monkeypatch):
        """Test pagination with page_size=1."""
        from src.database.db_books import book_ops

        def mock_get_user_books(user_id):
            # Return 3 books
            return [
                {
                    "asin": f"B08{i}",
                    "title": f"Book {i}",
                    "user_id": user_id,
                    "author": "Author",
                }
                for i in range(3)
            ]

        monkeypatch.setattr(book_ops, "get_user_books", mock_get_user_books)

        response = authenticated_client.get("/api/v1/library/?page_size=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert data["page_size"] == 1
        assert data["pages"] == 3
        assert len(data["items"]) == 1

    def test_pagination_max_page_size(self, authenticated_client, mock_book_ops):
        """Test pagination with maximum allowed page_size."""
        response = authenticated_client.get("/api/v1/library/?page_size=100")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_size"] == 100


class TestLibraryAudibleFetch:
    """Tests for Audible library fetch endpoint."""

    def test_fetch_audible_library_unauthorized(self, client):
        """Test Audible fetch without authentication."""
        response = client.get("/api/v1/library/audible/fetch")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_fetch_audible_library_no_credentials(self, authenticated_client, monkeypatch):
        """Test Audible fetch when user has no credentials."""
        from src.database.db_users import user_ops

        def mock_get_cursor():
            class MockCursor:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

                def execute(self, *args, **kwargs):
                    pass

                def fetchone(self):
                    return None  # No credentials

            return MockCursor()

        monkeypatch.setattr(user_ops.db_pool, "get_cursor", mock_get_cursor)

        response = authenticated_client.get("/api/v1/library/audible/fetch")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "credentials not configured" in data["detail"].lower()

    def test_fetch_audible_library_num_results_validation(self, authenticated_client):
        """Test num_results parameter validation."""
        # Test 0 (invalid)
        response = authenticated_client.get("/api/v1/library/audible/fetch?num_results=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test > 1000 (exceeds max)
        response = authenticated_client.get(
            "/api/v1/library/audible/fetch?num_results=1001"
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_fetch_audible_library_page_parameter(self, authenticated_client):
        """Test page parameter in Audible fetch."""
        # Negative page should be invalid
        response = authenticated_client.get("/api/v1/library/audible/fetch?page=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLibraryResponseFormat:
    """Tests for library response format and data integrity."""

    def test_library_response_contains_all_fields(self, authenticated_client, mock_book_ops):
        """Test that library response includes all required fields."""
        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check pagination fields
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data

        # Check book fields
        if data["items"]:
            book = data["items"][0]
            assert "asin" in book
            assert "title" in book
            assert "author" in book
            assert "user_id" in book

    def test_library_user_isolation(self, authenticated_client, monkeypatch):
        """Test that users only see their own books."""
        from src.database.db_books import book_ops

        def mock_get_user_books(user_id):
            # Return books only for the requesting user
            if user_id == authenticated_client.user_id:
                return [
                    {
                        "asin": "USERBOOK1",
                        "title": "User Book",
                        "user_id": user_id,
                        "author": "User Author",
                    }
                ]
            else:
                return [
                    {
                        "asin": "OTHERBOOK1",
                        "title": "Other Book",
                        "user_id": "other-user-id",
                        "author": "Other Author",
                    }
                ]

        monkeypatch.setattr(book_ops, "get_user_books", mock_get_user_books)

        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own books
        for book in data["items"]:
            assert book["user_id"] == authenticated_client.user_id
