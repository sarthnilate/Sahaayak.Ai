import os
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from backend.app.core.config import settings
from backend.app.core.errors import BadRequestError, ResourceNotFoundError


class StorageProvider(ABC):
    """Abstract file storage provider interface."""

    @abstractmethod
    def save_file(self, content: bytes, extension: str) -> str:
        """
        Saves file bytes and returns storage key / relative file path.
        """
        pass

    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """
        Reads and returns file bytes. Raises ResourceNotFoundError if missing.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Deletes stored file. Returns True if deleted, False if not found.
        """
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider with strict path traversal prevention
    and outside-web-root protected storage.
    """

    def __init__(self, base_directory: Optional[str] = None):
        self.base_dir = os.path.abspath(base_directory or settings.UPLOAD_DIR)
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> str:
        """
        Resolves path and enforces that target file cannot escape base_dir (path traversal guard).
        """
        if os.path.isabs(relative_path):
            raise BadRequestError(
                message="Absolute paths not allowed in storage operations",
                error_code="PATH_TRAVERSAL_DETECTED",
            )
        resolved = os.path.abspath(os.path.join(self.base_dir, relative_path))
        if not resolved.startswith(self.base_dir + os.sep) and resolved != self.base_dir:
            raise BadRequestError(
                message="Path traversal detected", error_code="PATH_TRAVERSAL_DETECTED"
            )
        return resolved

    def save_file(self, content: bytes, extension: str) -> str:
        """
        Saves content using a strictly generated server-side UUID filename.
        """
        ext = extension.lower().lstrip(".")
        if ext not in ["jpg", "jpeg", "png", "webp"]:
            raise BadRequestError(
                message=f"Disallowed file extension .{ext}", error_code="INVALID_FILE_TYPE"
            )

        filename = f"{uuid.uuid4().hex}.{ext}"
        target_path = os.path.join(self.base_dir, filename)

        with open(target_path, "wb") as f:
            f.write(content)

        # Return sanitized relative key
        return filename

    def read_file(self, file_path: str) -> bytes:
        safe_path = self._resolve_safe_path(file_path)
        if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
            raise ResourceNotFoundError(
                message="Requested media file not found", error_code="MEDIA_NOT_FOUND"
            )
        with open(safe_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        try:
            safe_path = self._resolve_safe_path(file_path)
            if os.path.exists(safe_path) and os.path.isfile(safe_path):
                os.remove(safe_path)
                return True
            return False
        except Exception:
            return False


# Singleton storage instance
storage_provider = LocalStorageProvider()
