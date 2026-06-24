"""
OpenAPI 契约测试（Contract & Diff Tests）。

验证：
1. OpenAPI 文档规范化解析的正确性
2. 接口变更差异检测的准确性（Breaking Change 识别）
3. 当前 Apifox 上导出的 OpenAPI 文档与基线快照无破坏性变更
"""

from __future__ import annotations

import pytest

from openapi_automation.contract.differ import diff_snapshots
from openapi_automation.contract.normalizer import normalize_openapi


@pytest.mark.contract
@pytest.mark.openapi
def test_openapi_normalizer_extracts_operations():
    """[单元测试-契约] 验证 OpenAPI 规范化工具能正确从文档中提取接口元数据（operation_id / request_body_required / response_codes）。

    被验证接口：POST /open/asr（ASR REST 语音识别）
    """
    document = {
        "openapi": "3.0.3",
        "paths": {
            "/open/asr": {
                "post": {
                    "operationId": "asrRest",
                    "summary": "ASR REST",
                    "tags": ["ASR"],
                    "parameters": [{"name": "traceId", "in": "header", "required": False, "schema": {"type": "string"}}],
                    "requestBody": {"required": True},
                    "responses": {"200": {"description": "success"}, "400": {"description": "bad request"}},
                }
            }
        },
    }

    snapshot = normalize_openapi(document)
    operation = snapshot["POST /open/asr"]
    assert operation["operation_id"] == "asrRest"
    assert operation["request_body_required"] is True
    assert operation["response_codes"] == ["200", "400"]


@pytest.mark.contract
@pytest.mark.openapi
def test_openapi_diff_detects_breaking_required_parameter_added():
    """[单元测试-契约] 验证差异检测工具能正确识别「参数从可选变为必填」的破坏性变更。

    模拟接口：GET /open/videots/status（视频翻译状态查询）
    - task_id 参数从 required=false 变为 required=true -> 检测为 parameter_became_required
    """
    old = {
        "operations": {
            "GET /open/videots/status": {
                "parameters": [{"name": "task_id", "in": "query", "required": False, "schema_type": "string"}],
                "request_body_required": False,
                "response_codes": ["200"],
            }
        }
    }
    new = {
        "operations": {
            "GET /open/videots/status": {
                "parameters": [{"name": "task_id", "in": "query", "required": True, "schema_type": "string"}],
                "request_body_required": False,
                "response_codes": ["200"],
            }
        }
    }

    diff = diff_snapshots(old, new)
    assert diff["has_breaking_changes"] is True
    assert any(item["type"] == "parameter_became_required" for item in diff["changes"])


@pytest.mark.openapi
def test_apifox_openapi_has_no_breaking_changes():
    """[Live 测试-契约] 从 Apifox 实时拉取 OpenAPI 文档，与本地快照对比，确保无破坏性变更。

    依赖：
        --live 参数 + 环境变量 APIFOX_PROJECT_ID / APIFOX_ACCESS_TOKEN
    接口来源：config/openapi_sources.yaml 中配置的 OpenAPI source
    """
    from openapi_automation.contract.sync import sync_openapi

    result = sync_openapi(update_snapshot=False)
    assert not result["diff"]["has_breaking_changes"], result["diff"]
