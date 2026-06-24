"""
测试辅助工具模块。

提供参数化用例生成、模板渲染、响应断言、文件打包等公共能力。
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import assert_expected_response
from openapi_automation.core.render import render_value

try:
    import allure
except ImportError:  # pragma: no cover
    allure = None

ATTACHMENT_LIMIT = 50_000
SENSITIVE_HEADERS = {"api_key", "x-admin-token", "authorization"}


def case_ids(cases: list[dict[str, Any]]) -> list[str]:
    """从测试用例列表中提取 id 字段，作为 pytest 参数化 ids。"""
    return [case["id"] for case in cases]


def case_params(cases: list[dict[str, Any]]) -> list[Any]:
    """将测试用例列表转换为 pytest.param 列表，并根据 category 字段附加标记（smoke/negative/boundary）。"""
    return [pytest.param(case, marks=_marks_for_case(case)) for case in cases]


def rendered(case: dict[str, Any], common: dict[str, Any]) -> dict[str, Any]:
    """使用 common 变量渲染用例模板（支持变量替换和 text_repeat 扩展）。"""
    return _expand_generated_text(render_value(case, common))


def assert_case(response, case: dict[str, Any]):
    """根据用例定义中的 expected 字段校验 API 响应（状态码、code、必填字段等）。"""
    attach_allure_case(case)
    attach_allure_exchange(response, case)
    try:
        return assert_expected_response(response, case["expected"])
    except AssertionError as exc:
        attach_allure_text("Failure reason", str(exc) or repr(exc))
        raise


def single_file_bundle(test_data: dict, case: dict[str, Any], field_name: str = "file"):
    """根据用例的 file_key 构建单文件 multipart 上传 bundle。"""
    if not case.get("file_key"):
        return build_files(test_data, {})
    return build_files(test_data, {field_name: case["file_key"]})



def _expand_generated_text(value: Any) -> Any:
    """递归处理 text_repeat 字段：将 text 字段内容重复扩展到指定长度（用于生成长文本边界值用例）。"""
    if isinstance(value, dict):
        output = {key: _expand_generated_text(item) for key, item in value.items() if key != "text_repeat"}
        repeat = value.get("text_repeat")
        if repeat is not None and "text" in output:
            seed = str(output["text"]) or "x"
            output["text"] = (seed * ((int(repeat) // len(seed)) + 1))[: int(repeat)]
        return output
    if isinstance(value, list):
        return [_expand_generated_text(item) for item in value]
    return value


def _marks_for_case(case: dict[str, Any]) -> list[Any]:
    """根据用例的 category 字段返回对应的 pytest 标记。"""
    category = case.get("category")
    marks = []
    if category == "positive":
        marks.append(pytest.mark.smoke)
    elif category == "negative":
        marks.append(pytest.mark.negative)
    elif category == "exception":
        marks.append(pytest.mark.exception)
    elif category == "boundary":
        marks.append(pytest.mark.boundary)
    return marks


def attach_allure_case(case: dict[str, Any]) -> None:
    if allure is None:
        return
    case_id = case.get("id", "")
    title = case.get("title") or case_id
    allure.dynamic.title(str(title))
    if case_id:
        allure.dynamic.story(str(case_id))
    if case.get("category"):
        allure.dynamic.label("category", str(case["category"]))
    if title:
        allure.dynamic.description(str(title))


def attach_allure_exchange(response, case: dict[str, Any]) -> None:
    if allure is None:
        return
    attach_allure_json("Case input", _case_input(case))
    attach_allure_json("Expected result", case.get("expected", {}))
    attach_allure_json("HTTP request", _request_info(response))
    attach_allure_json("HTTP response", _response_info(response))


def attach_allure_json(name: str, value: Any) -> None:
    if allure is None:
        return
    attach_allure_text(name, json.dumps(value, ensure_ascii=False, indent=2, default=str), "json")


def attach_allure_text(name: str, value: str, extension: str = "txt") -> None:
    if allure is None:
        return
    attachment_type = allure.attachment_type.JSON if extension == "json" else allure.attachment_type.TEXT
    allure.attach(_truncate(value), name=name, attachment_type=attachment_type, extension=extension)


def _case_input(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case.get("id"),
        "title": case.get("title"),
        "category": case.get("category"),
        "file_key": case.get("file_key"),
        "form": case.get("form"),
        "json": case.get("json"),
        "params": case.get("params"),
        "auth": case.get("auth", "default"),
    }


def _request_info(response) -> dict[str, Any]:
    request = getattr(response, "request", None)
    if request is None:
        return {}
    return {
        "method": getattr(request, "method", None),
        "url": getattr(request, "url", None),
        "headers": _sanitize_headers(dict(getattr(request, "headers", {}) or {})),
        "body": _safe_body(getattr(request, "body", None)),
    }


def _response_info(response) -> dict[str, Any]:
    text = getattr(response, "text", "")
    return {
        "status_code": getattr(response, "status_code", None),
        "headers": dict(getattr(response, "headers", {}) or {}),
        "body": _maybe_json(text),
    }


def _sanitize_headers(headers: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, value in headers.items():
        sanitized[key] = "***" if key.lower() in SENSITIVE_HEADERS else value
    return sanitized


def _safe_body(body: Any) -> Any:
    if body is None:
        return None
    if isinstance(body, bytes):
        return _truncate(body.decode("utf-8", errors="replace"))
    return _truncate(str(body))


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return _truncate(text or "")


def _truncate(value: str, limit: int = ATTACHMENT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    omitted = len(value) - limit
    return f"{value[:limit]}\n... <truncated {omitted} chars>"
