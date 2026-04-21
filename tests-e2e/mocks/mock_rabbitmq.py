"""
Mock 策略: RabbitMQ 消息生产/消费
在 E2E 测试中替代真实 RabbitMQ，拦截 Django 的消息发布并模拟消费者回调。
"""
import json
import threading
from typing import Callable, Dict, List, Optional
from unittest.mock import patch, MagicMock


class MockRabbitMQ:
    """
    内存版 RabbitMQ 替代品。

    工作原理:
    1. 通过 unittest.mock.patch 替换 Django 的 pika 连接
    2. 消息发布时存入内存队列
    3. 提供 consume() 方法模拟消费并触发回调
    4. 提供 get_messages() 方法检查已发布的消息

    使用方式 (在 conftest.py 中作为 fixture):
        @pytest.fixture
        def mock_mq():
            mq = MockRabbitMQ()
            mq.start()
            yield mq
            mq.stop()
    """

    def __init__(self):
        self._queues: Dict[str, List[dict]] = {}
        self._exchanges: Dict[str, List[str]] = {}  # exchange -> [routing_keys]
        self._bindings: Dict[str, str] = {}  # routing_key -> queue_name
        self._consumers: Dict[str, Callable] = {}  # queue_name -> callback
        self._patcher = None
        self._published_messages: List[dict] = []

    def start(self):
        """启动 Mock，替换 pika.BlockingConnection"""
        mock_connection = MagicMock()
        mock_channel = MagicMock()

        # 拦截 basic_publish: 将消息存入内存队列
        def fake_publish(exchange, routing_key, body, properties=None):
            message = {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": json.loads(body) if isinstance(body, str) else body,
                "properties": properties,
            }
            self._published_messages.append(message)
            if routing_key in self._bindings:
                queue = self._bindings[routing_key]
                self._queues.setdefault(queue, []).append(message)

        mock_channel.basic_publish.side_effect = fake_publish

        # 拦截 queue_declare: 返回一个 mock 方法
        mock_channel.queue_declare.return_value = MagicMock(method=MagicMock(queue="mock-queue"))

        # 拦截 basic_consume: 注册回调
        def fake_consume(queue, on_message_callback, auto_ack=True):
            self._consumers[queue] = on_message_callback

        mock_channel.basic_consume.side_effect = fake_consume

        mock_connection.channel.return_value = mock_channel

        self._patcher = patch("pika.BlockingConnection", return_value=mock_connection)
        self._patcher.start()

    def stop(self):
        """停止 Mock"""
        if self._patcher:
            self._patcher.stop()

    def get_published_messages(self, routing_key: Optional[str] = None) -> List[dict]:
        """获取已发布的消息列表，可按 routing_key 过滤"""
        if routing_key:
            return [m for m in self._published_messages if m["routing_key"] == routing_key]
        return self._published_messages

    def get_task_messages(self) -> List[dict]:
        """获取所有 executor 任务消息 (routing_key 以 executor. 开头)"""
        return [m for m in self._published_messages if m["routing_key"].startswith("executor.")]

    def consume_message(self, queue_name: str, message: Optional[dict] = None):
        """
        模拟消费一条消息。
        如果指定了 message，消费该消息；否则消费队列中的第一条。
        """
        if queue_name not in self._consumers:
            raise ValueError(f"No consumer registered for queue: {queue_name}")

        if message is None:
            messages = self._queues.get(queue_name, [])
            if not messages:
                return
            message = messages.pop(0)

        callback = self._consumers[queue_name]
        # 构造 pika 的 mock method 和 properties
        mock_method = MagicMock()
        mock_method.routing_key = message.get("routing_key", "")
        mock_properties = MagicMock()
        mock_properties.headers = {}
        callback(
            mock_channel_or_connection=MagicMock(),
            method=mock_method,
            properties=mock_properties,
            body=json.dumps(message["body"]),
        )

    def consume_all(self, queue_name: str):
        """消费指定队列的所有消息"""
        while self._queues.get(queue_name):
            self.consume_message(queue_name)

    def clear(self):
        """清空所有消息"""
        self._published_messages.clear()
        self._queues.clear()

    @property
    def message_count(self) -> int:
        return len(self._published_messages)

    def bind_queue(self, routing_key: str, queue_name: str):
        """绑定 routing_key 到队列"""
        self._bindings[routing_key] = queue_name


# ============================================================
# Fixture 用法示例 (添加到 conftest.py):
# ============================================================
#
# @pytest.fixture(scope="function")
# def mock_mq():
#     mq = MockRabbitMQ()
#     mq.start()
#     yield mq
#     mq.stop()
#
# 使用示例:
# def test_task_published_to_mq(api_client, mock_mq, test_script):
#     api_client.post(f"{api_client.base_url}/executions/", json={"script_id": test_script["id"]})
#     messages = mock_mq.get_task_messages()
#     assert len(messages) >= 1
#     assert messages[0]["body"]["script_id"] == test_script["id"]
