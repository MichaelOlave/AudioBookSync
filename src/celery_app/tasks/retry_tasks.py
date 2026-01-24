"""Retry tasks for failed operations."""

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import and_, select

from src.celery_app import celery_app
from src.celery_app.tasks.decrypt_tasks import execute_decrypt_task
from src.celery_app.tasks.download_tasks import execute_download_task
from src.core.config import Config
from src.database.engine import AsyncSessionLocal
from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus
from src.database.services import user_service


@celery_app.task(name="retry_failed_downloads")
def retry_failed_downloads() -> dict:
    """Retry failed download operations that haven't exceeded max attempts."""
    return asyncio.run(_async_retry_downloads())


async def _async_retry_downloads() -> dict:
    """Async implementation of download retry."""
    try:
        logger.info("Starting failed download retry")

        retry_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=Config.CELERY_RETRY_DELAY
        )

        async with AsyncSessionLocal() as db:
            # Find failed downloads eligible for retry
            result = await db.execute(
                select(
                    DownloadStatus.download_id,
                    DownloadStatus.user_id,
                    DownloadStatus.asin,
                    DownloadStatus.title,
                    DownloadStatus.attempt_number,
                ).where(
                    and_(
                        DownloadStatus.status == "failed",
                        DownloadStatus.attempt_number < Config.CELERY_MAX_RETRIES,
                        DownloadStatus.updated_at < retry_cutoff,
                    )
                )
            )

            failed_downloads = result.fetchall()

            retry_count = 0
            for (
                download_id,
                user_id,
                asin,
                title,
                attempt_number,
            ) in failed_downloads:
                # Find the download record and update it
                download_record = await db.execute(
                    select(DownloadStatus).where(
                        DownloadStatus.download_id == download_id
                    )
                )
                download = download_record.scalars().first()

                if download:
                    # Increment attempt number and reset status to pending
                    download.attempt_number = attempt_number + 1
                    download.status = "pending"
                    download.updated_at = datetime.now(timezone.utc)
                    await db.flush()

                    # Enqueue new download task with exponential backoff
                    backoff = Config.CELERY_RETRY_DELAY * (2 ** attempt_number)
                    execute_download_task.apply_async(
                        args=[
                            str(user_id),
                            str(download_id),
                            {"asin": asin, "title": title},
                        ],
                        countdown=backoff,
                    )
                    retry_count += 1

            await db.commit()

        logger.info(f"Retrying {retry_count} failed downloads")
        return {"retry_count": retry_count}

    except Exception as e:
        logger.error(f"Download retry failed: {e}", exc_info=True)
        return {"error": str(e)}


@celery_app.task(name="retry_failed_decrypts")
def retry_failed_decrypts() -> dict:
    """Retry failed decryption operations that haven't exceeded max attempts."""
    return asyncio.run(_async_retry_decrypts())


async def _async_retry_decrypts() -> dict:
    """Async implementation of decryption retry."""
    try:
        logger.info("Starting failed decryption retry")

        retry_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=Config.CELERY_RETRY_DELAY
        )

        async with AsyncSessionLocal() as db:
            # Find failed decryptions eligible for retry
            result = await db.execute(
                select(
                    DecryptionStatus.decryption_id,
                    DecryptionStatus.user_id,
                    DecryptionStatus.asin,
                    DecryptionStatus.title,
                    DecryptionStatus.attempt_number,
                ).where(
                    and_(
                        DecryptionStatus.status == "failed",
                        DecryptionStatus.attempt_number < Config.CELERY_MAX_RETRIES,
                        DecryptionStatus.updated_at < retry_cutoff,
                    )
                )
            )

            failed_decrypts = result.fetchall()

            retry_count = 0
            for (
                decryption_id,
                user_id,
                asin,
                title,
                attempt_number,
            ) in failed_decrypts:
                # Find the decryption record and update it
                decrypt_record = await db.execute(
                    select(DecryptionStatus).where(
                        DecryptionStatus.decryption_id == decryption_id
                    )
                )
                decrypt = decrypt_record.scalars().first()

                if decrypt:
                    # Increment attempt number and reset status to pending
                    decrypt.attempt_number = attempt_number + 1
                    decrypt.status = "pending"
                    decrypt.updated_at = datetime.now(timezone.utc)
                    await db.flush()

                    # Enqueue new decrypt task with exponential backoff
                    backoff = Config.CELERY_RETRY_DELAY * (2 ** attempt_number)
                    execute_decrypt_task.apply_async(
                        args=[
                            str(user_id),
                            str(decryption_id),
                            {"asin": asin, "title": title},
                        ],
                        countdown=backoff,
                    )
                    retry_count += 1

            await db.commit()

        logger.info(f"Retrying {retry_count} failed decryptions")
        return {"retry_count": retry_count}

    except Exception as e:
        logger.error(f"Decryption retry failed: {e}", exc_info=True)
        return {"error": str(e)}


@celery_app.task(name="retry_failed_decrypts_from_minio")
def retry_failed_decrypts_from_minio() -> dict:
    """Retry failed decryptions with encrypted files stored in MinIO."""
    return asyncio.run(_async_retry_decrypts_from_minio())


async def _async_retry_decrypts_from_minio() -> dict:
    """Async implementation of decryption retry from MinIO encrypted files."""
    try:
        logger.info("Starting failed decryption retry from MinIO encrypted files")

        from src.database.models.book import Book
        from src.operations.decryptor import decrypt_book
        from src.infrastructure.storage_service import StorageService

        async with AsyncSessionLocal() as db:
            # Find decryptions with encrypted files stored in MinIO (failed decryptions)
            result = await db.execute(
                select(DecryptionStatus).where(
                    and_(
                        DecryptionStatus.encrypted_file_object_key.isnot(None),
                        DecryptionStatus.status == "failed",
                    )
                )
            )

            failed_decrypts = result.scalars().all()

            retry_count = 0
            for decrypt_record in failed_decrypts:
                try:
                    # Get book info for retry
                    book_result = await db.execute(
                        select(Book).where(Book.asin == decrypt_record.asin)
                    )
                    book = book_result.scalars().first()

                    if not book:
                        logger.warning(f"Book not found for ASIN {decrypt_record.asin}")
                        continue

                    if not decrypt_record.user_id:
                        logger.warning(
                            f"Missing user_id for decryption {decrypt_record.decryption_id}"
                        )
                        continue

                    user_id = str(decrypt_record.user_id)

                    # Download encrypted file from MinIO
                    storage_service = StorageService()
                    encrypted_file_path = storage_service.get_file(
                        user_id=user_id,
                        object_key=decrypt_record.encrypted_file_object_key,
                    )

                    if not encrypted_file_path:
                        logger.warning(
                            f"Failed to download encrypted file from MinIO: "
                            f"{decrypt_record.encrypted_file_object_key}"
                        )
                        continue

                    user = await user_service.get_user_by_id(db, user_id)
                    activation_bytes = user.activation_bytes if user else None
                    if not activation_bytes:
                        logger.warning(
                            f"Activation bytes not configured for user {user_id}"
                        )
                        continue

                    # Attempt retry decryption
                    book_data = [book.asin, book.title]
                    decrypt_success = await decrypt_book(
                        book=book_data,
                        user_id=user_id,
                        encrypted_file_path=encrypted_file_path,
                        is_retry=True,
                        activation_bytes=activation_bytes,
                    )

                    if decrypt_success:
                        # Update status and clear encrypted_file_object_key
                        decrypt_record.status = "completed"
                        decrypt_record.encrypted_file_object_key = None
                        await db.flush()
                        retry_count += 1
                        logger.info(f"Retry successful for ASIN {decrypt_record.asin}")

                        # Delete encrypted file from MinIO
                        try:
                            storage_service.delete_file(
                                user_id=user_id,
                                object_key=decrypt_record.encrypted_file_object_key,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete encrypted file from MinIO: {e}"
                            )
                    else:
                        logger.warning(f"Retry still failed for ASIN {decrypt_record.asin}")

                except Exception as e:
                    logger.error(f"Error retrying decryption for ASIN {decrypt_record.asin}: {e}")

            await db.commit()

        logger.info(f"Retried {retry_count} failed decryptions from MinIO")
        return {"retry_count": retry_count}

    except Exception as e:
        logger.error(f"Decryption retry from MinIO failed: {e}", exc_info=True)
        return {"error": str(e)}
