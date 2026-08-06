from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
import yaml

from openapi_automation.core.config import project_path


def load_openapi_source_config(source_name: str | None = None) -> dict[str, Any]:
    config_path = project_path("config/openapi_sources.yaml")
    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}
    selected = source_name or os.getenv("OPENAPI_SOURCE") or raw["default"]
    try:
        source = raw["sources"][selected]
    except KeyError as exc:
        raise KeyError(f"Unknown OPENAPI_SOURCE={selected!r}") from exc
    return {"name": selected, **source}


def fetch_openapi_document(source: dict[str, Any], timeout: tuple[int, int] = (30, 120)) -> dict[str, Any]:
    raw_url = os.getenv(source.get("raw_url_env", "")) or source.get("raw_url")
    if raw_url:
        response = requests.get(raw_url, timeout=timeout)
        response.raise_for_status()
        return _parse_document(response.text)

    project_id = os.getenv(source.get("project_id_env", ""))
    access_token = os.getenv(source.get("access_token_env", ""))
    if project_id and access_token:
        url = source["export_api_url"].format(project_id=project_id)
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=source.get("export_options", {}),
            timeout=timeout,
        )
        response.raise_for_status()
        return _extract_openapi_from_response(response)

    raise RuntimeError(
        "No Apifox OpenAPI source configured. Set APIFOX_OPENAPI_RAW_URL, "
        "or set APIFOX_PROJECT_ID and APIFOX_ACCESS_TOKEN."
    )


def _parse_document(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict):
        raise TypeError("OpenAPI document root must be an object.")
    return parsed


def _extract_openapi_from_response(response: requests.Response) -> dict[str, Any]:
    parsed = response.json()
    if isinstance(parsed, dict) and ("openapi" in parsed or "swagger" in parsed):
        return parsed
    for key in ("data", "document", "spec", "openapi"):
        value = parsed.get(key) if isinstance(parsed, dict) else None
        if isinstance(value, dict) and ("openapi" in value or "swagger" in value):
            return value
        if isinstance(value, str):
            return _parse_document(value)
    raise ValueError(f"Cannot locate OpenAPI document in Apifox response keys: {list(parsed) if isinstance(parsed, dict) else type(parsed)}")


def read_json(path: str | Path) -> dict[str, Any] | None:
    resolved = project_path(path)
    if not resolved.exists():
        return None
    with resolved.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
