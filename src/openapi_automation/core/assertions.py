from __future__ import annotations

from typing import Any

import requests


def response_json(response: requests.Response) -> dict[str, Any]:
    try:
        parsed = response.json()
    except ValueError as exc:
        raise AssertionError(f"Response is not JSON. status={response.status_code}, body={response.text[:300]!r}") from exc
    if not isinstance(parsed, dict):
        raise AssertionError(f"Response JSON root is not an object: {parsed!r}")
    return parsed


def get_json_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def assert_expected_response(response: requests.Response, expected: dict[str, Any]) -> dict[str, Any] | None:
    if "http_status" in expected:
        assert response.status_code == expected["http_status"], response.text
    if "http_status_any" in expected:
        assert response.status_code in expected["http_status_any"], response.text

    if response.headers.get("Content-Type", "").startswith("application/octet-stream"):
        return None

    payload = response_json(response)
    if "code" in expected:
        assert payload.get("code") == expected["code"], payload
    if "code_any" in expected:
        assert payload.get("code") in expected["code_any"], payload
    for field in expected.get("required_fields", []):
        assert field in payload and payload[field] not in (None, ""), payload
    for path in expected.get("json_path_required", []):
        value = get_json_path(payload, path)
        assert value not in (None, ""), payload
    if "message_contains_any" in expected:
        body = response.text
        assert any(item in body for item in expected["message_contains_any"]), body
    return payload
