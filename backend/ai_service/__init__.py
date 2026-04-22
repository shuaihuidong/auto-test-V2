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


def get_llm_gateway() -> LLMGateway:
    """
    获取 LLM Gateway 单例

    首次调用时从 Django settings 初始化，后续复用同一实例。
    """
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = LLMGateway.from_settings()
    return _gateway_instance


def is_ai_configured() -> bool:
    """检查 AI 服务是否已配置（API Key 非空）"""
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
