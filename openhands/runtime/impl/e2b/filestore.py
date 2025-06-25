from typing import Protocol

from openhands.storage.files import FileStore
from e2b.sandbox_sync.filesystem.filesystem import Filesystem


class SupportsFilesystemOperations(Protocol):
    def write(self, path: str, contents: str | bytes) -> None: ...
    def read(self, path: str) -> str: ...
    def list(self, path: str) -> list[str]: ...
    def delete(self, path: str) -> None: ...


class E2BFileStore(FileStore):
    def __init__(self, filesystem: Filesystem) -> None:
        self.filesystem = filesystem

    def write(self, path: str, contents: str | bytes) -> None:
        self.filesystem.write(path, contents)

    def read(self, path: str) -> str:
        if not self._exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        return self.filesystem.read(path)

    def list(self, path: str) -> list[str]:
        """List files in a directory."""
        if not self._exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        try:
            return [entry.name for entry in self.filesystem.list(path)]
        except Exception as e:
            raise RuntimeError(f"Error listing files in {path}: {e}") from e

    def delete(self, path: str) -> None:
        self.filesystem.remove(path)

    def _exists(self, path: str) -> bool:
        """Check if a file exists."""
        return self.filesystem.exists(path)
