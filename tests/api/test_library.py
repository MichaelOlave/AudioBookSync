"""Tests for library endpoints."""

import pytest
from fastapi import status

from tests.factories import BookFactory


class TestGetLibrary:
    """Tests for get library endpoint."""

    @pytest.mark.asyncio
    async def test_get_library_success(self, authenticated_client, db_session, test_user_in_db):
        """Test successful library retrieval with real database."""
        # Create a test book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Becoming",
            author="Michelle Obama",
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert data["page"] == 1
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_library_pagination(self, authenticated_client, db_session, test_user_in_db):
        """Test library pagination with real database."""
        # Create multiple books
        for i in range(5):
            await BookFactory.create(
                db=db_session,
                user_id=str(test_user_in_db.user_id),
                asin=f"B08{i:06d}",
                title=f"Book {i}",
                author=f"Author {i}",
            )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] >= 5

    def test_get_library_unauthorized(self, client):
        """Test library access without authentication."""
        response = client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_library_empty(self, authenticated_client, db_session, test_user_in_db):
        """Test library retrieval when user has no books."""
        # Don't create any books - should return empty list
        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


class TestGetBookDetails:
    """Tests for get book details endpoint."""

    @pytest.mark.asyncio
    async def test_get_book_details_success(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test successful book details retrieval with real database."""
        # Create a test book
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Becoming",
            author="Michelle Obama",
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["asin"] == "B084L6Z6M3"
        assert data["title"] == "Becoming"
        assert data["author"] == "Michelle Obama"

    def test_get_book_details_not_found(self, authenticated_client):
        """Test book details for non-existent book."""
        response = authenticated_client.get("/api/v1/library/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_book_details_unauthorized(self, authenticated_client, client, db_session):
        """Test book details access for another user's book."""
        from tests.factories import UserFactory

        # Create a different user with a book
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )
        await BookFactory.create(
            db=db_session,
            user_id=str(other_user.user_id),
            asin="B999999999",
            title="Other Book",
            author="Other Author",
        )
        await db_session.commit()

        # Try to access another user's book with authenticated_client
        response = authenticated_client.get("/api/v1/library/B999999999")

        # Should either return 404 (book not found for this user) or 403 (forbidden)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_get_book_details_unauthenticated(self, client):
        """Test book details access without authentication."""
        response = client.get("/api/v1/library/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPaginationEdgeCases:
    """Tests for pagination edge cases."""

    def test_pagination_page_zero(self, authenticated_client):
        """Test pagination with page 0 (invalid)."""
        response = authenticated_client.get("/api/v1/library/?page=0")

        # Page 0 is invalid (pages start at 1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_negative_page(self, authenticated_client):
        """Test pagination with negative page number."""
        response = authenticated_client.get("/api/v1/library/?page=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_pagination_page_exceeds_max(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test pagination when page number exceeds available pages."""
        # Create one book
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B001",
            title="Book 1",
            author="Author",
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/?page=9999")

        # Should succeed but return empty or adjust to last page
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data

    def test_pagination_zero_page_size(self, authenticated_client):
        """Test pagination with page_size=0."""
        response = authenticated_client.get("/api/v1/library/?page_size=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_negative_page_size(self, authenticated_client):
        """Test pagination with negative page_size."""
        response = authenticated_client.get("/api/v1/library/?page_size=-10")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_page_size_exceeds_max(self, authenticated_client):
        """Test pagination when page_size exceeds maximum."""
        response = authenticated_client.get("/api/v1/library/?page_size=1000")

        # Max is 100
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_pagination_page_size_one(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test pagination with page_size=1 using real database."""
        # Create 3 books
        for i in range(3):
            await BookFactory.create(
                db=db_session,
                user_id=str(test_user_in_db.user_id),
                asin=f"B08{i}",
                title=f"Book {i}",
                author="Author",
            )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/?page_size=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 3
        assert data["page_size"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_pagination_max_page_size(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test pagination with maximum allowed page_size."""
        # Create a book to ensure there's something to paginate
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B100",
            title="Book",
            author="Author",
        )
        await db_session.commit()

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

    @pytest.mark.asyncio
    async def test_fetch_audible_library_no_credentials(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test Audible fetch when user has no credentials."""
        # User created without Audible credentials
        # (test_user_in_db by default has no credentials set)
        response = authenticated_client.get("/api/v1/library/audible/fetch")

        # Should fail because user has no Audible credentials
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

    def test_fetch_audible_library_num_results_validation(self, authenticated_client):
        """Test num_results parameter validation."""
        # Test 0 (invalid)
        response = authenticated_client.get("/api/v1/library/audible/fetch?num_results=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test > 1000 (exceeds max)
        response = authenticated_client.get("/api/v1/library/audible/fetch?num_results=1001")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_fetch_audible_library_page_parameter(self, authenticated_client):
        """Test page parameter in Audible fetch."""
        # Negative page should be invalid
        response = authenticated_client.get("/api/v1/library/audible/fetch?page=-1")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLibraryResponseFormat:
    """Tests for library response format and data integrity."""

    @pytest.mark.asyncio
    async def test_library_response_contains_all_fields(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test that library response includes all required fields."""
        # Create a test book
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B123",
            title="Test Book",
            author="Test Author",
        )
        await db_session.commit()

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

    @pytest.mark.asyncio
    async def test_library_user_isolation(self, authenticated_client, db_session, test_user_in_db):
        """Test that users only see their own books with real database."""
        from tests.factories import UserFactory

        # Create another user with a book
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )

        # Create book for test_user_in_db
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="USERBOOK1",
            title="User Book",
            author="User Author",
        )

        # Create book for other_user
        await BookFactory.create(
            db=db_session,
            user_id=str(other_user.user_id),
            asin="OTHERBOOK1",
            title="Other Book",
            author="Other Author",
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/library/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own books
        for book in data["items"]:
            assert book["user_id"] == authenticated_client.user_id
