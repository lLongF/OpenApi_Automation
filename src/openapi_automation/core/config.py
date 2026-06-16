from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RetryConfig:
    total: int
    backoff_factor: float
    status_forcelist: tuple[int, ...]


@dataclass(frozen=True)
class TimeoutConfig:
    connect: float
    read: float

    @property
    def requests_tuple(self) -> tuple[float, float]:
        return self.connect, self.read


@dataclass(frozen=True)
class EnvConfig:
    name: str
    base_url: str
    api_key_env: str
    user_id_value: str | None
    user_id_env: str
    admin_token_value: str | None
    admin_token_env: str
    timeout: TimeoutConfig
    retry: RetryConfig

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)

    @property
    def user_id(self) -> str | None:
        return os.getenv(self.user_id_env) or self.user_id_value

    @property
    def admin_token(self) -> str | None:
        return os.getenv(self.admin_token_env) or self.admin_token_value


def load_yaml(path: str | Path) -> dict[str, Any]:
    resolved = PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
    with resolved.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    if not isinstance(loaded, dict):
        raise TypeError(f"YAML root must be a mapping: {resolved}")
    return loaded


def load_env_config(env_name: str | None = None) -> EnvConfig:
    raw = load_yaml("config/env.yaml")
    selected = env_name or os.getenv("TEST_ENV") or raw["default"]
    envs = raw["environments"]
    if selected not in envs:
        raise KeyError(f"Unknown TEST_ENV={selected!r}. Available: {', '.join(envs)}")
    item = envs[selected]
    timeout = TimeoutConfig(**item["timeout"])
    retry = RetryConfig(
        total=int(item["retry"]["total"]),
        backoff_factor=float(item["retry"]["backoff_factor"]),
        status_forcelist=tuple(item["retry"].get("status_forcelist", [])),
    )
    return EnvConfig(
        name=selected,
        base_url=item["base_url"].rstrip("/"),
        api_key_env=item["api_key_env"],
        user_id_value=str(item["user_id"]) if item.get("user_id") is not None else None,
        user_id_env=item["user_id_env"],
        admin_token_value=str(item["admin_token"]) if item.get("admin_token") is not None else None,
        admin_token_env=item["admin_token_env"],
        timeout=timeout,
        retry=retry,
    )


def load_test_data() -> dict[str, Any]:
    return load_yaml("data/test_data.yaml")


def project_path(path: str | Path) -> Path:
    return PROJECT_ROOT / path if not Path(path).is_absolute() else Path(path)
