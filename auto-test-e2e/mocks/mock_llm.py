"""
Mock 策略: LLM Gateway 响应 Mock
通过 unittest.mock 替换 ai_service 的 HTTP 调用，无需真实 API Key。
同时提供 mock_llm_server 作为独立的 HTTP Server (已在 conftest.py 中实现)。
"""
import json
from typing import Optional
from unittest.mock import patch, MagicMock


# ============================================================
# 策略 A: Mock HTTP 响应 (推荐, 无需启动服务)
# ============================================================

def create_mock_llm_response(content: dict, model: str = "mock-model",
                              total_tokens: int = 300) -> dict:
    """构造 OpenAI 兼容格式的 Mock 响应"""
    return {
        "id": "mock-response-id",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(content, ensure_ascii=False),
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": total_tokens,
        },
        "model": model,
    }


class MockLLMGateway:
    """
    通过 mock httpx.Client 替换 LLM Gateway 的 HTTP 调用。

    使用方式:
        mock = MockLLMGateway()
        mock.set_response("nl2script", {...})
        mock.start()
        # ... 执行测试 ...
        mock.stop()
    """

    def __init__(self):
        self._responses = {
            "nl2script": create_mock_llm_response({
                "steps": [
                    {"type": "open_page", "name": "打开页面", "params": {"url": "https://www.baidu.com"}},
                    {"type": "input_text", "name": "输入文本", "params": {
                        "locator": {"type": "css", "value": "#kw"},
                        "value": "playwright",
                    }},
                    {"type": "click", "name": "点击搜索", "params": {
                        "locator": {"type": "css", "value": "#su"},
                    }},
                ]
            }),
            "healing": create_mock_llm_response({
                "suggested_locator": "input[name='wd']",
                "locator_type": "css",
                "confidence": 0.92,
                "reason": "原定位器已失效，通过 DOM 分析发现等效替代",
                "strategy": "dom_analysis",
            }),
            "default": create_mock_llm_response({
                "steps": [
                    {"type": "open_page", "name": "打开页面", "params": {"url": "https://example.com"}},
                ]
            }),
        }
        self._active_response = "default"
        self._call_log = []
        self._patcher = None

    def set_response(self, scenario: str, response: dict):
        """设置指定场景的响应"""
        self._responses[scenario] = create_mock_llm_response(response)
        self._active_response = scenario

    def use_scenario(self, scenario: str):
        """切换到指定场景的预设响应"""
        self._active_response = scenario

    def start(self):
        """启动 Mock，替换 httpx.AsyncClient 或 httpx.Client"""
        gateway = self

        class MockResponse:
            def __init__(self, data):
                self._data = data
                self.status_code = 200

            def json(self):
                return self._data

            def raise_for_status(self):
                pass

        def mock_post(url, **kwargs):
            gateway._call_log.append({"url": url, "kwargs": kwargs})
            response_data = gateway._responses.get(
                gateway._active_response,
                gateway._responses["default"]
            )
            return MockResponse(response_data)

        self._patcher = patch("httpx.Client.post", side_effect=mock_post)
        self._patcher.start()

    def stop(self):
        """停止 Mock"""
        if self._patcher:
            self._patcher.stop()

    @property
    def call_count(self) -> int:
        return len(self._call_log)

    @property
    def last_call(self) -> Optional[dict]:
        return self._call_log[-1] if self._call_log else None

    def get_calls_to(self, url_substring: str) -> list:
        """获取所有包含指定字符串的 URL 调用"""
        return [c for c in self._call_log if url_substring in c.get("url", "")]


# ============================================================
# 策略 B: Mock settings (关闭 AI 功能)
# ============================================================

def disable_ai_service():
    """
    完全禁用 AI 服务，使平台在没有 LLM API 的环境下正常运行。
    NL2Script 和 Healing API 会返回 503。
    """
    import os
    os.environ["AI_PRIMARY_PROVIDER"] = ""
    os.environ["AI_FALLBACK_PROVIDER"] = ""


# ============================================================
# Fixture 用法示例 (添加到 conftest.py):
# ============================================================
#
# @pytest.fixture(scope="function")
# def mock_llm():
#     gateway = MockLLMGateway()
#     gateway.start()
#     yield gateway
#     gateway.stop()
#
# 使用示例:
# def test_nl2script_with_mock_llm(api_client, mock_llm):
#     mock_llm.use_scenario("nl2script")
#     resp = api_client.post(f"{api_client.base_url}/scripts/nl2script/",
#                            json={"prompt": "打开百度搜索"})
#     assert resp.status_code == 200
#     assert len(resp.json()["steps"]) == 3
#     assert mock_llm.call_count == 1
