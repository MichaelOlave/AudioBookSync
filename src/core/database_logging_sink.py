"""Database logging sink for loguru that stores logs in the database."""

import asyncio
import sys
import threading
import traceback
from queue import Queue
from typing import Any, Dict, Optional

from src.database.engine import AsyncSessionLocal
from src.database.models.application_log import ApplicationLog


class DatabaseLoggingSink:
    """
    Custom loguru sink that writes logs to database asynchronously.

    Uses a queue-based architecture:
    - write() is called synchronously by loguru and immediately returns (non-blocking)
    - A background worker thread processes the queue asynchronously
    - Logs are batched and inserted in groups
    - Handles errors gracefully with stderr fallback
    """

    def __init__(
        self,
        batch_size: int = 10,
        batch_timeout_seconds: float = 1.0,
        max_queue_size: int = 10000,
    ):
        """
        Initialize the database logging sink.

        Args:
            batch_size: Number of logs to batch before flushing
            batch_timeout_seconds: Max time to wait before flushing partial batch
            max_queue_size: Maximum queue size before rejecting logs
        """
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.max_queue_size = max_queue_size
        self.queue: Queue[Dict[str, Any]] = Queue(maxsize=max_queue_size)
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self._stop_event = threading.Event()

    def write(self, message: Any) -> None:
        """
        Called by loguru for each log message.

        This is synchronous and must not block, so we immediately queue and return.
        Works with loguru's Message objects.

        Args:
            message: Loguru Message object
        """
        try:
            # Extract record from loguru message
            if hasattr(message, "record"):
                record = self._parse_record(message.record)
            else:
                # Fallback for string messages
                record = self._parse_message(str(message))

            # Try to add to queue without blocking
            if not self.queue.full():
                self.queue.put_nowait(record)
            else:
                # Queue full - log to stderr and drop log
                msg_text = (
                    message.record.get("message") if hasattr(message, "record") else str(message)
                )
                print(
                    f"WARNING: Database logging queue full (max {self.max_queue_size}), "
                    f"dropping log: {msg_text}",
                    file=sys.stderr,
                )

        except Exception as e:
            # If anything fails, log to stderr to avoid blocking loguru
            print(f"ERROR in database logging sink: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    def start(self) -> None:
        """Start the background worker thread."""
        if self.running:
            return

        self.running = True
        self._stop_event.clear()
        self.worker_thread = threading.Thread(daemon=True, target=self._worker)
        self.worker_thread.start()

    def stop(self) -> None:
        """Stop the worker thread and flush remaining logs."""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()

        # Wait for worker thread to finish
        if self.worker_thread and threading.current_thread() != self.worker_thread:
            self.worker_thread.join(timeout=5.0)

    def _worker(self) -> None:
        """Background worker that processes the queue asynchronously."""
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._process_queue())
        finally:
            loop.close()

    async def _process_queue(self) -> None:  # noqa: C901
        """
        Process logs from the queue in batches.

        Runs until stop() is called, batching logs and flushing periodically.
        """
        batch: list[Dict[str, Any]] = []
        last_flush = asyncio.get_event_loop().time()

        while not self._stop_event.is_set() or not self.queue.empty():
            try:
                # Try to get item with timeout
                try:
                    record = self.queue.get(timeout=self.batch_timeout_seconds)
                    batch.append(record)
                except Exception:
                    # Timeout - check if we should flush
                    pass

                current_time = asyncio.get_event_loop().time()
                time_since_flush = current_time - last_flush

                # Flush if batch is full or timeout reached
                if len(batch) >= self.batch_size or (
                    batch and time_since_flush >= self.batch_timeout_seconds
                ):
                    if batch:
                        await self._flush_batch(batch)
                        batch = []
                        last_flush = current_time

            except Exception as e:
                print(f"ERROR processing log batch: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

        # Final flush
        if batch:
            try:
                await self._flush_batch(batch)
            except Exception as e:
                print(f"ERROR on final flush: {e}", file=sys.stderr)

    async def _flush_batch(self, batch: list[Dict[str, Any]]) -> None:
        """
        Flush a batch of logs to the database.

        Args:
            batch: List of log records to insert
        """
        if not batch:
            return

        try:
            async with AsyncSessionLocal() as session:
                # Create ApplicationLog objects
                logs = [ApplicationLog(**record) for record in batch]

                # Bulk insert
                session.add_all(logs)
                await session.commit()

        except Exception as e:
            print(f"ERROR writing logs to database: {e}", file=sys.stderr)
            # In a real implementation, could retry with exponential backoff
            # For now, just log error and continue

    def write_record(self, record: Dict[str, Any]) -> None:
        """
        Write a complete loguru record to the queue.

        This method is designed to be used with loguru's sink parameter
        that receives the full Record object.

        Args:
            record: Loguru Record dictionary
        """
        try:
            log_record = self._parse_record(record)

            # Try to add to queue without blocking
            if not self.queue.full():
                self.queue.put_nowait(log_record)
            else:
                # Queue full - log to stderr and drop log
                print(
                    f"WARNING: Database logging queue full (max {self.max_queue_size}), "
                    f"dropping log: {record.get('message', 'unknown')}",
                    file=sys.stderr,
                )

        except Exception as e:
            # If anything fails, log to stderr to avoid blocking loguru
            print(f"ERROR in database logging sink write_record: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    def _parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse loguru message into a database record.

        This is kept for legacy support if only string messages are passed.

        Args:
            message: Loguru formatted message

        Returns:
            Dictionary ready for ApplicationLog insertion
        """
        return {
            "message": message.strip(),
            "level": "INFO",
            "module": None,
            "function": None,
            "line_number": None,
            "process_name": None,
            "thread_id": None,
            "extra_data": None,
            "exception_type": None,
            "exception_message": None,
            "stack_trace": None,
        }

    def _parse_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a loguru Record into a database record.

        Args:
            record: Loguru Record dictionary with full metadata

        Returns:
            Dictionary ready for ApplicationLog insertion
        """
        exception = record.get("exception")
        stack_trace = None
        exception_type = None
        exception_message = None

        if exception:
            exception_type = exception[0].__name__ if exception[0] else None
            exception_message = str(exception[1]) if exception[1] else None
            if exception[2]:
                stack_trace = "".join(traceback.format_tb(exception[2]))

        # Extract level name - loguru record["level"] is a namedtuple with a 'name' attribute
        level_obj = record.get("level")
        level_name = level_obj.name if hasattr(level_obj, "name") else str(level_obj)

        # Extract process name - loguru record["process"] is a namedtuple
        process_obj = record.get("process")
        process_name = process_obj.name if hasattr(process_obj, "name") else ""

        # Extract thread info - loguru record["thread"] is a namedtuple
        thread_obj = record.get("thread")
        thread_id = str(thread_obj.id) if hasattr(thread_obj, "id") else ""

        return {
            "message": record.get("message", ""),
            "level": level_name,
            "module": record.get("name", ""),
            "function": record.get("function", ""),
            "line_number": str(record.get("line", "")),
            "process_name": process_name,
            "thread_id": thread_id,
            "extra_data": record.get("extra"),
            "exception_type": exception_type,
            "exception_message": exception_message,
            "stack_trace": stack_trace,
        }


def configure_database_logging_sink() -> DatabaseLoggingSink:
    """
    Create and start a database logging sink.

    Returns:
        DatabaseLoggingSink instance that is ready to use
    """
    sink = DatabaseLoggingSink()
    sink.start()
    return sink
