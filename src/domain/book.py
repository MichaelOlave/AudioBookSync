"""Book domain model for type-safe operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    """Immutable book domain model.

    Represents a book with ASIN and title as core attributes,
    with optional metadata fields. Provides conversion methods
    for compatibility with different layers (operations, API).

    Attributes:
        asin: Amazon Standard Identification Number (unique identifier)
        title: Book title
        author: Author name (optional)
        narrator: Narrator name (optional)
        runtime_min: Runtime in minutes (optional)
        purchase_date: Date book was purchased (optional)
    """

    asin: str
    title: str
    author: Optional[str] = None
    narrator: Optional[str] = None
    runtime_min: Optional[int] = None
    purchase_date: Optional[str] = None

    def to_operations_format(self) -> list:
        """Convert to operations format [asin, title].

        Used when calling download_book() and decrypt_book()
        which expect a list [asin, title] for backward compatibility.

        Returns:
            List with [asin, title]
        """
        return [self.asin, self.title]

    def to_api_format(self) -> dict:
        """Convert to API dictionary format.

        Used for returning book data in API responses
        with full metadata.

        Returns:
            Dictionary with all book attributes
        """
        return {
            "asin": self.asin,
            "title": self.title,
            "author": self.author,
            "narrator": self.narrator,
            "runtime_min": self.runtime_min,
            "purchase_date": self.purchase_date,
        }

    @classmethod
    def from_list(cls, book_list: list) -> "Book":
        """Create Book from operations format [asin, title].

        Converts from the list format used by downloader/decryptor
        functions into a typed Book domain model.

        Args:
            book_list: List with [asin, title] (minimum 2 elements)

        Returns:
            Book instance

        Raises:
            IndexError: If list has fewer than 2 elements
            ValueError: If asin or title is empty
        """
        if len(book_list) < 2:
            raise ValueError("book_list must contain at least [asin, title]")

        asin = book_list[0]
        title = book_list[1]

        if not asin or not title:
            raise ValueError("asin and title cannot be empty")

        return cls(asin=asin, title=title)

    @classmethod
    def from_dict(cls, book_dict: dict) -> "Book":
        """Create Book from API/database dictionary format.

        Converts from dictionary format (with optional metadata)
        into a typed Book domain model.

        Args:
            book_dict: Dictionary with at least 'asin' and 'title' keys

        Returns:
            Book instance

        Raises:
            KeyError: If 'asin' or 'title' keys are missing
            ValueError: If asin or title is empty
        """
        asin = book_dict.get("asin")
        title = book_dict.get("title")

        if not asin or not title:
            raise ValueError("asin and title cannot be empty")

        return cls(
            asin=asin,
            title=title,
            author=book_dict.get("author"),
            narrator=book_dict.get("narrator"),
            runtime_min=book_dict.get("runtime_min"),
            purchase_date=book_dict.get("purchase_date"),
        )
