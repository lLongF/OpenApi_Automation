from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openapi_automation.contract.normalizer import normalize_openapi
from openapi_automation.contract.sync import sync_openapi


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
DEFAULT_RAW_PATH = ROOT / "data" / "openapi" / "apifox_raw.json"
DEFAULT_DIFF_PATH = ROOT / "reports" / "openapi" / "apifox_diff.json"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "generated" / "openapi_new_test_data.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate draft pytest data templates from OpenAPI operations.")
    parser.add_argument("--source", default=None, help="OpenAPI source name in config/openapi_sources.yaml.")
    parser.add_argument("--sync", action="store_true", help="Sync OpenAPI from Apifox before generating templates.")
    parser.add_argument("--all", action="store_true", help="Generate templates for all operations instead of only added operations.")
    parser.add_argument("--raw", default=str(DEFAULT_RAW_PATH), help="Raw OpenAPI JSON/YAML path.")
    parser.add_argument("--diff", default=str(DEFAULT_DIFF_PATH), help="OpenAPI diff JSON path used to detect added operations.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output YAML template path.")
    parser.add_argument(
        "--format",
        choices=("test-data", "case-templates"),
        default="test-data",
        help="Output format. test-data follows data/test_data/*.yaml style.",
    )
    args = parser.parse_args()

    if args.sync:
        sync_openapi(args.source, update_snapshot=False)

    raw_path = _project_path(args.raw)
    document = _read_document(raw_path)
    operations = normalize_openapi(document)

    target_keys = sorted(operations)
    if not args.all:
        added = _read_added_operations(_project_path(args.diff))
        if added:
            target_keys = [key for key in target_keys if key in added]

    templates = _build_templates(document, operations, target_keys)
    output_payload = _to_test_data_format(templates) if args.format == "test-data" else templates
    output_path = _project_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        yaml.safe_dump(output_payload, file, allow_unicode=True, sort_keys=False, width=120)

    print(f"Generated {len(templates['case_templates'])} operation template(s): {output_path}")
    if not args.all and not templates["case_templates"]:
        print("No added operations found in diff. Use --all to generate templates for all operations.")
    return 0


def _project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _read_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"OpenAPI raw document not found: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict):
        raise TypeError(f"OpenAPI document root must be an object: {path}")
    return parsed


def _read_added_operations(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as file:
        diff = json.load(file)
    return {item["operation"] for item in diff.get("changes", []) if item.get("type") == "operation_added" and item.get("operation")}


def _build_templates(document: dict[str, Any], operations: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "data/openapi/apifox_raw.json",
        "note": "Generated draft only. Fill real request values, file_key, expected code, and assertions before merging into data/test_data/*.yaml.",
        "case_templates": [_build_operation_template(document, operations[key], index + 1) for index, key in enumerate(keys)],
    }


def _to_test_data_format(templates: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "_meta": {
            "generated_at": templates["generated_at"],
            "source": templates["source"],
            "note": templates["note"],
        }
    }
    for template in templates["case_templates"]:
        name = template["name"]
        output[name] = {
            "endpoint": template["endpoint"],
            "cases": template["cases"],
        }
    return output


def _build_operation_template(document: dict[str, Any], operation: dict[str, Any], index: int) -> dict[str, Any]:
    method = operation["method"]
    path = operation["path"]
    operation_item = _find_operation_item(document, method, path)
    body = _request_body_template(document, operation_item)
    parameters = _parameter_template(operation.get("parameters", []))
    prefix = _case_id_prefix(path)

    positive_case = {
        "id": f"{prefix}_POS_001",
        "title": f"{operation.get('summary') or path}-正向成功",
        "category": "positive",
        "expected": _expected_template(operation),
    }
    if parameters:
        positive_case["params"] = parameters
    positive_case.update(body)

    cases = [positive_case]
    cases.extend(_negative_cases(prefix, operation, parameters, body))

    return {
        "name": _template_name(path, method, index),
        "endpoint": {
            "method": method,
            "path": path,
            "summary": operation.get("summary"),
            "operation_id": operation.get("operation_id"),
            "response_codes": operation.get("response_codes", []),
        },
        "cases": cases,
    }


def _find_operation_item(document: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    path_item = document.get("paths", {}).get(path, {})
    if not isinstance(path_item, dict):
        return {}
    operation_item = path_item.get(method.lower(), {})
    return operation_item if isinstance(operation_item, dict) else {}


def _parameter_template(parameters: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter in parameters:
        if parameter.get("in") == "header":
            continue
        name = str(parameter.get("name", ""))
        if not name:
            continue
        values[name] = _sample_value(name, parameter.get("schema_type"))
    return values


def _request_body_template(document: dict[str, Any], operation_item: dict[str, Any]) -> dict[str, Any]:
    request_body = operation_item.get("requestBody") if isinstance(operation_item, dict) else None
    if not isinstance(request_body, dict):
        return {}

    content = request_body.get("content")
    if not isinstance(content, dict) or not content:
        return {}

    content_type = _preferred_content_type(content)
    media = content.get(content_type, {})
    schema = _resolve_ref(document, media.get("schema", {}) if isinstance(media, dict) else {})
    properties = _schema_properties(document, schema)
    required = set(schema.get("required") or []) if isinstance(schema, dict) else set()

    if content_type == "multipart/form-data":
        form: dict[str, Any] = {}
        file_field = None
        for name, prop in properties.items():
            prop = _resolve_ref(document, prop)
            if _is_file_schema(prop):
                file_field = name
                continue
            form[name] = _sample_value(name, prop.get("type") if isinstance(prop, dict) else None)
        output: dict[str, Any] = {
            "content_type": content_type,
            "form": form,
        }
        if file_field:
            output["file_field"] = file_field
            output["file_key"] = "replace-with-file-key"
        if required:
            output["required_body_fields"] = sorted(required)
        return output

    payload = {name: _sample_value(name, _resolve_ref(document, prop).get("type")) for name, prop in properties.items()}
    output = {"content_type": content_type, "json": payload}
    if required:
        output["required_body_fields"] = sorted(required)
    return output


def _preferred_content_type(content: dict[str, Any]) -> str:
    for content_type in ("application/json", "multipart/form-data"):
        if content_type in content:
            return content_type
    return next(iter(content))


def _resolve_ref(document: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    ref = value.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return value
    current: Any = document
    for part in ref[2:].split("/"):
        if not isinstance(current, dict):
            return {}
        current = current.get(part)
    return current if isinstance(current, dict) else {}


def _schema_properties(document: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    schema = _resolve_ref(document, schema)
    properties = schema.get("properties") if isinstance(schema, dict) else None
    return properties if isinstance(properties, dict) else {}


def _is_file_schema(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "string" and schema.get("format") in {"binary", "base64"}


def _sample_value(name: str, schema_type: str | None) -> Any:
    lowered = name.lower()
    if lowered.endswith("_id") or lowered in {"id", "taskid", "requestid", "projectid"}:
        return f"{{{{{name}}}}}"
    if "lang" in lowered:
        return "zh"
    if "text" in lowered or "body" in lowered:
        return "replace-with-text"
    if schema_type in {"integer", "number"}:
        return 1
    if schema_type == "boolean":
        return True
    if schema_type == "array":
        return []
    if schema_type == "object":
        return {}
    return f"replace-with-{name}"


def _expected_template(operation: dict[str, Any]) -> dict[str, Any]:
    success_codes = [code for code in operation.get("response_codes", []) if str(code).startswith("2")]
    http_status = int(success_codes[0]) if success_codes and str(success_codes[0]).isdigit() else 200
    return {
        "http_status": http_status,
        "code": 200,
        "required_fields": ["code"],
    }


def _negative_cases(prefix: str, operation: dict[str, Any], parameters: dict[str, Any], body: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    required_params = [item for item in operation.get("parameters", []) if item.get("required") and item.get("in") != "header"]
    if required_params:
        name = required_params[0]["name"]
        negative_params = dict(parameters)
        negative_params.pop(name, None)
        cases.append(
            {
                "id": f"{prefix}_NEG_001",
                "title": f"{operation.get('summary') or operation.get('path')}-缺少必填参数{name}",
                "category": "negative",
                "params": negative_params,
                "expected": {
                    "http_status_any": [200, 400, 422],
                    "code_any": [400, 422],
                    "message_contains_any": [name, "必填", "缺少", "不能为空"],
                },
            }
        )

    required_body_fields = body.get("required_body_fields")
    if required_body_fields:
        field = required_body_fields[0]
        negative = {key: value for key, value in body.items() if key != "required_body_fields"}
        if isinstance(negative.get("json"), dict):
            negative["json"] = dict(negative["json"])
            negative["json"].pop(field, None)
        if isinstance(negative.get("form"), dict):
            negative["form"] = dict(negative["form"])
            negative["form"].pop(field, None)
        if negative.get("file_field") == field:
            negative["file_key"] = None
        negative.update(
            {
                "id": f"{prefix}_NEG_{len(cases) + 1:03d}",
                "title": f"{operation.get('summary') or operation.get('path')}-缺少必填字段{field}",
                "category": "negative",
                "expected": {
                    "http_status_any": [200, 400, 422],
                    "code_any": [400, 422],
                    "message_contains_any": [field, "必填", "缺少", "不能为空"],
                },
            }
        )
        cases.append(negative)
    return cases


def _case_id_prefix(path: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", path) if part and part.lower() != "open"]
    initials = "".join(part[0].upper() for part in parts[:4])
    return initials or "API"


def _template_name(path: str, method: str, index: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path.strip("/")).strip("_").lower()
    return f"{slug or 'api'}_{method.lower()}_{index:03d}"


if __name__ == "__main__":
    raise SystemExit(main())
