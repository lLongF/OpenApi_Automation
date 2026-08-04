"""
视频翻译（Video Translation）接口测试。

覆盖接口：
- POST /open/videots/translate          视频翻译提交
- POST /open/videots/retranslate        视频重新翻译
- POST /open/videots/back-translation   反向翻译

测试数据来源：data/test_data/*.yaml 中 videots 模块
"""

from __future__ import annotations

from typing import Any

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered

def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 videots 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()["videots"]
    mapping = {
        "translate_case": data["translate_cases"],
        "retranslate_case": data["retranslate_cases"],
        "back_translation_case": data["back_translation_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_translate(api_client, test_data, common, translate_case, runtime_context):
    """[Live 测试] 视频翻译提交接口。

    接口：POST /open/videots/translate
    请求方式：multipart/form-data（视频文件 + 表单参数如 src_lang / target_lang）
    认证：api_key 请求头
    """
    case = rendered(translate_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.translate(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        data = payload.get("data") or {}
        task_id = data.get("task_id") or data.get("taskId") or payload.get("task_id") or payload.get("taskId")
        if task_id:
            runtime_context["task_id"] = str(task_id)
            runtime_context["subtitle_translation_task_id"] = str(task_id)


@pytest.mark.live
def test_retranslate(api_client, test_data, common, retranslate_case):
    """[Live 测试] 视频重新翻译接口。

    接口：POST /open/videots/retranslate
    请求方式：multipart/form-data（视频文件 + SRT 字幕文件 + 表单参数）
    认证：api_key 请求头
    """
    case = rendered(retranslate_case, common)
    bundle = build_files(test_data, case.get("files", {}))
    with bundle as files:
        response = api_client.retranslate(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_back_translation(api_client, test_data, common, back_translation_case):
    """[Live 测试] 反向翻译接口（将翻译结果再译回源语言以评估翻译质量）。

    接口：POST /open/videots/back-translation
    请求方式：multipart/form-data（视频文件 + 表单参数）
    认证：api_key 请求头
    """
    case = rendered(back_translation_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.back_translate(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)
def submit_translation_and_get_task_id(api_client, test_data: dict) -> str:
    """提交一次任务，返回统一任务状态查询所需 task_id。"""
    bundle = build_files(test_data, {"file": "valid_subtitle"})
    with bundle as files:
        response = api_client.translate(
            files=files,
            data={"target_language": "en", "user_prompt": "auto-task-id", "mode": "direct"},
        )
    payload = response_json(response)
    task_id = _first_present(payload, ("data.task_id", "task_id"))
    assert task_id, f"字幕翻译提交接口未返回 task_id，无法用于统一状态查询。响应: {payload!r}"
    return str(task_id)


def _first_present(payload: dict, paths: tuple[str, ...]):
    for path in paths:
        current = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current not in (None, ""):
            return current
    return None
