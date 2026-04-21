"""
LLM Provider 实现
- OpenAIProvider: 兼容所有 OpenAI API 格式的服务商（OpenAI / DeepSeek / 本地部署）
- QwenProvider: 阿里通义千问 DashScope API
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from .exceptions import AIProviderError, AIResponseParseError


@dataclass
class LLMResponse:
    """LLM 响应统一结构"""
    content: str                     # 文本内容
    model: str                       # 实际使用的模型
    provider: str                    # 提供商标识
    prompt_tokens: int = 0           # 输入 Token 数
    completion_tokens: int = 0       # 输出 Token 数
    total_tokens: int = 0            # 总 Token 数
    raw_response: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_usage(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class BaseLLMProvider(ABC):
    """Provider 抽象基类"""

    provider_name: str = ""

    def __init__(self, api_key: str, model: str, timeout: int = 60, **kwargs):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.extra_config = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """发送对话请求"""
        ...

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """
        强制 JSON 输出。
        默认实现：在 system prompt 追加 JSON 指令，解析响应。
        子类可重写以使用原生 JSON mode。
        """
        # 注入 JSON 格式要求
        enriched = list(messages)
        if enriched and enriched[0]["role"] == "system":
            enriched[0] = {
                "role": "system",
                "content": enriched[0]["content"] + "\n\n请严格以合法 JSON 格式输出，不要包含 markdown 代码块标记。",
            }
        else:
            enriched.insert(0, {
                "role": "system",
                "content": "请严格以合法 JSON 格式输出，不要包含 markdown 代码块标记。",
            })

        response = await self.chat(enriched, temperature=temperature, max_tokens=max_tokens, **kwargs)

        # 清理并解析 JSON
        content = response.content.strip()
        if content.startswith("```"):
            # 移除 markdown 代码块包裹
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
            response.raw_response["parsed_json"] = parsed
        except json.JSONDecodeError as e:
            raise AIResponseParseError(
                f"JSON 解析失败: {e}\n原始内容: {content[:500]}",
                provider=self.provider_name,
            )

        return response


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI 兼容 Provider
    支持 OpenAI / DeepSeek / 任何兼容 OpenAI API 格式的服务商
    """

    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 60,
        **kwargs,
    ):
        super().__init__(api_key, model, timeout, **kwargs)
        self.api_base = api_base.rstrip("/")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.TimeoutException as e:
                raise AIProviderError(f"请求超时 ({self.timeout}s)", provider=self.provider_name, original_error=e)
            except httpx.HTTPStatusError as e:
                body = e.response.text[:500]
                raise AIProviderError(
                    f"API 返回错误: HTTP {e.response.status_code} - {body}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.RequestError as e:
                raise AIProviderError(f"网络请求失败: {e}", provider=self.provider_name, original_error=e)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.provider_name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            raw_response=data,
        )


class QwenProvider(BaseLLMProvider):
    """
    阿里通义千问 Provider
    基于 DashScope OpenAI 兼容接口
    """

    provider_name = "qwen"

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-max",
        timeout: int = 60,
        **kwargs,
    ):
        super().__init__(api_key, model, timeout, **kwargs)
        # DashScope 的 OpenAI 兼容端点
        self.api_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
            except httpx.TimeoutException as e:
                raise AIProviderError(f"请求超时 ({self.timeout}s)", provider=self.provider_name, original_error=e)
            except httpx.HTTPStatusError as e:
                body = e.response.text[:500]
                raise AIProviderError(
                    f"API 返回错误: HTTP {e.response.status_code} - {body}",
                    provider=self.provider_name,
                    original_error=e,
                )
            except httpx.RequestError as e:
                raise AIProviderError(f"网络请求失败: {e}", provider=self.provider_name, original_error=e)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.provider_name,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            raw_response=data,
        )


# Provider 注册表：名称 → 类
PROVIDER_REGISTRY: Dict[str, type] = {
    "openai": OpenAIProvider,
    "qwen": QwenProvider,
}
