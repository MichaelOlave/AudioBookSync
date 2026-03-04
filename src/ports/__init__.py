"""Ports for hexagonal architecture.

This package contains abstract interfaces (ports) that define contracts
for external integrations and adapters.
"""

from src.ports.file_storage_port import FileStoragePort

__all__ = ["FileStoragePort"]
