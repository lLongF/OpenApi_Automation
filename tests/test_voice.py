"""
声音克隆与推理接口测试。

覆盖接口：
- POST /open/voice/zeroshot/clone  Zero-shot 声音克隆
- POST /open/voice/zeroshot/infer  Zero-shot 声音推理（合成）

测试数据来源：data/test_data/*.yaml 中 voice_clone / voice_infer 模块
"""

from __future__ import annotations

import pytest

from openapi_automation.clients.openapi_client import build_files

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 test_data/*.yaml 中 voice_clone / voice_infer 模块数据自动生成测试用例。"""
    if "voice_clone_case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        data = load_test_data()
        cases = data["voice_clone"]["cases"]
        metafunc.parametrize("voice_clone_case", case_params(cases), ids=case_ids(cases))
    if "voice_infer_case" in metafunc.fixturenames:
        from openapi_automation.core.config import load_test_data

        data = load_test_data()
        cases = data["voice_infer"]["cases"]
        metafunc.parametrize("voice_infer_case", case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_voice_clone(api_client, test_data, common, voice_clone_case, runtime_context):
    """[Live 测试] Zero-shot 声音克隆接口。

    接口：POST /open/voice/zeroshot/clone
    请求方式：multipart/form-data（音频样本 + 表单参数如 timbre_name / language）
    认证：api_key 请求头
    功能：上传参考音频，注册一个新的音色，返回 timbre_id
    """
    case = rendered(voice_clone_case, common)
    mapping = {"audio": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.clone_voice(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") == "positive" and payload:
        request_id = payload.get("request_id") or (payload.get("data") or {}).get("request_id")
        if request_id:
            runtime_context["speaker_id"] = str(request_id)


@pytest.mark.live
def test_voice_infer(api_client, test_data, common, voice_infer_case, runtime_context):
    """[Live 测试] Zero-shot 声音推理（合成）接口。

    接口：POST /open/voice/zeroshot/infer
    请求方式：multipart/form-data（参考音频 + 表单参数如 timbre_id / text / language）
    认证：api_key 请求头
    功能：根据已注册的 timbre_id 和文本合成语音
    """
    case = rendered(voice_infer_case, common)
    case = resolve_auto_speaker_id(case, api_client, test_data, runtime_context)
    mapping = {"audio": case["file_key"]} if case.get("file_key") else {}
    bundle = build_files(test_data, mapping)
    with bundle as files:
        response = api_client.infer_voice(files=files or None, data=case.get("form"), auth=case.get("auth", "default"))
    assert_case(response, case)


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