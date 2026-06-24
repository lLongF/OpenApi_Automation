"""
视频翻译（Video Translation）接口测试。

覆盖接口：
- POST /open/videots/translate          视频翻译提交
- POST /open/videots/retranslate        视频重新翻译
- POST /open/videots/back-translation   反向翻译
- GET  /open/videots/status             翻译任务状态查询

测试数据来源：data/test_data/*.yaml 中 videots 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 videots 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()["videots"]
    mapping = {
        "translate_case": data["translate_cases"],
        "retranslate_case": data["retranslate_cases"],
        "back_translation_case": data["back_translation_cases"],
        "status_case": data["status_cases"],
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
        task_id = (payload.get("data") or {}).get("task_id") or payload.get("task_id")
        if task_id:
            runtime_context["task_id"] = str(task_id)


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


@pytest.mark.live
def test_videots_status(api_client, test_data, common, status_case, runtime_context):
    """[Live 测试] 视频翻译任务状态查询接口。

    接口：GET /open/videots/status
    请求参数：task_id（查询参数）
    认证：api_key 请求头
    """
    case = rendered(status_case, common)
    case = resolve_auto_task_id(case, api_client, test_data, runtime_context)
    response = api_client.videots_status(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


def resolve_auto_task_id(
    case: dict[str, Any],
    api_client,
    test_data: dict,
    runtime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = case.get("params")
    if not isinstance(params, dict):
        return case
    task_id = params.get("task_id")
    if not task_id or not str(task_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_params = dict(params)
    context_task_id = (runtime_context or {}).get("task_id")
    resolved_params["task_id"] = context_task_id or submit_translation_and_get_task_id(api_client, test_data)
    resolved["params"] = resolved_params
    return resolved


def submit_translation_and_get_task_id(api_client, test_data: dict) -> str:
    bundle = build_files(test_data, {"file": "valid_subtitle"})
    with bundle as files:
        response = api_client.translate(
            files=files,
            data={"target_language": "en", "user_prompt": "auto-task-id", "mode": "direct"},
        )
    payload = response_json(response)
    task_id = _first_present(payload, ("data.task_id", "task_id"))
    assert task_id, f"Translation API did not return task_id. response={payload!r}"
    return str(task_id)