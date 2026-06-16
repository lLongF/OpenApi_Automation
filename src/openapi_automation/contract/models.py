from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Parameter:
    name: str
    location: str
    required: bool
    schema_type: str | None = None

    @property
    def key(self) -> str:
        return f"{self.location}:{self.name}"


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    operation_id: str | None
    summary: str | None
    tags: tuple[str, ...]
    parameters: tuple[Parameter, ...] = field(default_factory=tuple)
    request_body_required: bool = False
    response_codes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        return f"{self.method.upper()} {self.path}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.upper(),
            "path": self.path,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "tags": list(self.tags),
            "parameters": [
                {
                    "name": item.name,
                    "in": item.location,
                    "required": item.required,
                    "schema_type": item.schema_type,
                }
                for item in self.parameters
            ],
            "request_body_required": self.request_body_required,
            "response_codes": list(self.response_codes),
        }
