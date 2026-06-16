"""
Pytest 全局配置与共享 fixtures 模块。

提供：
- 命令行参数 --live / --env
- Session 级别的环境配置、测试数据、API Key、API 客户端等 fixtures
- 对未启用 --live 时自动跳过标记了 @pytest.mark.live 的用例
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openapi_automation.clients.openapi_client import ShanhaiOpenApiClient
from openapi_automation.core.config import load_env_config, load_test_data
from openapi_automation.core.http_client import HttpClient


def pytest_addoption(parser):
    """注册自定义命令行参数。

    参数：
        --live: 是否执行需要真实 API 调用的测试用例（默认 False，跳过 live 用例）
        --env:  指定配置文件 config/env.yaml 中的环境名（如 dev / prod）
    """
    parser.addoption("--live", action="store_true", default=False, help="Run tests against real Shanhai OpenAPI.")
    parser.addoption("--env", action="store", default=None, help="Environment name in config/env.yaml.")


def pytest_collection_modifyitems(config, items):
    """在用例收集后，若未传递 --live，则自动跳过所有标记了 @pytest.mark.live 的用例。"""
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(reason="live API test skipped; run with --live and SHANHAI_USER_ID to enable")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def env_config(pytestconfig):
    """[Fixture] 从 config/env.yaml 加载指定环境的环境配置（Environments Config）。"""
    return load_env_config(pytestconfig.getoption("--env"))


@pytest.fixture(scope="session")
def test_data():
    """[Fixture] 从 data/test_data.yaml 加载所有测试数据定义。"""
    return load_test_data()


@pytest.fixture(scope="session")
def common(test_data):
    """[Fixture] 从测试数据中提取 common 通用变量块（如语言、音色 id 等）。"""
    return test_data["common"]


@pytest.fixture(scope="session")
def runtime_context():
    """[Fixture] 运行期上下文，用于在同一轮测试内传递上游接口返回值。"""
    return {}


@pytest.fixture(scope="session")
def api_key(env_config):
    """[Fixture] 通过管理接口创建 API Key（仅 --live 时生效）。

    调用接口：
        POST /admin/api-key/create
        请求头: X-Admin-Token = env_config.admin_token
        请求体: {"user_id": env_config.user_id}

    前置条件：config/env.yaml 中配置 user_id，或设置环境变量 SHANHAI_USER_ID。
    创建成功后会将 api_key 写入环境变量 SHANHAI_API_KEY。
    """
    user_id = env_config.user_id
    if not user_id:
        pytest.skip(
            f"user_id is required. Set user_id in config/env.yaml or export {env_config.user_id_env}. "
            "It is used to create api_key before live tests."
        )

    bootstrap_client = ShanhaiOpenApiClient(HttpClient(env_config, api_key=None))
    response = bootstrap_client.create_api_key(user_id=user_id, admin_token=env_config.admin_token)
    try:
        payload = response.json()
    except ValueError as exc:
        pytest.fail(f"/admin/api-key/create did not return JSON. status={response.status_code}, body={response.text[:300]!r}")
        raise exc

    key = (payload.get("data") or {}).get("api_key")
    if not key:
        pytest.fail(f"/admin/api-key/create did not return data.api_key. status={response.status_code}, body={payload!r}")
    os.environ[env_config.api_key_env] = key
    return key


@pytest.fixture()
def api_client(env_config, api_key):
    """[Fixture] 创建山海 OpenAPI 客户端实例，所有 live 测试用例使用该客户端调用接口。

    认证方式：通过请求头 api_key 携带 API Key。
    """
    return ShanhaiOpenApiClient(HttpClient(env_config, api_key=api_key))
