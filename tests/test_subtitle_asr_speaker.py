"""
字幕擦除与 ASR 语音识别接口测试。

覆盖接口：
- POST /open/subtitle/erase        字幕擦除提交
- GET  /open/subtitle/erase/result 字幕擦除结果查询
- POST /open/asr                   ASR 语音识别（REST 模式）

测试数据来源：data/test_data/*.yaml 中 subtitle_erase / asr 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 subtitle_erase / asr 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "erase_submit_case": data["subtitle_erase"]["submit_cases"],
        "erase_result_case": data["subtitle_erase"]["result_cases"],
        "asr_case": data["asr"]["rest_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_subtitle_erase_submit(api_client, test_data, common, erase_submit_case, runtime_context):
    """[Live 测试] 字幕擦除任务提交接口。

    接口：POST /open/subtitle/erase
    请求方式：multipart/form-data（视频文件 + 表单参数）
    认证：api_key 请求头
    正向用例成功后缓存 project_id，供字幕擦除结果查询接口使用。
    """
    case = rendered(erase_submit_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.erase_subtitle(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        project_id = (payload.get("data") or {}).get("project_id") or payload.get("project_id")
        if project_id:
            runtime_context["project_id"] = str(project_id)


@pytest.mark.live
def test_subtitle_erase_result(api_client, common, erase_result_case,runtime_context,test_data):
    """[Live 测试] 字幕擦除结果查询接口。

    接口：GET /open/subtitle/erase/result
    请求参数：project_id（查询参数）
    认证：api_key 请求头
    """
    case = rendered(erase_result_case, common)
    case = resolve_auto_project_id(case, api_client, test_data, runtime_context)
    response = api_client.erase_result(params=case.get("params", {}), auth=case.get("auth", "default"))
    assert_case(response, case)


@pytest.mark.live
def test_asr_rest(api_client, test_data, common, asr_case):
    """[Live 测试] ASR 语音识别接口（REST 模式）。

    接口：POST /open/asr
    请求方式：multipart/form-data（音频文件 + 表单参数，如 language）
    认证：api_key 请求头
    """
    case = rendered(asr_case, common)
    mapping = {"file": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.asr_rest(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)



def resolve_auto_project_id(case, api_client, test_data, runtime_context):
    params = case.get("params")
    if not isinstance(params, dict):
        return case

    project_id = params.get("project_id")
    if not project_id or not str(project_id).startswith("replace-with-valid"):
        return case

    resolved = dict(case)
    resolved_params = dict(params)

    context_project_id = runtime_context.get("project_id")
    resolved_params["project_id"] = context_project_id or submit_subtitle_erase_and_get_project_id(api_client, test_data)

    resolved["params"] = resolved_params
    return resolved



def submit_subtitle_erase_and_get_project_id(api_client, test_data):
    bundle = build_files(test_data, {"file": "valid_video"})
    with bundle as files:
        response = api_client.erase_subtitle(
            files=files,
            data={
                "name": "api-auto-erase",
                "language_code": "zh",
                "subtitle_mode": 0,
                "do_not_encrypt_link": "true",
            },
        )

    payload = response_json(response)
    project_id = (payload.get("data") or {}).get("project_id") or payload.get("project_id")

    assert project_id, f"字幕擦除提交接口未返回 project_id，无法用于结果查询。响应: {payload!r}"
    return str(project_id)
