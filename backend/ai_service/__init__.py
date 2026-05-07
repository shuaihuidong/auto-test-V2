"""
AI Service 模块 - LLM Gateway

对外暴露两个入口：
1. get_llm_gateway() → LLMGateway 单例（推荐）
2. LLMResponse 数据类

使用示例:
    from ai_service import get_llm_gateway

    gateway = get_llm_gateway()
    response = await gateway.call("你好", system_prompt="你是测试助手")
    print(response.content, response.token_usage)

    # 强制 JSON 输出
    response = await gateway.call_json("生成测试步骤", system_prompt="...")
    data = response.raw_response["parsed_json"]
"""

from .client import LLMGateway
from .providers import LLMResponse
from .exceptions import AIServiceError, AIProviderError, AIRetryExhaustedError, AIResponseParseError

# 模块级单例
_gateway_instance: LLMGateway | None = None
_config_hash: str = ""


def get_llm_gateway() -> LLMGateway:
    """
    获取 LLM Gateway 单例

    每次调用时检查 DB config hash，hash 变化则重建 gateway。
    """
    global _gateway_instance, _config_hash

    try:
        from apps.settings.resolver import _compute_config_hash
        current_hash = _compute_config_hash()
    except Exception:
        current_hash = ""

    if _gateway_instance is None or current_hash != _config_hash:
        try:
            from apps.settings.resolver import get_ai_config
            config = get_ai_config()
            _gateway_instance = LLMGateway.from_config(config)
        except Exception:
            # fallback 到 Django settings
            _gateway_instance = LLMGateway.from_settings()

        _config_hash = current_hash

    return _gateway_instance


def is_ai_configured() -> bool:
    """检查 AI 服务是否已配置（优先检查 DB 配置）"""
    try:
        from apps.settings.resolver import get_ai_config
        config = get_ai_config()
    except Exception:
        from django.conf import settings
        config = getattr(settings, "AI_SERVICE", {})

    primary = config.get("PRIMARY_PROVIDER", "openai")
    key_mapping = {
        "openai": "OPENAI_API_KEY",
        "qwen": "QWEN_API_KEY",
    }
    key_name = key_mapping.get(primary, "OPENAI_API_KEY")
    api_key = config.get(key_name, "")
    return bool(api_key and api_key.strip())
