"""
Docker 执行器配置模块
所有配置通过环境变量注入，无 GUI、无配置文件
"""

import os
import uuid
from dataclasses import dataclass, field


@dataclass
class ExecutorConfig:
    """执行器运行配置"""

    # ---- 后端连接 ----
    backend_url: str = "http://backend:8000"

    # ---- RabbitMQ 连接 ----
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"

    # ---- 执行机身份 ----
    executor_uuid: str = ""
    executor_name: str = "docker-executor"
    owner_username: str = ""

    # ---- 运行参数 ----
    max_concurrent: int = 2
    heartbeat_interval: int = 30

    # ---- 浏览器 ----
    headless: bool = True
    default_browser: str = "chromium"

    # ---- Trace 录制 ----
    trace_enabled: bool = True

    # ---- 调试 ----
    slow_mo: int = 0  # 毫秒，0 表示不延迟

    # ---- 内部属性 ----
    _executor_id: int = 0

    @property
    def rabbitmq_url(self) -> str:
        """构建 RabbitMQ 连接 URL"""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )

    @property
    def queue_name(self) -> str:
        """RabbitMQ 专属队列名"""
        return f"executor.{self.executor_uuid}"


def load_config() -> ExecutorConfig:
    """
    从环境变量加载配置
    如果 EXECUTOR_UUID 未设置，自动生成一个（适用于 docker-compose scale）
    """
    executor_uuid = os.getenv("EXECUTOR_UUID", "")
    if not executor_uuid:
        # 自动生成，便于 scale 弹性扩展
        executor_uuid = str(uuid.uuid4())
        os.environ["EXECUTOR_UUID"] = executor_uuid

    config = ExecutorConfig(
        backend_url=os.getenv("BACKEND_URL", "http://backend:8000"),
        rabbitmq_host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        rabbitmq_port=int(os.getenv("RABBITMQ_PORT", "5672")),
        rabbitmq_user=os.getenv("RABBITMQ_USER", "guest"),
        rabbitmq_password=os.getenv("RABBITMQ_PASSWORD", "guest"),
        rabbitmq_vhost=os.getenv("RABBITMQ_VHOST", "/"),
        executor_uuid=executor_uuid,
        executor_name=os.getenv("EXECUTOR_NAME", f"docker-executor-{executor_uuid[:8]}"),
        owner_username=os.getenv("OWNER_USERNAME", ""),
        max_concurrent=int(os.getenv("MAX_CONCURRENT", "2")),
        heartbeat_interval=int(os.getenv("HEARTBEAT_INTERVAL", "30")),
        headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true",
        default_browser=os.getenv("DEFAULT_BROWSER", "chromium"),
        trace_enabled=os.getenv("TRACE_ENABLED", "true").lower() == "true",
        slow_mo=int(os.getenv("SLOW_MO", "0")),
    )

    return config
