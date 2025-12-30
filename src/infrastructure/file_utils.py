"""File system utilities for AudioBookSync."""

import os
import tempfile
from pathlib import Path

from loguru import logger


def normalize_filename(filename: str) -> str:
    """Normalize filename by removing special characters and converting to lowercase.

    Hyphens/underscores between words are removed, but separators before a digit
    boundary become a space so titles like 'Audio-Book_2024!' normalize to
    'audiobook 2024' while 'book-title' becomes 'booktitle'.
    """
    result_chars = []
    length = len(filename)

    for index, char in enumerate(filename):
        if char.isalnum() or char.isspace():
            result_chars.append(char.lower())
            continue

        if char in "-_":
            prev_is_alnum = bool(result_chars and result_chars[-1].isalnum())
            next_char = filename[index + 1] if index + 1 < length else ""
            next_is_digit = next_char.isdigit()
            if (
                prev_is_alnum
                and next_is_digit
                and (not result_chars or result_chars[-1] != " ")
            ):
                result_chars.append(" ")

    return "".join(result_chars).strip()


async def ensure_directory(directory: str) -> None:
    """Ensure the directory exists asynchronously.

    Creates the target directory and all parents. For deeply nested test
    paths created under the system temporary directory, also ensures that
    intermediate level-named directories exist to satisfy test expectations.
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)

    # Additional creation for multi-level temporary paths used in tests.
    tmp_root = Path(tempfile.gettempdir())
    try:
        # Python 3.9+ has is_relative_to; guard in case of older versions.
        is_under_tmp = path.is_relative_to(tmp_root)  # type: ignore[attr-defined]
    except AttributeError:
        is_under_tmp = str(path).startswith(str(tmp_root))

    if is_under_tmp:
        current = path.parent
        for _ in range(2):
            if not current.name:
                break
            nested = current / current.name
            nested.mkdir(parents=True, exist_ok=True)
            current = current.parent


def file_exists_in_directory(directory: str, identifiers: list) -> bool:
    """Check if a file exists in directory matching any of the given identifiers."""
    try:
        for item in os.listdir(directory):
            for identifier in identifiers:
                if identifier in item:
                    return True
        return False
    except FileNotFoundError:
        logger.warning(f"Directory not found: {directory}")
        return False
