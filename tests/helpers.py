"""
测试辅助工具模块。

提供参数化用例生成、模板渲染、响应断言、文件打包等公共能力。
"""

from __future__ import annotations

from typing import Any

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json
from openapi_automation.core.assertions import assert_expected_response
from openapi_automation.core.render import render_value


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
    return assert_expected_response(response, case["expected"])


def single_file_bundle(test_data: dict, case: dict[str, Any], field_name: str = "file"):
    """根据用例的 file_key 构建单文件 multipart 上传 bundle。"""
    if not case.get("file_key"):
        return build_files(test_data, {})
    return build_files(test_data, {field_name: case["file_key"]})


def clone_voice_and_get_speaker_id(api_client, test_data: dict) -> str:
    """调用语音克隆接口，返回后续语音合成所需 speaker_id。

    当前业务约定：语音克隆响应中的 request_id 即为 speaker_id。
    """
    bundle = build_files(test_data, {"audio": "valid_clone_audio"})
    with bundle as files:
        response = api_client.clone_voice(
            files=files,
            data={"body": '{"carry_back":"auto-speaker-id"}'},
        )
    payload = response_json(response)
    speaker_id = _first_present(payload, ("request_id", "data.request_id"))
    assert speaker_id, f"语音克隆接口未返回 request_id，无法作为 speaker_id 传递。响应: {payload!r}"
    return str(speaker_id)


def resolve_auto_speaker_id(
    case: dict[str, Any],
    api_client,
    test_data: dict,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把语音合成用例中的占位 speaker_id 替换成真实值。

    优先使用 test_voice_clone 正向用例缓存的 request_id；如果只单独跑 test_voice_infer，
    则自动补跑一次语音克隆。
    """
    form = case.get("form")
    if not isinstance(form, dict):
        return case
    speaker_id = form.get("speaker_id")
    if not speaker_id or not str(speaker_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_form = dict(form)
    context_speaker_id = (runtime_context or {}).get("speaker_id")
    resolved_form["speaker_id"] = context_speaker_id or clone_voice_and_get_speaker_id(api_client, test_data)
    resolved["form"] = resolved_form
    return resolved


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


def _first_present(payload: dict[str, Any], paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = payload
        missing = False
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                missing = True
                break
            current = current[part]
        if not missing and current not in (None, ""):
            return current
    return None


def _marks_for_case(case: dict[str, Any]) -> list[Any]:
    """根据用例的 category 字段返回对应的 pytest 标记。"""
    category = case.get("category")
    marks = []
    if category == "positive":
        marks.append(pytest.mark.smoke)
    elif category == "negative":
        marks.append(pytest.mark.negative)
    elif category == "boundary":
        marks.append(pytest.mark.boundary)
    return marks
