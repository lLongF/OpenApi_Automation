from __future__ import annotations

import mimetypes
from contextlib import ExitStack
from pathlib import Path
from typing import BinaryIO

from .config import project_path


class MultipartFiles:
    def __init__(self) -> None:
        self._stack = ExitStack()
        self.files: dict[str, tuple[str, BinaryIO, str]] = {}

    def add(self, field_name: str, path: str | Path, content_type: str | None = None) -> None:
        resolved = project_path(path)
        guessed_type = content_type or mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        file_obj = self._stack.enter_context(resolved.open("rb"))
        self.files[field_name] = (resolved.name, file_obj, guessed_type)

    def close(self) -> None:
        self._stack.close()

    def __enter__(self) -> dict[str, tuple[str, BinaryIO, str]]:
        return self.files

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def file_path_by_key(test_data: dict, file_key: str) -> Path:
    try:
        return project_path(test_data["files"][file_key])
    except KeyError as exc:
        raise KeyError(f"Unknown file key: {file_key}") from exc
