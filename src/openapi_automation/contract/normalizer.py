from __future__ import annotations

from typing import Any

from .models import Operation, Parameter


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def normalize_openapi(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operations = extract_operations(document)
    return {operation.key: operation.as_dict() for operation in sorted(operations, key=lambda item: item.key)}


def extract_operations(document: dict[str, Any]) -> list[Operation]:
    paths = document.get("paths", {})
    if not isinstance(paths, dict):
        raise TypeError("OpenAPI document paths must be an object.")

    operations: list[Operation] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = _parameters(path_item.get("parameters", []))
        for method, operation_item in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation_item, dict):
                continue
            operation_parameters = _merge_parameters(path_parameters, _parameters(operation_item.get("parameters", [])))
            request_body = operation_item.get("requestBody") or {}
            responses = operation_item.get("responses") or {}
            operations.append(
                Operation(
                    method=method.upper(),
                    path=path,
                    operation_id=operation_item.get("operationId"),
                    summary=operation_item.get("summary") or operation_item.get("description"),
                    tags=tuple(operation_item.get("tags") or []),
                    parameters=tuple(operation_parameters),
                    request_body_required=bool(request_body.get("required", False)) if isinstance(request_body, dict) else False,
                    response_codes=tuple(sorted(str(code) for code in responses.keys())) if isinstance(responses, dict) else tuple(),
                )
            )
    return operations


def _parameters(items: list[Any]) -> list[Parameter]:
    output: list[Parameter] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        schema = item.get("schema") if isinstance(item.get("schema"), dict) else {}
        output.append(
            Parameter(
                name=str(item.get("name", "")),
                location=str(item.get("in", "")),
                required=bool(item.get("required", False)),
                schema_type=schema.get("type"),
            )
        )
    return [item for item in output if item.name and item.location]


def _merge_parameters(base: list[Parameter], override: list[Parameter]) -> list[Parameter]:
    merged = {item.key: item for item in base}
    for item in override:
        merged[item.key] = item
    return sorted(merged.values(), key=lambda item: item.key)
