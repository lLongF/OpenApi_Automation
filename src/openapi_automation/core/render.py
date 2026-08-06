from __future__ import annotations

from typing import Any


def render_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        rendered = value
        for key, replacement in context.items():
            rendered = rendered.replace("{{" + key + "}}", str(replacement))
        return rendered
    if isinstance(value, dict):
        return {key: render_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [render_value(item, context) for item in value]
    return value
