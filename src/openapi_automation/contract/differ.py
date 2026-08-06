from __future__ import annotations

from typing import Any


BREAKING_CHANGE_TYPES = {
    "operation_removed",
    "required_parameter_added",
    "parameter_became_required",
    "parameter_type_changed",
    "request_body_became_required",
    "success_response_removed",
}


def diff_snapshots(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    old_ops = (old or {}).get("operations", {})
    new_ops = new.get("operations", {})

    changes: list[dict[str, Any]] = []
    for key in sorted(set(new_ops) - set(old_ops)):
        changes.append({"type": "operation_added", "operation": key, "new": new_ops[key]})
    for key in sorted(set(old_ops) - set(new_ops)):
        changes.append({"type": "operation_removed", "operation": key, "old": old_ops[key]})
    for key in sorted(set(old_ops) & set(new_ops)):
        changes.extend(_diff_operation(key, old_ops[key], new_ops[key]))

    breaking = [item for item in changes if item["type"] in BREAKING_CHANGE_TYPES]
    return {
        "summary": {
            "total_changes": len(changes),
            "breaking_changes": len(breaking),
            "added": sum(1 for item in changes if item["type"] == "operation_added"),
            "removed": sum(1 for item in changes if item["type"] == "operation_removed"),
            "changed": sum(1 for item in changes if item["type"] not in {"operation_added", "operation_removed"}),
        },
        "has_breaking_changes": bool(breaking),
        "changes": changes,
    }


def _diff_operation(key: str, old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    old_params = {f"{item['in']}:{item['name']}": item for item in old.get("parameters", [])}
    new_params = {f"{item['in']}:{item['name']}": item for item in new.get("parameters", [])}

    for param_key in sorted(set(new_params) - set(old_params)):
        change_type = "required_parameter_added" if new_params[param_key].get("required") else "optional_parameter_added"
        changes.append({"type": change_type, "operation": key, "parameter": param_key, "new": new_params[param_key]})
    for param_key in sorted(set(old_params) - set(new_params)):
        changes.append({"type": "parameter_removed", "operation": key, "parameter": param_key, "old": old_params[param_key]})
    for param_key in sorted(set(old_params) & set(new_params)):
        old_param = old_params[param_key]
        new_param = new_params[param_key]
        if old_param.get("schema_type") != new_param.get("schema_type"):
            changes.append(
                {
                    "type": "parameter_type_changed",
                    "operation": key,
                    "parameter": param_key,
                    "old": old_param.get("schema_type"),
                    "new": new_param.get("schema_type"),
                }
            )
        if not old_param.get("required") and new_param.get("required"):
            changes.append({"type": "parameter_became_required", "operation": key, "parameter": param_key})

    if not old.get("request_body_required") and new.get("request_body_required"):
        changes.append({"type": "request_body_became_required", "operation": key})

    old_success = _success_codes(old.get("response_codes", []))
    new_success = _success_codes(new.get("response_codes", []))
    if old_success and not new_success:
        changes.append({"type": "success_response_removed", "operation": key, "old": sorted(old_success)})
    elif old_success != new_success:
        changes.append({"type": "response_codes_changed", "operation": key, "old": sorted(old_success), "new": sorted(new_success)})

    if old.get("operation_id") != new.get("operation_id"):
        changes.append({"type": "operation_id_changed", "operation": key, "old": old.get("operation_id"), "new": new.get("operation_id")})
    return changes


def _success_codes(codes: list[str]) -> set[str]:
    return {str(code) for code in codes if str(code).startswith("2")}
