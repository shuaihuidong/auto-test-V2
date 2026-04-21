"""
LLM Gateway 自定义异常
"""


class AIServiceError(Exception):
    """AI 服务基础异常"""

    def __init__(self, message: str, provider: str = "", original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)


class AIProviderError(AIServiceError):
    """Provider 调用异常（网络、API 错误等）"""
    pass


class AIRetryExhaustedError(AIServiceError):
    """重试耗尽异常"""
    pass


class AIResponseParseError(AIServiceError):
    """响应解析异常（JSON 格式错误等）"""
    pass
