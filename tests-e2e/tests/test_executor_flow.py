"""
测试用例: 执行器注册、心跳、任务调度全链路 (API-EXC-001 ~ FLOW-RES-003)
通过 Mock 替代真实 RabbitMQ 和 Docker 执行器
"""
import time

import pytest


class TestExecutorRegister:
    """API-EXC-001 ~ API-EXC-004: 执行器注册与心跳"""

    def test_register_executor(self, api_client):
        """API-EXC-001: 注册执行器"""
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/register/",
            json={
                "name": f"E2E执行器_{int(time.time())}",
                "platform": "linux",
                "max_concurrent": 2,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "uuid" in data or "executor_uuid" in data or "id" in data

    def test_heartbeat_report(self, api_client):
        """API-EXC-002: 心跳上报"""
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/heartbeat/",
            json={
                "executor_uuid": "test-uuid-e2e",
                "cpu_usage": 30.0,
                "memory_usage": 50.0,
                "disk_usage": 40.0,
                "current_tasks": 0,
                "max_concurrent": 2,
            },
        )
        assert resp.status_code == 200

    def test_get_online_executors(self, api_client):
        """API-EXC-004: 获取在线执行器列表"""
        resp = api_client.get(f"{api_client.base_url}/executors/online/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestExecutionFlow:
    """FLOW-001 ~ FLOW-004: 执行全链路"""

    def test_create_execution(self, api_client, test_script):
        """FLOW-001 部分: 创建执行记录"""
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] in ("pending", "queued")
        assert "id" in data
        return data["id"]

    def test_execution_status_lifecycle(self, api_client, test_script):
        """FLOW-001: 执行状态生命周期 pending → running → completed"""
        # 创建执行
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = resp.json()["id"]

        # 验证 pending
        resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/")
        assert resp.json()["status"] in ("pending", "queued")

        # 模拟执行器接取任务 → running
        api_client.patch(
            f"{api_client.base_url}/executions/{execution_id}/",
            json={"status": "running"},
        )
        resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/")
        assert resp.json()["status"] == "running"

        # 模拟执行完成
        api_client.patch(
            f"{api_client.base_url}/executions/{execution_id}/",
            json={"status": "completed", "result": "pass"},
        )
        resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/")
        assert resp.json()["status"] == "completed"

    def test_execution_failed(self, api_client, test_script):
        """FLOW-002: 执行失败闭环"""
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = resp.json()["id"]

        # 模拟执行失败
        api_client.patch(
            f"{api_client.base_url}/executions/{execution_id}/",
            json={
                "status": "failed",
                "error_message": "Element not found: #missing-btn",
            },
        )
        resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/")
        assert resp.json()["status"] == "failed"

    def test_stop_execution(self, api_client, test_script):
        """API-EXE-004: 停止执行"""
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = resp.json()["id"]

        # 设为 running 后停止
        api_client.patch(
            f"{api_client.base_url}/executions/{execution_id}/",
            json={"status": "running"},
        )
        stop_resp = api_client.post(
            f"{api_client.base_url}/executions/{execution_id}/stop/"
        )
        assert stop_resp.status_code == 200

    def test_no_executor_queues_task(self, api_client, test_script):
        """FLOW-003: 无执行器时任务排队"""
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] in ("pending", "queued")


class TestTaskResultCallback:
    """FLOW-RES-001 ~ FLOW-RES-003: 结果回传"""

    def test_submit_task_result(self, api_client, test_script):
        """FLOW-RES-001: 上报执行结果"""
        # 创建执行
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = exec_resp.json()["id"]

        # 查找关联的 task
        pending_resp = api_client.get(f"{api_client.base_url}/tasks/pending/")
        tasks = pending_resp.json() if isinstance(pending_resp.json(), list) else pending_resp.json().get("results", [])

        if tasks:
            task_id = tasks[0]["id"]
            # 模拟任务完成上报
            result_resp = api_client.post(
                f"{api_client.base_url}/tasks/{task_id}/result/",
                json={
                    "status": "completed",
                    "steps_results": [
                        {"step_index": 0, "status": "pass", "duration": 1500},
                    ],
                },
            )
            assert result_resp.status_code == 200

    def test_submit_trace(self, api_client, test_script):
        """FLOW-RES-003: 上传 Trace 文件"""
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = exec_resp.json()["id"]

        # 查找 task
        pending_resp = api_client.get(f"{api_client.base_url}/tasks/pending/")
        tasks = pending_resp.json() if isinstance(pending_resp.json(), list) else pending_resp.json().get("results", [])

        if tasks:
            task_id = tasks[0]["id"]
            import io
            trace_file = io.BytesIO(b"mock-trace-zip-content")
            trace_resp = api_client.post(
                f"{api_client.base_url}/tasks/{task_id}/trace/",
                files={"file": ("trace.zip", trace_file, "application/zip")},
            )
            # 可能 200 或 201
            assert trace_resp.status_code in (200, 201)
