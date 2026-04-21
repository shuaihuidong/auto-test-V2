"""
Mock 策略: Docker 执行器的心跳与结果回调
模拟执行器注册、心跳上报、任务接取、结果回传的完整生命周期。
无需真实 Docker 容器。
"""
import json
import time
import threading
from typing import Optional
from unittest.mock import MagicMock

import requests


class MockExecutor:
    """
    模拟 Docker 容器化执行器的行为。

    能力:
    1. 向平台注册执行器 (POST /api/executor/register/)
    2. 定期发送心跳 (POST /api/executor/heartbeat/)
    3. 接取任务并上报结果 (POST /api/tasks/{id}/result/)
    4. 上传 Trace 文件 (POST /api/tasks/{id}/trace/)

    使用方式:
        executor = MockExecutor(backend_url="http://localhost:8000")
        executor.register("E2E-Mock-Executor")
        executor.start_heartbeat()  # 后台线程每 30s 上报
        # ... 触发测试任务 ...
        executor.simulate_task_complete(task_id, status="completed")
        executor.stop_heartbeat()
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.executor_uuid: Optional[str] = None
        self.executor_id: Optional[int] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False

    def register(self, name: str = "Mock-Executor") -> dict:
        """注册执行器"""
        resp = requests.post(
            f"{self.backend_url}/api/executor/register/",
            json={
                "name": name,
                "platform": "linux",
                "max_concurrent": 2,
                "hostname": "mock-executor",
            },
            timeout=10,
        )
        data = resp.json()
        self.executor_uuid = data.get("uuid") or data.get("executor_uuid")
        self.executor_id = data.get("id")
        return data

    def send_heartbeat(self) -> dict:
        """发送一次心跳"""
        resp = requests.post(
            f"{self.backend_url}/api/executor/heartbeat/",
            json={
                "executor_uuid": self.executor_uuid,
                "cpu_usage": 25.0,
                "memory_usage": 40.0,
                "disk_usage": 30.0,
                "current_tasks": 0,
                "max_concurrent": 2,
            },
            timeout=10,
        )
        return resp.json()

    def start_heartbeat(self, interval: int = 30):
        """启动后台心跳线程"""
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval,),
            daemon=True,
        )
        self._heartbeat_thread.start()

    def stop_heartbeat(self):
        """停止心跳线程"""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

    def _heartbeat_loop(self, interval: int):
        while self._heartbeat_running:
            try:
                self.send_heartbeat()
            except Exception:
                pass
            time.sleep(interval)

    def get_pending_tasks(self, api_token: str) -> list:
        """获取待执行任务列表"""
        resp = requests.get(
            f"{self.backend_url}/api/tasks/pending/",
            headers={"Authorization": f"Token {api_token}"},
            timeout=10,
        )
        data = resp.json()
        return data if isinstance(data, list) else data.get("results", [])

    def simulate_task_complete(self, task_id: int, api_token: str,
                                status: str = "completed",
                                steps_results: list = None) -> dict:
        """模拟任务完成，上报结果"""
        if steps_results is None:
            steps_results = [
                {"step_index": 0, "status": "pass", "duration": 1500, "screenshot": None},
            ]

        resp = requests.post(
            f"{self.backend_url}/api/tasks/{task_id}/result/",
            json={
                "status": status,
                "steps_results": steps_results,
                "duration": sum(s.get("duration", 0) for s in steps_results),
            },
            headers={"Authorization": f"Token {api_token}"},
            timeout=10,
        )
        return resp.json()

    def simulate_task_failed(self, task_id: int, api_token: str,
                              error_message: str = "Element not found") -> dict:
        """模拟任务失败"""
        return self.simulate_task_complete(
            task_id=task_id,
            api_token=api_token,
            status="failed",
            steps_results=[
                {"step_index": 0, "status": "fail", "error": error_message, "duration": 500},
            ],
        )

    def upload_trace(self, task_id: int, api_token: str,
                     trace_data: bytes = b"mock-trace-data") -> dict:
        """上传 Trace 文件"""
        import io
        resp = requests.post(
            f"{self.backend_url}/api/tasks/{task_id}/trace/",
            files={"file": ("trace.zip", io.BytesIO(trace_data), "application/zip")},
            headers={"Authorization": f"Token {api_token}"},
            timeout=10,
        )
        return resp.json()


# ============================================================
# Fixture 用法示例 (添加到 conftest.py):
# ============================================================
#
# @pytest.fixture(scope="function")
# def mock_executor(api_token):
#     executor = MockExecutor(backend_url=API_URL)
#     executor.register("E2E-Mock-Executor")
#     executor.start_heartbeat()
#     yield executor
#     executor.stop_heartbeat()
#
# 使用示例:
# def test_full_execution_flow(api_client, mock_executor, test_script, api_token):
#     # 触发执行
#     resp = api_client.post(f"{api_client.base_url}/executions/",
#                            json={"script_id": test_script["id"]})
#     execution_id = resp.json()["id"]
#
#     # 模拟执行器接取并完成
#     tasks = mock_executor.get_pending_tasks(api_token)
#     if tasks:
#         mock_executor.simulate_task_complete(tasks[0]["id"], api_token)
#
#     # 验证状态
#     resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/")
#     assert resp.json()["status"] == "completed"
