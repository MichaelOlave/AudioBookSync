"""Tests for books management endpoints."""


import pytest
from fastapi import status

from tests.factories import BookFactory


class TestCreateBook:
    """Tests for create/add book endpoint."""

    @pytest.mark.asyncio
    async def test_create_book_success(
        self, authenticated_client, test_book_data, db_session, test_user_in_db
    ):
        """Test successful book creation with real database."""
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

    @pytest.mark.asyncio
    async def test_delete_book_success(self, authenticated_client, db_session, test_user_in_db):
        """Test successful book deletion with real database."""
        # Create a book first
        book = await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        response = authenticated_client.delete(f"/api/v1/books/{book.asin}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

    def test_delete_book_not_found(self, authenticated_client):
        """Test delete non-existent book."""
        response = authenticated_client.delete("/api/v1/books/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_book_unauthorized(self, authenticated_client, db_session):
        """Test delete another user's book with real database."""
        from tests.factories import UserFactory

        # Create another user with a book
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )

        book = await BookFactory.create(
            db=db_session, user_id=str(other_user.user_id), asin="B084L6Z6M3", title="Other Book"
        )
        await db_session.commit()

        response = authenticated_client.delete(f"/api/v1/books/{book.asin}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_book_unauthenticated(self, client):
        """Test book deletion without authentication."""
        response = client.delete("/api/v1/books/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestCreateBookWithMetadata:
    """Tests for creating books with comprehensive metadata."""

    @pytest.mark.asyncio
    async def test_create_book_with_optional_fields(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test book creation with all optional fields using real database."""
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
        assert data["title"] == "Test Book"

    @pytest.mark.asyncio
    async def test_create_book_with_null_optional_fields(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test book creation with null optional fields using real database."""
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

    @pytest.mark.asyncio
    async def test_create_duplicate_book_upsert(
        self, authenticated_client, test_book_data, db_session, test_user_in_db
    ):
        """Test that creating duplicate book triggers upsert with real database."""
        # Create book first time
        response1 = authenticated_client.post(
            "/api/v1/books/",
            json=test_book_data,
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Create same book again (upsert - should succeed)
        response2 = authenticated_client.post(
            "/api/v1/books/",
            json=test_book_data,
        )
        assert response2.status_code == status.HTTP_201_CREATED

        # Both should return same book (upsert behavior)
        data1 = response1.json()
        data2 = response2.json()
        assert data1["asin"] == data2["asin"]


class TestBookResponseFormat:
    """Tests for book response format and data integrity."""

    @pytest.mark.asyncio
    async def test_book_response_contains_required_fields(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test that book response includes all required fields with real database."""
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
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_book_password_not_in_response(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test that sensitive data is not included in response with real database."""
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

    @pytest.mark.asyncio
    async def test_create_book_very_long_title(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test book creation with very long title using real database."""
        very_long_title = "A" * 1000

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

    @pytest.mark.asyncio
    async def test_create_book_special_characters_in_title(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test book creation with special characters in title using real database."""
        special_title = "Test Book: Café & Naïve™ 中文"

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
