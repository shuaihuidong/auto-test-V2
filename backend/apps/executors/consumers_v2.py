"""
WebSocket Consumer - 执行状态展示

用于 Web UI 实时状态展示（保留兼容，前端可通过此通道监听执行机相关事件）。
任务下发已迁移到轻量化执行引擎 (ExecutionRunner)。
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ExecutorStatusConsumer(AsyncWebsocketConsumer):
    """
    执行机状态 WebSocket Consumer

    用于 Web UI 实时监听执行状态变化
    """

    async def connect(self):
        """建立连接"""
        self.group_name = 'executor_status'

        # 加入状态广播组
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("客户端已连接到执行状态监听")

    async def disconnect(self, close_code):
        """断开连接"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """接收消息"""
        try:
            message = json.loads(text_data)
            msg_type = message.get('type')
            logger.debug(f"收到消息: type={msg_type}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    # 事件处理器（通过 channel_layer 调用）

    async def executor_online(self, event):
        """执行机上线事件"""
        await self.send(text_data=json.dumps({
            'type': 'executor_online',
            'data': event.get('data', {})
        }))

    async def executor_offline(self, event):
        """执行机离线事件"""
        await self.send(text_data=json.dumps({
            'type': 'executor_offline',
            'data': event.get('data', {})
        }))

    async def executor_status_update(self, event):
        """执行机状态更新事件"""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': event.get('data', {})
        }))

    async def task_started(self, event):
        """任务开始事件"""
        await self.send(text_data=json.dumps({
            'type': 'task_started',
            'data': event.get('data', {})
        }))

    async def task_completed(self, event):
        """任务完成事件"""
        await self.send(text_data=json.dumps({
            'type': 'task_completed',
            'data': event.get('data', {})
        }))

    async def task_failed(self, event):
        """任务失败事件"""
        await self.send(text_data=json.dumps({
            'type': 'task_failed',
            'data': event.get('data', {})
        }))
