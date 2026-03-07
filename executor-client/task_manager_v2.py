"""
任务管理器 V2 - 集成消息队列和 HTTP 心跳

主要变更:
1. 使用 RabbitMQ 消息队列接收任务，替代 WebSocket
2. 使用 HTTP API 上报心跳和状态
3. 保留 WebSocket 仅用于 Web UI 状态展示（可选）
"""

import threading
import time
import traceback
from typing import Dict, Any, Optional
from loguru import logger
import requests

# 禁用 SSL 警告（用于自签名证书）
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import get_config_manager, ExecutorConfig
from executor import ScriptExecutor
from message_queue_client import get_message_queue_consumer
from utils.system import get_resource_usage


class TaskManagerV2:
    """
    任务管理器 V2

    负责：
    1. 从消息队列接收任务并执行
    2. 通过 HTTP 上报心跳和状态
    3. 实时上报日志和截图到平台
    """

    def __init__(self):
        self.config: ExecutorConfig = get_config_manager().get()
        self.mq_consumer = get_message_queue_consumer()
        self.running_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_info
        self.cancelled_tasks: set = set()

        # 【修复】停止的父执行集合，记录已被用户停止的父执行ID
        # 使用列表+锁来管理，支持清理过期条目
        self._stopped_executions_list: list = []
        self._stopped_executions_lock = threading.Lock()
        self._stopped_cache_max_size = 100

        # 【修复】保存计划执行信息（用于GUI显示），保留历史记录
        # 只保留最近 N 条记录，避免内存无限增长
        self.plan_executions: Dict[str, Dict[str, Any]] = {}  # parent_execution_id -> plan_info
        self._plan_executions_lock = threading.Lock()
        self._max_history_records = 50  # 最多保留 50 条历史记录

        # 心跳线程
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._is_heartbeat_running = False

        # 任务完成回调
        self.on_task_complete = None  # callable(task_id, status, message)

        # 顺序执行的等待队列：parent_execution_id -> [等待的任务列表]
        self._sequential_wait_queue: Dict[str, list] = {}
        self._wait_lock = threading.Lock()

        # 设置消息队列回调
        self.mq_consumer.on_task_received = self.on_task_received
        self.mq_consumer.on_connected = self.on_mq_connected
        self.mq_consumer.on_disconnected = self.on_mq_disconnected
        self.mq_consumer.on_error = self.on_mq_error

    def connect(self) -> bool:
        """
        连接到服务器（注册执行机 + 启动消息队列消费者 + 启动心跳）

        Returns:
            是否连接成功
        """
        try:
            # 1. 注册执行机
            if not self._register_executor():
                return False

            # 2. 启动消息队列消费者
            if not self.mq_consumer.start():
                logger.error("启动消息队列消费者失败")
                return False

            # 3. 启动心跳线程
            self._start_heartbeat()

            logger.info("执行机已成功连接到平台")
            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            return False

    def _register_executor(self, max_retries: int = 5, initial_delay: float = 2.0) -> bool:
        """
        注册执行机到平台（带重试机制）

        Args:
            max_retries: 最大重试次数（默认5次）
            initial_delay: 初始重试延迟秒数（默认2秒）

        Returns:
            是否注册成功
        """
        import time

        api_base = self.config.server_url.rstrip('/')
        register_url = f"{api_base}/api/executor/register/"

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    register_url,
                    json={
                        "executor_uuid": self.config.executor_uuid,
                        "executor_name": self.config.executor_name,
                        "platform": "Windows",
                        "browser_types": ["chrome", "firefox", "edge"],
                        "owner_username": self.config.owner_username
                    }, verify=False, timeout=10
                )

                if response.status_code == 200:
                    logger.info("执行机注册成功")
                    return True
                else:
                    logger.warning(f"执行机注册失败: HTTP {response.status_code}")

            except Exception as e:
                logger.warning(f"执行机注册异常 (尝试 {attempt + 1}/{max_retries}): {e}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # 指数退避
                logger.info(f"等待 {delay:.1f} 秒后重试注册...")
                time.sleep(delay)
            else:
                logger.error(f"执行机注册失败：已达到最大重试次数 ({max_retries})")

        return False

    def _start_heartbeat(self):
        """启动心跳线程"""
        if self._is_heartbeat_running:
            return

        self._is_heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="Heartbeat"
        )
        self._heartbeat_thread.start()
        logger.info("心跳线程已启动")

    def _heartbeat_loop(self):
        """心跳循环（在单独线程中运行）"""
        import time

        while self._is_heartbeat_running:
            try:
                # 上报心跳
                self._send_heartbeat()

                # 等待下次心跳
                time.sleep(self.config.heartbeat_interval)

            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                time.sleep(5)  # 出错后短暂等待

    def _send_heartbeat(self):
        """发送心跳"""
        try:
            # 【关键修复】定期检查所有正在执行的父任务状态
            # 如果发现父任务已停止，则标记到 _stopped_executions 集合中
            self._check_running_parent_executions()

            # 获取系统资源使用情况
            resources = get_resource_usage()
            current_tasks = len(self.running_tasks)

            # 确定状态
            if current_tasks == 0:
                status = "idle"
            elif current_tasks < self.config.max_concurrent:
                status = "busy"
            else:
                status = "busy"

            # 构建 API URL
            api_base = self.config.server_url.rstrip('/')
            heartbeat_url = f"{api_base}/api/executor/heartbeat/"

            response = requests.post(
                heartbeat_url,
                json={
                    "executor_uuid": self.config.executor_uuid,
                    "status": status,
                    "current_tasks": current_tasks,
                    "cpu_usage": resources.get("cpu", 0),
                    "memory_usage": resources.get("memory", 0),
                    "disk_usage": resources.get("disk", 0),
                    "message": ""
                }, verify=False, timeout=5
            )

            if response.status_code == 200:
                logger.debug(f"心跳上报成功: status={status}, tasks={current_tasks}")
            else:
                logger.warning(f"心跳上报失败: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"心跳上报异常: {e}")

    def _check_running_parent_executions(self):
        """
        检查所有正在执行的父任务状态
        如果发现已停止的父任务，则标记到 _stopped_executions_list 中
        """
        try:
            # 获取所有正在执行的父执行ID
            parent_ids = set()
            with self._stopped_executions_lock:
                stopped_set = set(self._stopped_executions_list)

            for task_id, task_info in self.running_tasks.items():
                script_data = task_info.get("script_data", {})
                parent_id = script_data.get("parent_execution_id")
                if parent_id and parent_id not in stopped_set:
                    parent_ids.add(parent_id)

            # 批量查询这些父执行的状态
            if parent_ids:
                api_base = self.config.server_url.rstrip('/')
                for parent_id in parent_ids:
                    try:
                        status_check_url = f"{api_base}/api/executions/{parent_id}/status_check/"
                        response = requests.get(status_check_url, verify=False, timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            status = data.get("status", "")
                            if status == "stopped":
                                logger.warning(f"[心跳检查] 父执行 {parent_id} 已停止，加入停止列表")
                                with self._stopped_executions_lock:
                                    if parent_id not in self._stopped_executions_list:
                                        self._stopped_executions_list.append(parent_id)
                                        # 限制缓存大小，移除最旧的条目
                                        if len(self._stopped_executions_list) > self._stopped_cache_max_size:
                                            self._stopped_executions_list.pop(0)
                    except:
                        pass  # 查询失败，下次心跳再试

            # 【修复】定期清理已完成的停止执行ID
            # 检查缓存中的父执行ID是否还在running_tasks中，如果不在则可以清理
            with self._stopped_executions_lock:
                if len(self._stopped_executions_list) > 10:  # 只有缓存较大时才清理
                    # 获取当前所有运行任务的父执行ID
                    current_parent_ids = set()
                    for task_info in self.running_tasks.values():
                        script_data = task_info.get("script_data", {})
                        parent_id = script_data.get("parent_execution_id")
                        if parent_id:
                            current_parent_ids.add(parent_id)

                    # 保留仍然在运行中的父执行ID
                    self._stopped_executions_list = [
                        pid for pid in self._stopped_executions_list
                        if pid in current_parent_ids
                    ]

        except Exception as e:
            logger.debug(f"检查父执行状态异常: {e}")

    def on_task_received(self, task_data: Dict[str, Any]) -> bool:
        """
        收到任务时的回调（在消息队列线程中调用）

        Args:
            task_data: 任务数据

        Returns:
            任务是否成功接收（返回 False 会拒绝任务，让 RabbitMQ 重新排队）
        """
        task_id = task_data.get("task_id", "")
        script_data = task_data.get("script_data", {})
        script_name = script_data.get("name", "未命名脚本")
        execution_mode = script_data.get("execution_mode", "parallel")
        parent_execution_id = script_data.get("parent_execution_id")
        plan_scripts = script_data.get("plan_scripts", [])

        # 【关键修复】在接收任务前，向后端验证任务状态
        # 检查父任务是否已被停止
        if parent_execution_id:
            if not self._validate_task_status(task_data):
                logger.warning(f"任务 {task_id} 的父任务已停止，拒绝接收")
                return False  # 返回 False 拒绝任务

        # 【修复】先检查并发限制，再决定是否接收任务
        # 必须在加入 running_tasks 之前检查，避免超出限制
        current_tasks = len(self.running_tasks)
        logger.info(f"[并发检查] 任务 {task_id} 到达，当前任务数={current_tasks}，最大并发={self.config.max_concurrent}")

        if current_tasks >= self.config.max_concurrent:
            # 超过限制，拒绝任务
            logger.warning(f"执行机已达到最大并发数 ({self.config.max_concurrent})，当前任务数={current_tasks}，拒绝接收新任务 {task_id}")
            return False  # 返回 False 拒绝任务，消息会重新入队（requeue=True）

        # 【修复】对于顺序执行，需要检查是否有同父任务正在执行
        if execution_mode == 'sequential' and parent_execution_id:
            # 检查是否有相同父执行ID的任务正在运行
            for running_task_id, running_task_info in self.running_tasks.items():
                running_script_data = running_task_info.get("script_data", {})
                running_parent_id = running_script_data.get("parent_execution_id")
                if running_parent_id == parent_execution_id:
                    # 有同父任务正在执行，将当前任务加入等待队列
                    with self._wait_lock:
                        if parent_execution_id not in self._sequential_wait_queue:
                            self._sequential_wait_queue[parent_execution_id] = []
                        self._sequential_wait_queue[parent_execution_id].append(task_data)
                    logger.info(f"顺序执行：父任务 {parent_execution_id} 有任务正在执行，任务 {task_id} 加入等待队列")
                    return True  # 返回 True 表示任务已接收（ACK），但放入等待队列

        # 通过检查，加入 running_tasks
        execution_id = task_data.get("execution_id")
        self.running_tasks[task_id] = {
            "execution_id": execution_id,
            "script_name": script_name,
            "status": "starting",  # 初始状态为 starting
            "script_data": script_data  # 【修复】保存 script_data，用于后续检查
        }

        # 在新线程中执行任务
        thread = threading.Thread(
            target=self._execute_task_thread,
            args=(task_data,),
            daemon=True,
            name=f"Task-{task_id}"
        )
        thread.start()

        return True  # 返回 True 表示任务已接收（ACK），不等待执行完成

    def _check_execution_status(self, execution_id: str, parent_execution_id: str = None) -> bool:
        """
        检查执行状态是否仍然有效（未被停止）

        Args:
            execution_id: 子执行ID
            parent_execution_id: 父执行ID（如果存在）

        Returns:
            任务是否仍然有效（True=有效，False=已停止）
        """
        try:
            api_base = self.config.server_url.rstrip('/')

            # 优先检查父任务状态（如果存在）
            if parent_execution_id:
                status_check_url = f"{api_base}/api/executions/{parent_execution_id}/status_check/"
                response = requests.get(status_check_url, verify=False, timeout=3)

                if response.status_code == 200:
                    data = response.json()
                    parent_status = data.get("status", "")

                    # 如果父任务已停止，子任务也应该停止
                    if parent_status == "stopped":
                        logger.warning(f"父任务 {parent_execution_id} 已停止，子任务应停止执行")
                        return False

            # 检查子执行状态
            status_check_url = f"{api_base}/api/executions/{execution_id}/status_check/"
            response = requests.get(status_check_url, verify=False, timeout=3)

            if response.status_code == 200:
                data = response.json()
                exec_status = data.get("status", "")

                # 如果任务已停止，返回False
                if exec_status == "stopped":
                    logger.warning(f"执行 {execution_id} 已停止")
                    return False

                return True
            else:
                # 查询失败，保守处理：允许继续执行
                return True

        except Exception as e:
            # 查询异常，保守处理：允许继续执行
            # 避免网络问题导致正常执行被中断
            logger.debug(f"检查执行状态异常: {e}")
            return True

    def _check_parent_execution_status(self, parent_execution_id: str) -> bool:
        """
        检查父执行状态是否仍然有效（未被停止）

        Args:
            parent_execution_id: 父执行ID

        Returns:
            父执行是否仍然有效（True=有效，False=已停止）
        """
        try:
            import requests

# 禁用 SSL 警告（用于自签名证书）
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            api_base = self.config.server_url.rstrip('/')
            status_check_url = f"{api_base}/api/executions/{parent_execution_id}/status_check/"

            response = requests.get(status_check_url, verify=False, timeout=3)

            if response.status_code == 200:
                data = response.json()
                parent_status = data.get("status", "")

                if parent_status == "stopped":
                    logger.warning(f"父执行 {parent_execution_id} 已停止")
                    return False

                return True
            else:
                # 查询失败，保守处理：允许继续执行
                return True

        except Exception as e:
            # 查询异常，保守处理：允许继续执行
            logger.debug(f"检查父执行状态异常: {e}")
            return True

    def _validate_task_status(self, task_data: Dict[str, Any]) -> bool:
        """
        向后端验证任务状态

        检查父任务是否已被停止，如果停止则返回False

        Args:
            task_data: 任务数据

        Returns:
            任务是否仍然有效（True=有效，False=已停止）
        """
        try:
            script_data = task_data.get("script_data", {})
            parent_execution_id = script_data.get("parent_execution_id")

            if not parent_execution_id:
                # 没有父任务，是单个脚本执行，直接返回有效
                return True

            # 向后端查询父任务状态
            api_base = self.config.server_url.rstrip('/')
            status_check_url = f"{api_base}/api/executions/{parent_execution_id}/status_check/"

            response = requests.get(status_check_url, verify=False, timeout=5)

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "")
                is_valid = data.get("is_valid", False)

                # 如果父任务已停止，返回False
                if status == "stopped":
                    logger.warning(f"父任务 {parent_execution_id} 已停止，任务无效")
                    return False

                return True
            else:
                # 查询失败，保守处理：允许任务执行
                logger.warning(f"查询父任务状态失败: HTTP {response.status_code}，允许任务执行")
                return True

        except Exception as e:
            # 查询异常，保守处理：允许任务执行
            logger.warning(f"验证任务状态异常: {e}，允许任务执行")
            return True

    def _execute_task_thread(self, task_data: Dict[str, Any]):
        """
        在单独线程中执行任务

        Args:
            task_data: 任务数据
        """
        task_id = task_data.get("task_id", "")
        execution_id = task_data.get("execution_id")
        script_data = task_data.get("script_data", {})
        variables = task_data.get("variables", {})
        browser_type = task_data.get("browser_type", self.config.default_browser)

        # 【修复】任务已在 on_task_received 中加入 running_tasks
        # 这里只更新状态为 running，不再重复创建
        if task_id in self.running_tasks:
            self.running_tasks[task_id]["status"] = "running"
            self.running_tasks[task_id]["script_data"] = script_data
        else:
            # 异常情况：任务不在 running_tasks 中，可能是并发问题
            logger.warning(f"任务 {task_id} 不在 running_tasks 中，添加它")
            self.running_tasks[task_id] = {
                "execution_id": execution_id,
                "script_name": script_data.get("name", "未命名脚本"),
                "status": "running",
                "script_data": script_data
            }

        # 如果是计划执行，保存计划信息（用于GUI显示）
        parent_execution_id = script_data.get("parent_execution_id")
        plan_scripts = script_data.get("plan_scripts", [])

        if parent_execution_id and plan_scripts:
            if parent_execution_id not in self.plan_executions:
                plan_name = script_data.get("plan_name", "未知计划")
                execution_mode = script_data.get("execution_mode", "parallel")

                self.plan_executions[parent_execution_id] = {
                    "plan_name": plan_name,
                    "execution_mode": execution_mode,
                    "scripts": []
                }
                # 初始化所有脚本状态
                for idx, script in enumerate(plan_scripts):
                    self.plan_executions[parent_execution_id]["scripts"].append({
                        "id": script.get("id"),
                        "name": script.get("name"),
                        "status": "waiting",
                        "index": idx
                    })
            else:
                # 更新当前脚本状态为 running
                script_index = script_data.get("script_index", -1)
                if 0 <= script_index < len(self.plan_executions[parent_execution_id]["scripts"]):
                    old_status = self.plan_executions[parent_execution_id]["scripts"][script_index]["status"]
                    self.plan_executions[parent_execution_id]["scripts"][script_index]["status"] = "running"
                    script_name = self.plan_executions[parent_execution_id]['scripts'][script_index]['name']

        # 初始化结果变量
        result = None

        # 每个线程创建自己的 executor 实例（避免并发冲突）
        executor = None

        try:
            # 【修复】在启动浏览器之前，检查父执行是否已被停止
            if parent_execution_id:
                # 先检查本地缓存的停止列表
                with self._stopped_executions_lock:
                    if parent_execution_id in self._stopped_executions_list:
                        logger.info(f"任务 {task_id}: 父执行 {parent_execution_id} 已停止（本地缓存），不执行此任务")
                        result = {
                            "success": False,
                            "message": "父执行已被用户停止",
                            "cancelled": True
                        }
                        self.cancelled_tasks.add(task_id)
                        raise Exception("父执行已被停止")

                # 再向后端查询父执行状态
                if not self._check_parent_execution_status(parent_execution_id):
                    logger.info(f"任务 {task_id}: 父执行 {parent_execution_id} 已停止（后端查询），加入停止列表并停止")
                    # 将父执行ID加入停止列表，这样后续任务也会被停止
                    with self._stopped_executions_lock:
                        if parent_execution_id not in self._stopped_executions_list:
                            self._stopped_executions_list.append(parent_execution_id)
                            # 限制缓存大小
                            if len(self._stopped_executions_list) > self._stopped_cache_max_size:
                                self._stopped_executions_list.pop(0)
                    result = {
                        "success": False,
                        "message": "父执行已被用户停止",
                        "cancelled": True
                    }
                    self.cancelled_tasks.add(task_id)
                    raise Exception("父执行已被停止")

            # 检查任务是否已被取消
            if task_id in self.cancelled_tasks:
                raise Exception("任务已被取消")

            # 启动浏览器
            logger.info(f"任务 {task_id}: 正在启动 {browser_type} 浏览器...")
            executor = ScriptExecutor()
            if not executor.start(browser_type):
                raise Exception("浏览器启动失败")

            logger.info(f"任务 {task_id}: 浏览器启动成功")

            # 执行脚本
            result = self._execute_script(task_id, script_data, variables, executor)

            # 构建日志数据
            logs = []
            for step_result in result.get("steps", []):
                log_entry = {
                    "step": step_result.get("step_index", 0) + 1,
                    "level": "INFO" if step_result.get("success") else "ERROR",
                    "message": step_result.get("message", ""),
                    "timestamp": time.strftime("%H:%M:%S")
                }
                logs.append(log_entry)

            # 上报结果到平台
            self._send_task_result(task_id, {
                "status": "completed" if result["success"] else "failed",
                "message": result["message"],
                "steps": result.get("steps", []),
                "duration": result.get("duration", 0),
                "logs": logs
            })

            if result["success"]:
                logger.info(f"任务 {task_id} 执行成功")
            else:
                logger.error(f"任务 {task_id} 执行失败: {result['message']}")

        except Exception as e:
            logger.exception(f"任务 {task_id} 执行异常")
            error_msg = f"执行异常: {str(e)}"

            # 上报失败结果
            self._send_task_result(task_id, {
                "status": "failed",
                "message": error_msg,
                "error": traceback.format_exc()
            })

        finally:
            # 关闭浏览器（使用局部 executor 变量）
            if executor:
                try:
                    executor.stop()
                except:
                    pass

            # 获取任务信息，用于检查是否有等待的任务
            task_info = self.running_tasks.get(task_id, {})
            script_data = task_info.get("script_data", {})
            parent_execution_id = script_data.get("parent_execution_id")
            script_index = script_data.get("script_index", -1)

            # 清理任务
            self.running_tasks.pop(task_id, None)
            self.cancelled_tasks.discard(task_id)

            # 确定最终状态
            if result is not None:
                final_status = "completed" if result.get("success", False) else "failed"
                final_message = result.get("message", "")
            else:
                final_status = "failed"
                final_message = "执行失败"

            # 【修复】更新 plan_executions 中的脚本状态，保留历史记录（到退出时才清空）
            if parent_execution_id and parent_execution_id in self.plan_executions:
                with self._plan_executions_lock:
                    if 0 <= script_index < len(self.plan_executions[parent_execution_id]["scripts"]):
                        old_status = self.plan_executions[parent_execution_id]["scripts"][script_index]["status"]
                        self.plan_executions[parent_execution_id]["scripts"][script_index]["status"] = final_status
                        self.plan_executions[parent_execution_id]["scripts"][script_index]["completed_at"] = time.strftime("%H:%M:%S")
                        logger.info(f"任务完成后更新脚本状态: index={script_index}, {old_status} -> {final_status}")

                    # 检查是否所有脚本都已完成，如果是则添加计划完成时间
                    all_finished = True
                    for script_info in self.plan_executions[parent_execution_id]["scripts"]:
                        if script_info["status"] in ["waiting", "running"]:
                            all_finished = False
                            break

                    if all_finished:
                        # 所有脚本完成，添加计划完成时间，保留历史记录
                        self.plan_executions[parent_execution_id]["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        logger.info(f"父执行 {parent_execution_id} 所有脚本已完成，保留历史记录（退出时清空）")

            # 【关键修复】检查并触发等待队列中的下一个任务
            if parent_execution_id:
                logger.info(f"任务 {task_id} 完成，parent_id={parent_execution_id}，检查等待队列")
                self._process_sequential_queue(parent_execution_id)

            # 调用任务完成回调
            if self.on_task_complete:
                try:
                    self.on_task_complete(task_id, final_status, final_message)
                except Exception as e:
                    logger.error(f"任务完成回调失败: {e}")

            logger.info(f"任务结束: {task_id}")

    def _execute_script(
        self,
        task_id: str,
        script_data: Dict[str, Any],
        variables: Dict[str, Any],
        executor: ScriptExecutor
    ) -> Dict[str, Any]:
        """
        执行脚本

        Args:
            task_id: 任务ID
            script_data: 脚本数据
            variables: 变量字典
            executor: ScriptExecutor 实例（每个线程独立）

        Returns:
            执行结果
        """
        steps = script_data.get("steps", [])
        script_name = script_data.get("name", "未命名脚本")
        execution_id = script_data.get("execution_id", "")
        parent_execution_id = script_data.get("parent_execution_id")

        logger.info(f"任务 {task_id}: 脚本 '{script_name}' 共有 {len(steps)} 个步骤")

        # 【修复】在执行任何步骤之前，先检查父执行是否已被停止
        # 这是为了处理以下场景：
        # 1. 任务在停止之前通过了并发检查，线程已启动
        # 2. 用户点击停止
        # 3. 当有任务完成时，这个任务的线程继续执行
        if parent_execution_id:
            # 先检查本地缓存
            with self._stopped_executions_lock:
                if parent_execution_id in self._stopped_executions_list:
                    logger.info(f"任务 {task_id}: 父执行 {parent_execution_id} 已停止（本地缓存），不执行脚本")
                    return {
                        "success": False,
                        "message": "父执行已被用户停止",
                        "steps": [],
                        "cancelled": True
                    }

            # 再向后端查询
            if not self._check_parent_execution_status(parent_execution_id):
                logger.info(f"任务 {task_id}: 父执行 {parent_execution_id} 已停止（后端查询），不执行脚本")
                with self._stopped_executions_lock:
                    if parent_execution_id not in self._stopped_executions_list:
                        self._stopped_executions_list.append(parent_execution_id)
                        # 限制缓存大小
                        if len(self._stopped_executions_list) > self._stopped_cache_max_size:
                            self._stopped_executions_list.pop(0)
                return {
                    "success": False,
                    "message": "父执行已被用户停止",
                    "steps": [],
                    "cancelled": True
                }

        results = []
        all_success = True
        import time
        start_time = time.time()

        for index, step in enumerate(steps):
            # 【关键修复】检查任务是否被取消
            if task_id in self.cancelled_tasks:
                logger.info(f"任务 {task_id} 已被取消（本地标记）")
                return {
                    "success": False,
                    "message": "任务已被取消",
                    "steps": results,
                    "cancelled": True
                }

            # 【关键修复】定期检查后端状态，确认任务是否仍然有效
            # 每隔几个步骤检查一次，避免频繁请求
            if index % 3 == 0:  # 每3个步骤检查一次
                if not self._check_execution_status(execution_id, parent_execution_id):
                    logger.info(f"任务 {task_id} 已被后端停止")
                    # 将任务添加到取消集合
                    self.cancelled_tasks.add(task_id)
                    return {
                        "success": False,
                        "message": "任务已被用户停止",
                        "steps": results,
                        "cancelled": True
                    }

            step_name = step.get("name", f"步骤{index + 1}")
            step_type = step.get("type", "")
            step_start_time = time.time()

            logger.info(f"任务 {task_id}: 执行步骤 {index + 1}/{len(steps)}: {step_name} ({step_type})")

            # 执行步骤
            step_result = executor.step_executor.execute(step, variables)

            # 计算步骤耗时（毫秒）
            step_duration = round((time.time() - step_start_time) * 1000, 2)

            # 添加步骤详细信息
            step_result["name"] = step_name
            step_result["type"] = step_type
            step_result["duration"] = step_duration
            step_result["step_index"] = index

            results.append(step_result)

            # 发送步骤日志
            if step_result["success"]:
                logger.info(f"任务 {task_id}: 步骤成功: {step_name} (耗时: {step_duration}ms)")
            else:
                logger.error(f"任务 {task_id}: 步骤失败: {step_name} - {step_result.get('message', 'Unknown error')}")

                # 失败立即上传截图
                if "screenshot" in step_result and step_result["screenshot"]:
                    self._send_screenshot(task_id, step_result["screenshot"], is_failure=True)

                all_success = False
                break

        end_time = time.time()
        duration = end_time - start_time

        if all_success:
            return {
                "success": True,
                "message": "脚本执行成功",
                "steps": results,
                "duration": round(duration, 2)
            }
        else:
            return {
                "success": False,
                "message": "脚本执行失败",
                "steps": results,
                "duration": round(duration, 2)
            }

    def _send_task_result(self, task_id: str, result: Dict[str, Any]):
        """发送任务执行结果到平台"""
        try:
            import json
            api_base = self.config.server_url.rstrip('/')
            result_url = f"{api_base}/api/tasks/{task_id}/result/"

            # 【关键修复】后端期望的是 status 字段 ('completed'/'failed')，不是 success 字段
            # 将 success: True/False 转换为 status: 'completed'/'failed'
            if "success" in result:
                is_success = result.pop("success")
                result["status"] = "completed" if is_success else "failed"

            # 清理数据：从步骤中移除截图数据（截图已单独发送）
            # 截图数据会导致 JSON 解析错误或数据过大
            if "steps" in result:
                # 创建新的 steps 列表，避免修改原始数据
                cleaned_steps = []
                for step in result["steps"]:
                    cleaned_step = {}
                    for key, value in step.items():
                        # 只保留需要的字段，确保值是 JSON 可序列化的
                        if key in ["name", "type", "success", "message", "duration", "step_index"]:
                            # 确保字符串值中的特殊字符被正确处理
                            if isinstance(value, str):
                                # 移除可能导致 JSON 解析错误的控制字符
                                cleaned_step[key] = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
                            else:
                                cleaned_step[key] = value
                    cleaned_steps.append(cleaned_step)
                result["steps"] = cleaned_steps

            # 移除其他可能有问题的字段
            result.pop("error", None)
            result.pop("logs", None)  # logs 可能包含特殊字符

            # 使用 default=str 处理非序列化对象，让 json.dumps 自动处理转义
            try:
                json_data = json.dumps(result, ensure_ascii=False, default=str)
            except Exception as e:
                logger.error(f"JSON 序列化失败: {e}")
                # 降级：只发送基本信息
                simple_result = {
                    "status": result.get("status", "failed"),
                    "message": "JSON序列化失败",
                    "duration": result.get("duration", 0)
                }
                json_data = json.dumps(simple_result, ensure_ascii=False)

            # 调试：打印完整 JSON 数据
            # 【关键修复】使用 json 参数而不是 data 参数
            # requests 库会自动设置正确的 Content-Length 和 Content-Type 头
            # 避免 JSON 数据在传输过程中被截断
            response = requests.post(
                result_url,
                json=result,  # 直接传入字典，让 requests 自动序列化
                verify=False,  # 跳过 SSL 验证
                timeout=10
            )

            # 检查响应状态码
            if response.status_code == 200:
                logger.info(f"任务结果已上报: {task_id}")

                # 主动请求后端分发新任务（确保并发任务能立即开始）
                try:
                    distribute_url = f"{api_base}/api/tasks/distribute/"
                    dist_response = requests.post(
                        distribute_url,
                        json={},
                        headers={'Content-Type': 'application/json; charset=utf-8'}, verify=False, timeout=5
                    )
                    if dist_response.status_code == 200:
                        logger.info(f"已请求后端分发新任务")
                    else:
                        logger.warning(f"请求分发失败: HTTP {dist_response.status_code}")
                except Exception as dist_e:
                    logger.warning(f"请求分发异常: {dist_e}")
            else:
                logger.error(f"上报任务结果失败: {task_id}, HTTP {response.status_code}")
                logger.error(f"响应内容: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"上报任务结果网络失败: {task_id}, {e}")
        except Exception as e:
            logger.error(f"上报任务结果失败: {task_id}, {e}")

    def _process_sequential_queue(self, parent_execution_id: str):
        """
        处理顺序执行队列，触发下一个任务

        Args:
            parent_execution_id: 父执行ID
        """
        # 【修复】只有在没有同父任务正在运行时才触发下一个任务
        # 这确保了顺序执行：一次只运行一个同父执行的任务

        # 首先检查并发限制（注意：当前任务刚完成，所以有一个空位）
        current_tasks = len(self.running_tasks)
        if current_tasks >= self.config.max_concurrent:
            logger.debug(f"达到最大并发数 ({self.config.max_concurrent})，不触发等待队列中的任务")
            return

        # 检查是否还有同父任务正在运行（排除刚刚完成的任务）
        has_running_sibling = False
        for task_id, task_info in self.running_tasks.items():
            script_data = task_info.get("script_data", {})
            running_parent_id = script_data.get("parent_execution_id")
            if running_parent_id == parent_execution_id:
                has_running_sibling = True
                break

        if has_running_sibling:
            # 还有同父任务正在运行，不触发下一个任务
            logger.debug(f"父执行 {parent_execution_id} 仍有任务正在运行，不触发等待队列中的任务")
            return

        # 没有同父任务正在运行，可以从等待队列中取下一个任务
        next_task_data = None
        next_task_id = None

        with self._wait_lock:
            if parent_execution_id in self._sequential_wait_queue:
                wait_queue = self._sequential_wait_queue[parent_execution_id]
                if wait_queue:
                    # 获取下一个等待的任务
                    next_task_data = wait_queue.pop(0)
                    next_task_id = next_task_data.get("task_id", "")

                    # 如果队列为空，删除队列
                    if not wait_queue:
                        del self._sequential_wait_queue[parent_execution_id]

        # 在锁外执行任务，避免持有锁的时间过长
        if next_task_data:
            logger.info(f"从等待队列中取下一个任务: {next_task_id}")

            # 在执行之前，先将任务加入 running_tasks，防止并发问题
            self.running_tasks[next_task_id] = {
                "execution_id": next_task_data.get("execution_id"),
                "script_name": next_task_data.get("script_data", {}).get("name", "未命名脚本"),
                "status": "running",
                "script_data": next_task_data.get("script_data", {})
            }

            # 在新线程中执行下一个任务
            thread = threading.Thread(
                target=self._execute_task_thread,
                args=(next_task_data,),
                daemon=True,
                name=f"Task-{next_task_id}"
            )
            thread.start()

    def _send_screenshot(self, task_id: str, image_data: str, is_failure: bool = True):
        """发送截图到平台"""
        try:
            api_base = self.config.server_url.rstrip('/')
            screenshot_url = f"{api_base}/api/tasks/{task_id}/screenshot/"

            # 【关键修复】使用 json 参数，requests 会自动处理序列化和 Content-Length
            requests.post(
                screenshot_url,
                json={
                    "image_data": image_data,
                    "is_failure": is_failure
                }, verify=False, timeout=10
            )
            logger.info(f"截图已上报: {task_id}")

        except Exception as e:
            logger.error(f"上报截图失败: {e}")

    def on_mq_connected(self):
        """消息队列连接成功回调"""
        logger.info("消息队列已连接")

    def on_mq_disconnected(self):
        """消息队列断开连接回调"""
        logger.warning("消息队列已断开")

    def on_mq_error(self, error):
        """消息队列错误回调"""
        logger.error(f"消息队列错误: {error}")

    def disconnect(self):
        """断开连接"""
        logger.info("正在断开连接...")

        # 停止心跳
        self._is_heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

        # 停止消息队列消费者
        self.mq_consumer.stop()

        # 取消所有正在执行的任务
        for task_id in list(self.running_tasks.keys()):
            self.cancelled_tasks.add(task_id)

        # 清理所有缓存，包括历史记录
        self.running_tasks.clear()
        self.cancelled_tasks.clear()
        with self._stopped_executions_lock:
            self._stopped_executions_list.clear()
        with self._wait_lock:
            self._sequential_wait_queue.clear()
        with self._plan_executions_lock:
            self.plan_executions.clear()

        logger.info("任务管理器已断开连接并清空所有缓存和历史记录")


# 单例
_task_manager_v2: Optional[TaskManagerV2] = None


def get_task_manager_v2() -> TaskManagerV2:
    """获取任务管理器 V2 单例"""
    global _task_manager_v2
    if _task_manager_v2 is None:
        _task_manager_v2 = TaskManagerV2()
    return _task_manager_v2
