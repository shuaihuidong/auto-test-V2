"""
异步任务管理器 - 替代 PyQt6 版本的同步 task_manager_v2
- aio-pika 消费 RabbitMQ 任务
- httpx 异步上报心跳和结果
- asyncio 全链路，无线程竞争
"""

import asyncio
import json
import os
import time
import traceback
from typing import Any, Callable, Dict, Optional

import aio_pika
import httpx
from loguru import logger

from config import ExecutorConfig
from executor import PlaywrightScriptExecutor

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AsyncTaskManager:
    """异步任务管理器"""

    def __init__(self, config: ExecutorConfig):
        self.config = config

        # 连接
        self._mq_connection: Optional[aio_pika.RobustConnection] = None
        self._mq_channel: Optional[aio_pika.RobustChannel] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        # 任务追踪
        self.running_tasks: Dict[str, Dict[str, Any]] = {}
        self.cancelled_tasks: set = set()

        # 顺序执行等待队列
        self._sequential_wait_queue: Dict[str, list] = {}

        # 已停止的父执行 ID 缓存
        self._stopped_executions: set = set()

        # 后台任务
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # 回调
        self.on_task_complete: Optional[Callable] = None

    # ==================== 生命周期 ====================

    async def connect(self) -> bool:
        """
        连接到平台：注册 → 连 MQ → 启动心跳

        Returns:
            是否连接成功
        """
        try:
            # 1. 创建 HTTP 客户端
            self._http_client = httpx.AsyncClient(verify=False, timeout=15)

            # 2. 注册执行机
            if not await self._register_executor():
                return False

            # 3. 连接 RabbitMQ
            if not await self._connect_mq():
                return False

            # 4. 启动心跳
            self._running = True
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info("执行机已成功连接到平台")
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    async def disconnect(self):
        """断开所有连接"""
        logger.info("正在断开连接...")
        self._running = False

        # 取消心跳
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 取消所有任务
        for task_id in list(self.running_tasks.keys()):
            self.cancelled_tasks.add(task_id)

        # 关闭 MQ
        if self._mq_connection:
            try:
                await self._mq_connection.close()
            except Exception:
                pass

        # 关闭 HTTP
        if self._http_client:
            try:
                await self._http_client.aclose()
            except Exception:
                pass

        self.running_tasks.clear()
        self.cancelled_tasks.clear()
        self._stopped_executions.clear()
        self._sequential_wait_queue.clear()
        logger.info("已断开连接")

    # ==================== 注册 ====================

    async def _register_executor(self) -> bool:
        """注册执行机到后端（带重试）"""
        url = f"{self.config.backend_url}/api/executor/register/"
        payload = {
            "executor_uuid": self.config.executor_uuid,
            "executor_name": self.config.executor_name,
            "platform": f"docker-{os.uname().machine if hasattr(os, 'uname') else 'x86_64'}",
            "browser_types": ["chromium", "firefox"],
            "owner_username": self.config.owner_username,
        }

        for attempt in range(5):
            try:
                resp = await self._http_client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    self.config._executor_id = data.get("executor_id", 0)
                    logger.info(f"执行机注册成功, executor_id={self.config._executor_id}")
                    return True
                logger.warning(f"注册失败: HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"注册异常 (尝试 {attempt + 1}/5): {e}")

            if attempt < 4:
                await asyncio.sleep(2 * (2 ** attempt))

        logger.error("执行机注册失败：已达最大重试次数")
        return False

    # ==================== RabbitMQ ====================

    async def _connect_mq(self) -> bool:
        """连接 RabbitMQ 并开始消费"""
        try:
            self._mq_connection = await aio_pika.connect_robust(
                self.config.rabbitmq_url,
            )
            self._mq_channel = await self._mq_connection.channel()
            await self._mq_channel.set_qos(prefetch_count=self.config.max_concurrent)

            # 声明交换机和队列
            exchange = await self._mq_channel.declare_exchange(
                "tasks.exchange",
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
            queue = await self._mq_channel.declare_queue(
                self.config.queue_name,
                durable=True,
            )
            await queue.bind(exchange, routing_key=self.config.queue_name)

            # 开始消费
            await queue.consume(self._on_message)
            logger.info(f"RabbitMQ 已连接，监听队列: {self.config.queue_name}")
            return True

        except Exception as e:
            logger.error(f"RabbitMQ 连接失败: {e}")
            return False

    async def _on_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        """收到 MQ 消息的回调"""
        async with message.process(requeue=False):
            try:
                task_data = json.loads(message.body)
                task_id = task_data.get("task_id", "")
                logger.info(f"收到任务: {task_id}")

                # 验证任务状态
                if not await self._validate_task(task_data):
                    logger.warning(f"任务 {task_id} 无效或已停止，拒绝接收")
                    await message.nack(requeue=False)
                    return

                # 并发检查
                if len(self.running_tasks) >= self.config.max_concurrent:
                    logger.warning(f"已达最大并发 ({self.config.max_concurrent})，拒绝任务 {task_id}")
                    await message.nack(requeue=True)
                    return

                # 接收任务，异步执行
                script_data = task_data.get("script_data", {})
                self.running_tasks[task_id] = {
                    "execution_id": task_data.get("execution_id"),
                    "script_name": script_data.get("name", "未命名脚本"),
                    "script_data": script_data,
                    "status": "starting",
                }

                asyncio.create_task(self._execute_task(task_data))
                logger.info(f"任务 {task_id} 已接收并开始执行")

            except json.JSONDecodeError as e:
                logger.error(f"任务消息解析失败: {e}")
            except Exception as e:
                logger.error(f"处理任务消息异常: {e}")

    # ==================== 任务执行 ====================

    async def _execute_task(self, task_data: Dict[str, Any]):
        """执行单个任务"""
        task_id = task_data.get("task_id", "")
        script_data = task_data.get("script_data", {})
        variables = task_data.get("variables", {})
        browser_type = task_data.get("browser_type", self.config.default_browser)

        if task_id in self.running_tasks:
            self.running_tasks[task_id]["status"] = "running"

        executor = None
        result = None

        try:
            # 检查父执行是否已停止
            parent_id = script_data.get("parent_execution_id")
            if parent_id and parent_id in self._stopped_executions:
                raise Exception("父执行已被用户停止")

            if task_id in self.cancelled_tasks:
                raise Exception("任务已被取消")

            # 启动 Playwright 浏览器
            executor = PlaywrightScriptExecutor(self.config)
            if not await executor.start(browser_type):
                raise Exception("浏览器启动失败")

            # 执行脚本
            result = await executor.execute_script(script_data, variables)

            # 上报结果
            await self._send_task_result(task_id, {
                "status": "completed" if result["success"] else "failed",
                "message": result["message"],
                "steps": result.get("steps", []),
                "duration": result.get("duration", 0),
            })

            # 上报截图（失败步骤）
            for step in result.get("steps", []):
                if not step.get("success") and step.get("screenshot"):
                    await self._send_screenshot(task_id, step["screenshot"])

            # 上报 Trace（如果有）
            if executor.trace_path:
                await self._upload_trace(task_id, executor.trace_path)

        except Exception as e:
            logger.exception(f"任务 {task_id} 执行异常")
            await self._send_task_result(task_id, {
                "status": "failed",
                "message": f"执行异常: {str(e)}",
            })

        finally:
            if executor:
                await executor.stop()

            self.running_tasks.pop(task_id, None)
            self.cancelled_tasks.discard(task_id)

            # 触发等待队列中的下一个任务
            parent_id = script_data.get("parent_execution_id")
            if parent_id:
                await self._process_sequential_queue(parent_id)

            if self.on_task_complete:
                try:
                    self.on_task_complete(task_id)
                except Exception:
                    pass

            logger.info(f"任务结束: {task_id}")

    # ==================== HTTP 上报 ====================

    async def _send_task_result(self, task_id: str, result: Dict[str, Any]):
        """上报任务结果"""
        try:
            url = f"{self.config.backend_url}/api/tasks/{task_id}/result/"

            # 清理 steps 中的截图数据（已单独上报）
            cleaned_steps = []
            for step in result.get("steps", []):
                cleaned_steps.append({
                    k: v for k, v in step.items()
                    if k in ("name", "type", "success", "message", "duration", "step_index")
                })
            result["steps"] = cleaned_steps
            result.pop("error", None)

            resp = await self._http_client.post(url, json=result, timeout=15)
            if resp.status_code == 200:
                logger.info(f"任务结果已上报: {task_id}")
                # 请求后端分发新任务
                try:
                    await self._http_client.post(
                        f"{self.config.backend_url}/api/tasks/distribute/",
                        json={},
                        timeout=5,
                    )
                except Exception:
                    pass
            else:
                logger.error(f"上报结果失败: HTTP {resp.status_code}")

        except Exception as e:
            logger.error(f"上报结果异常: {e}")

    async def _send_screenshot(self, task_id: str, image_data: str, is_failure: bool = True):
        """上报截图"""
        try:
            url = f"{self.config.backend_url}/api/tasks/{task_id}/screenshot/"
            await self._http_client.post(url, json={
                "image_data": image_data,
                "is_failure": is_failure,
            }, timeout=15)
            logger.info(f"截图已上报: {task_id}")
        except Exception as e:
            logger.error(f"上报截图失败: {e}")

    async def _upload_trace(self, task_id: str, trace_path: str):
        """上传 Trace 文件到后端"""
        try:
            if not os.path.exists(trace_path):
                return
            url = f"{self.config.backend_url}/api/tasks/{task_id}/trace/"
            with open(trace_path, "rb") as f:
                files = {"trace": ("trace.zip", f, "application/zip")}
                resp = await self._http_client.post(url, files=files, timeout=30)
                if resp.status_code in (200, 201):
                    logger.info(f"Trace 已上传: {task_id}")
                else:
                    logger.warning(f"Trace 上传失败: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Trace 上传异常（后端可能尚未支持）: {e}")

    # ==================== 心跳 ====================

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
            await asyncio.sleep(self.config.heartbeat_interval)

    async def _send_heartbeat(self):
        """发送心跳"""
        try:
            # 检查运行中父执行状态
            await self._check_running_parent_executions()

            current_tasks = len(self.running_tasks)
            status = "idle" if current_tasks == 0 else "busy"

            url = f"{self.config.backend_url}/api/executor/heartbeat/"
            await self._http_client.post(url, json={
                "executor_uuid": self.config.executor_uuid,
                "status": status,
                "current_tasks": current_tasks,
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0,
                "message": "",
            }, timeout=5)

        except Exception as e:
            logger.debug(f"心跳异常: {e}")

    async def _check_running_parent_executions(self):
        """检查运行中的父执行是否已被停止"""
        parent_ids = set()
        for task_info in self.running_tasks.values():
            pid = task_info.get("script_data", {}).get("parent_execution_id")
            if pid and pid not in self._stopped_executions:
                parent_ids.add(pid)

        for pid in parent_ids:
            try:
                url = f"{self.config.backend_url}/api/executions/{pid}/status_check/"
                resp = await self._http_client.get(url, timeout=3)
                if resp.status_code == 200 and resp.json().get("status") == "stopped":
                    self._stopped_executions.add(pid)
                    logger.warning(f"父执行 {pid} 已停止")
            except Exception:
                pass

    # ==================== 任务验证 ====================

    async def _validate_task(self, task_data: Dict[str, Any]) -> bool:
        """验证任务是否仍然有效"""
        parent_id = task_data.get("script_data", {}).get("parent_execution_id")
        if not parent_id:
            return True

        if parent_id in self._stopped_executions:
            return False

        try:
            url = f"{self.config.backend_url}/api/executions/{parent_id}/status_check/"
            resp = await self._http_client.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.json().get("status") != "stopped"
        except Exception:
            pass
        return True

    # ==================== 顺序执行 ====================

    async def _process_sequential_queue(self, parent_execution_id: str):
        """处理顺序执行等待队列"""
        if len(self.running_tasks) >= self.config.max_concurrent:
            return

        # 检查是否还有同父任务在运行
        for info in self.running_tasks.values():
            if info.get("script_data", {}).get("parent_execution_id") == parent_execution_id:
                return

        # 取下一个等待任务
        wait_queue = self._sequential_wait_queue.get(parent_execution_id, [])
        if not wait_queue:
            return

        next_task = wait_queue.pop(0)
        if not wait_queue:
            del self._sequential_wait_queue[parent_execution_id]

        task_id = next_task.get("task_id", "")
        script_data = next_task.get("script_data", {})
        self.running_tasks[task_id] = {
            "execution_id": next_task.get("execution_id"),
            "script_name": script_data.get("name", "未命名脚本"),
            "script_data": script_data,
            "status": "starting",
        }

        asyncio.create_task(self._execute_task(next_task))
        logger.info(f"顺序执行：触发下一个等待任务 {task_id}")
