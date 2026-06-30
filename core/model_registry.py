"""
模型注册表 — 集中管理 DeepSeek 和阿里云通义千问两个 LLM 提供商

只支持两个模型提供商：DeepSeek 和阿里云通义千问（千问/通义千问）。
"""
from dataclasses import dataclass
from typing import Optional
import config


@dataclass
class ModelProvider:
    """单个模型提供商的配置"""
    key: str            # 唯一标识: "deepseek" / "aliyun"
    label: str          # 前端展示名称
    model: str          # 默认模型 ID
    api_key: str        # API Key
    base_url: str       # API Base URL
    available: bool     # 是否可用（key 非空）


# 已注册的提供商
_providers: dict[str, ModelProvider] = {}


def init_providers():
    """根据配置初始化所有提供商"""
    global _providers

    _providers = {
        "deepseek": ModelProvider(
            key="deepseek",
            label="DeepSeek",
            # model="deepseek-chat",
            model="deepseek-reasoner",
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            available=bool(config.DEEPSEEK_API_KEY),
        ),
        "aliyun": ModelProvider(
            key="aliyun",
            label="阿里云通义千问",
            model="qwen3.6-flash",
            api_key=config.ALIYUN_API_KEY,
            base_url=config.ALIYUN_BASE_URL,
            available=bool(config.ALIYUN_API_KEY),
        ),
    }


def get_provider(key: str) -> Optional[ModelProvider]:
    """获取指定提供商配置"""
    return _providers.get(key)


def get_default_provider() -> ModelProvider:
    """
    返回默认提供商（优先 DeepSeek，然后阿里云）
    若都不可用，返回 DeepSeek（后续会在 Agent 层提示用户配置 Key）
    """
    for key in ("deepseek", "aliyun"):
        p = _providers.get(key)
        if p and p.available:
            return p

    return _providers.get("deepseek", ModelProvider(
        key="deepseek", label="DeepSeek", model="deepseek-chat",
        api_key="", base_url="https://api.deepseek.com/v1", available=False,
    ))


def list_available_providers() -> list[dict]:
    """返回可用提供商列表（供前端展示）"""
    return [
        {
            "key": p.key,
            "label": p.label,
            "model": p.model,
            "available": p.available,
        }
        for p in _providers.values()
    ]


# 启动时自动初始化
init_providers()
