"""
ASR 语音识别接口测试。

覆盖接口：
- POST /asr/submit 异步提交 ASR 识别任务

测试数据来源：data/test_data/test_asr.yaml 中 asr.submit_cases。
"""

from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from typing import Iterator

import pytest

from openapi_automation.clients.openapi_client import build_files
from openapi_automation.core.assertions import response_json

from .helpers import assert_case, case_ids, case_params, rendered


def pytest_generate_tests(metafunc):
    """动态参数化：根据 asr 模块数据自动生成测试用例。"""
    from openapi_automation.core.config import load_test_data

    data = load_test_data()
    mapping = {
        "asr_case": data["asr"]["submit_cases"],
    }
    for name, cases in mapping.items():
        if name in metafunc.fixturenames:
            metafunc.parametrize(name, case_params(cases), ids=case_ids(cases))


@pytest.mark.live
def test_asr_submit(api_client, test_data, common, asr_case, runtime_context):
    """[Live 测试] 以 multipart/form-data 提交 ASR 异步识别任务。"""
    case = rendered(asr_case, common)
    with _asr_files(test_data, case) as files:
        response = api_client.asr_submit(files=files, data=case.get("form"), auth=case.get("auth", "default"))
    payload = assert_case(response, case)
    if case.get("category") in {"positive", "boundary", "equivalence", "scenario"} and payload:
        task_id = (payload.get("data") or {}).get("task_id") or payload.get("task_id")
        if task_id:
            runtime_context["asr_task_id"] = str(task_id)


def submit_asr_and_get_task_id(api_client, test_data: dict) -> str:
    """提交 URL 音频的 ASR 任务，供统一任务状态查询单独运行时复用。"""
    response = api_client.asr_submit(data={"audio_url": test_data["common"]["asr_audio_url"]})
    payload = response_json(response)
    task_id = (payload.get("data") or {}).get("task_id") or payload.get("task_id")
    assert task_id, f"ASR 提交接口未返回 task_id，无法用于统一状态查询。响应: {payload!r}"
    return str(task_id)


@contextmanager
def _asr_files(test_data: dict, case: dict) -> Iterator[dict | None]:
    """为 RAW 参数边界用例生成临时 16-bit PCM 数据，其余用例加载配置的本地文件。"""
    if case.get("raw_pcm"):
        # 两秒 192 kHz 单声道 16-bit PCM：覆盖最大采样率仍小于 1 MB，避免引入二进制测试文件。
        raw_audio = BytesIO(b"\x00\x00" * (192_000 * 2))
        try:
            yield {"audio": ("asr_boundary.raw", raw_audio, "application/octet-stream")}
        finally:
            raw_audio.close()
        return

    bundle = build_files(test_data, case.get("files", {}))
    with bundle as files:
        yield files or None
