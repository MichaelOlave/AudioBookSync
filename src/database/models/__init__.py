"""SQLAlchemy ORM models for AudioBookSync."""

from src.database.models.application_log import ApplicationLog
from src.database.models.base import Base, generate_uuid, get_current_timestamp
from src.database.models.book import Book
from src.database.models.book_availability import BookAvailability
from src.database.models.book_metadata import BookMetadataJson
from src.database.models.companion_material import CompanionMaterial
from src.database.models.contributor import BookContributor, Contributor
from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus
from src.database.models.error import ErrorLog
from src.database.models.genre import BookGenre, Genre
from src.database.models.media_info import MediaInfo
from src.database.models.reading_progress import ReadingProgress
from src.database.models.sync import SyncHistory
from src.database.models.user import User

__all__ = [
    "ApplicationLog",
    "Base",
    "generate_uuid",
    "get_current_timestamp",
    "User",
    "Book",
    "DownloadStatus",
    "DecryptionStatus",
    "SyncHistory",
    "ErrorLog",
    "Genre",
    "BookGenre",
    "Contributor",
    "BookContributor",
    "MediaInfo",
    "ReadingProgress",
    "BookAvailability",
    "CompanionMaterial",
    "BookMetadataJson",
]
