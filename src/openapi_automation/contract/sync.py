from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .differ import diff_snapshots
from .loader import fetch_openapi_document, load_openapi_source_config, read_json, write_json
from .normalizer import normalize_openapi
from .reporter import write_markdown_report


def sync_openapi(source_name: str | None = None, *, update_snapshot: bool = False) -> dict[str, Any]:
    source = load_openapi_source_config(source_name)
    document = fetch_openapi_document(source)
    operations = normalize_openapi(document)
    latest = {
        "source": source["name"],
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "openapi_version": document.get("openapi") or document.get("swagger"),
        "operation_count": len(operations),
        "operations": operations,
    }

    if source.get("raw_path"):
        write_json(source["raw_path"], document)
    previous = read_json(source["snapshot_path"])
    diff = diff_snapshots(previous, latest)
    write_json(source["latest_path"], latest)
    write_json(source["diff_json_path"], diff)
    write_markdown_report(source["diff_markdown_path"], source, diff)

    if update_snapshot:
        write_json(source["snapshot_path"], latest)

    return {"source": source, "latest": latest, "diff": diff}
