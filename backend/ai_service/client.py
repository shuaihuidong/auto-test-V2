"""
LLM Gateway 客户端
统一封装大模型调用，支持：
- 动态切换 Provider
- 自动重试（指数退避）
- 主备降级
- Token 消耗追踪
"""

import asyncio
import json
import re
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from .exceptions import (
    AIProviderError,
    AIRetryExhaustedError,
    AIServiceError,
)
from .providers import (
    PROVIDER_REGISTRY,
    BaseLLMProvider,
    LLMResponse,
)

# 可重试的 HTTP 状态码（网络超时、限流、服务端错误）
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable(error: Exception) -> bool:
    """判断异常是否可重试"""
    if isinstance(error, AIProviderError):
        if error.original_error:
            import httpx
            if isinstance(error.original_error, httpx.TimeoutException):
                return True
            if isinstance(error.original_error, httpx.HTTPStatusError):
                return error.original_error.response.status_code in _RETRYABLE_STATUS_CODES
        # 通用网络错误也重试
        if "网络请求失败" in str(error) or "请求超时" in str(error):
            return True
    return False


class LLMGateway:
    """
    LLM Gateway 主类

    用法:
        gateway = LLMGateway.from_settings()
        response = await gateway.call("你好", system_prompt="你是测试助手")
        response = await gateway.call_json("生成测试步骤", system_prompt=...)
    """

    def __init__(
        self,
        primary_provider: BaseLLMProvider,
        fallback_provider: Optional[BaseLLMProvider] = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        self.primary = primary_provider
        self.fallback = fallback_provider
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay

    # ==================== 工厂方法 ====================

    @classmethod
    def from_settings(cls) -> "LLMGateway":
        """从 Django settings 创建 Gateway 实例"""
        from django.conf import settings

        config = getattr(settings, "AI_SERVICE", {})

        # 创建主 Provider
        primary_name = config.get("PRIMARY_PROVIDER", "openai")
        primary = cls._create_provider(primary_name, config)

        # 创建备用 Provider
        fallback_name = config.get("FALLBACK_PROVIDER", "")
        fallback = None
        if fallback_name and fallback_name != primary_name:
            try:
                fallback = cls._create_provider(fallback_name, config)
            except Exception as e:
                logger.warning(f"备用 Provider ({fallback_name}) 初始化失败: {e}")

        return cls(
            primary_provider=primary,
            fallback_provider=fallback,
            max_retries=config.get("MAX_RETRIES", 3),
            retry_base_delay=config.get("RETRY_BASE_DELAY", 1.0),
        )

    @classmethod
    def _create_provider(cls, name: str, config: Dict[str, Any]) -> BaseLLMProvider:
        """根据配置创建 Provider 实例"""
        provider_class = PROVIDER_REGISTRY.get(name)
        if not provider_class:
            raise ValueError(f"未知的 Provider: {name}，可选: {list(PROVIDER_REGISTRY.keys())}")

        if name == "openai":
            return provider_class(
                api_key=config.get("OPENAI_API_KEY", ""),
                model=config.get("OPENAI_MODEL", "gpt-4o"),
                api_base=config.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
                timeout=config.get("TIMEOUT", 60),
            )
        elif name == "qwen":
            return provider_class(
                api_key=config.get("QWEN_API_KEY", ""),
                model=config.get("QWEN_MODEL", "qwen-max"),
                timeout=config.get("TIMEOUT", 60),
            )
        else:
            raise ValueError(f"Provider {name} 未配置")

    # ==================== 核心调用 ====================

    async def call(
        self,
        prompt: str,
        system_prompt: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """
        发送对话请求（带重试和降级）

        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            history: 历史对话 [{"role": "user/assistant", "content": "..."}]
            temperature: 温度
            max_tokens: 最大输出 Token

        Returns:
            LLMResponse
        """
        messages = self._build_messages(prompt, system_prompt, history)
        return await self._call_with_retry(messages, temperature, max_tokens, **kwargs)

    async def call_json(
        self,
        prompt: str,
        system_prompt: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """
        发送对话请求并强制 JSON 输出

        Returns:
            LLMResponse (raw_response["parsed_json"] 包含解析后的 dict)
        """
        messages = self._build_messages(prompt, system_prompt, history)
        return await self._call_json_with_retry(messages, temperature, max_tokens, **kwargs)

    # ==================== 重试与降级 ====================

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> LLMResponse:
        """带重试的调用，primary 失败切 fallback"""
        last_error = None

        # 尝试 primary
        try:
            return await self._retry_loop(
                self.primary, messages, temperature, max_tokens, **kwargs
            )
        except AIRetryExhaustedError as e:
            last_error = e
            logger.warning(f"主 Provider ({self.primary.provider_name}) 重试耗尽: {e}")

        # 尝试 fallback
        if self.fallback:
            logger.info(f"切换到备用 Provider: {self.fallback.provider_name}")
            try:
                return await self._retry_loop(
                    self.fallback, messages, temperature, max_tokens, **kwargs
                )
            except AIRetryExhaustedError as e:
                last_error = e
                logger.error(f"备用 Provider ({self.fallback.provider_name}) 重试耗尽: {e}")

        raise AIServiceError(
            f"所有 Provider 调用失败，最后错误: {last_error}",
            provider=last_error.provider if last_error else "",
        )

    async def _call_json_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> LLMResponse:
        """带重试的 JSON 调用"""
        last_error = None

        try:
            return await self._retry_loop(
                self.primary, messages, temperature, max_tokens, json_mode=True, **kwargs
            )
        except (AIRetryExhaustedError, AIProviderError) as e:
            last_error = e
            logger.warning(f"主 Provider JSON 调用失败: {e}")

        if self.fallback:
            logger.info(f"JSON 调用切换到备用: {self.fallback.provider_name}")
            try:
                return await self._retry_loop(
                    self.fallback, messages, temperature, max_tokens, json_mode=True, **kwargs
                )
            except (AIRetryExhaustedError, AIProviderError) as e:
                last_error = e

        raise AIServiceError(
            f"JSON 调用全部失败: {last_error}",
            provider=last_error.provider if last_error else "",
        )

    async def _retry_loop(
        self,
        provider: BaseLLMProvider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """指数退避重试循环"""
        method = provider.chat_json if json_mode else provider.chat
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await method(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
                if attempt > 0:
                    logger.info(f"重试第 {attempt + 1} 次成功 ({provider.provider_name})")
                return response

            except AIProviderError as e:
                last_error = e
                if _is_retryable(e) and attempt < self.max_retries - 1:
                    delay = self.retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Provider {provider.provider_name} 调用失败 (尝试 {attempt + 1}/{self.max_retries})，"
                        f"{delay:.1f}s 后重试: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    # 不可重试的错误直接抛出
                    raise AIRetryExhaustedError(
                        f"{provider.provider_name} 重试耗尽: {e}",
                        provider=provider.provider_name,
                        original_error=e,
                    )
            except Exception as e:
                last_error = e
                raise AIRetryExhaustedError(
                    f"{provider.provider_name} 未知错误: {e}",
                    provider=provider.provider_name,
                    original_error=e,
                )

        raise AIRetryExhaustedError(
            f"{provider.provider_name} 重试耗尽",
            provider=provider.provider_name,
            original_error=last_error,
        )

    # ==================== 辅助方法 ====================

    @staticmethod
    def _build_messages(
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        """构建 OpenAI 格式的 messages 数组"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages
