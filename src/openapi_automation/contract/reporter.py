from __future__ import annotations

from pathlib import Path
from typing import Any

from openapi_automation.core.config import project_path


def write_markdown_report(path: str | Path, source: dict[str, Any], diff: dict[str, Any]) -> None:
    resolved = project_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# OpenAPI Diff Report - {source['name']}",
        "",
        f"- Provider: `{source.get('provider', 'unknown')}`",
        f"- Description: {source.get('description', '')}",
        f"- Total changes: `{diff['summary']['total_changes']}`",
        f"- Breaking changes: `{diff['summary']['breaking_changes']}`",
        f"- Added operations: `{diff['summary']['added']}`",
        f"- Removed operations: `{diff['summary']['removed']}`",
        "",
        "## Changes",
        "",
    ]
    if not diff["changes"]:
        lines.append("No contract changes detected.")
    for item in diff["changes"]:
        operation = item.get("operation", "")
        parameter = f" `{item['parameter']}`" if "parameter" in item else ""
        lines.append(f"- `{item['type']}` `{operation}`{parameter}")
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")
