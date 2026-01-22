"""Retry tasks for failed operations."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select

from src.celery_app import celery_app
from src.celery_app.tasks.decrypt_tasks import execute_decrypt_task
from src.celery_app.tasks.download_tasks import execute_download_task
from src.core.config import Config
from src.database.engine import AsyncSessionLocal
from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus


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
