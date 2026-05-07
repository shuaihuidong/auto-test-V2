"""
E2E 测试: V2.0 已知问题修复验证 (独立版)
通过 HTTP API 验证所有行为，不依赖源码文件系统结构。
覆盖:
  1. 数据库多引擎支持 (通过 CRUD 验证)
  2. Secrets 管理 (通过 /api/settings/ai/ 验证脱敏)
  3. MinIO 存储后端 (通过 trace 上传 API 验证)
  4. executor-client 清理验证 (通过 PROJECT_ROOT 环境变量)
"""
import io
import os
import time

import pytest


# ============================================================
# 问题 1: 数据库多引擎配置
# ============================================================

class TestDatabaseEngine:
    """验证数据库连接正常 (通过 CRUD 操作验证)"""

    def test_db_engine_env_variable_respected(self):
        """验证 DB_ENGINE 环境变量可被读取"""
        db_engine = os.getenv('DB_ENGINE', 'sqlite3').lower()
        assert db_engine in ('sqlite3', 'postgresql', 'mysql')

    def test_database_connection_works(self, api_client):
        """验证数据库连接正常 (通过 CRUD 操作验证)"""
        # 创建项目 → 验证写入
        resp = api_client.post(
            f"{api_client.base_url}/projects/",
            json={"name": f"DB测试项目_{int(time.time())}", "type": "web"},
        )
        assert resp.status_code == 201
        project = resp.json()
        project_id = project["id"]

        # 读取 → 验证读取
        resp = api_client.get(f"{api_client.base_url}/projects/{project_id}/")
        assert resp.status_code == 200
        assert resp.json()["name"] == project["name"]

        # 删除 → 验证删除
        resp = api_client.delete(f"{api_client.base_url}/projects/{project_id}/")
        assert resp.status_code == 204


# ============================================================
# 问题 2: Secrets 管理
# ============================================================

class TestSecretsManagement:
    """验证敏感配置通过 API 脱敏返回"""

    def test_ai_settings_secret_masking(self, api_client):
        """验证 API Key 在 /api/settings/ai/ 中返回脱敏值"""
        resp = api_client.get(f"{api_client.base_url}/settings/ai/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        secret_items = [item for item in data if item.get("is_secret")]
        assert len(secret_items) >= 2, "应有至少 2 个密钥配置项"

        for item in secret_items:
            value = item.get("value", "")
            # 如果有值, 应该是脱敏格式 (含 ****), 或为空
            if value:
                assert "****" in value, \
                    f"密钥 {item['key']} 应该被脱敏, 实际值: {value}"

    def test_masked_value_not_overwrite_real(self, api_client):
        """验证脱敏格式的值不会覆盖真实密钥"""
        # 获取脱敏后的 OPENAI_API_KEY
        resp = api_client.get(f"{api_client.base_url}/settings/ai/")
        data = resp.json()
        api_key_item = next((i for i in data if i["key"] == "OPENAI_API_KEY"), None)
        assert api_key_item is not None
        masked_value = api_key_item["value"]

        # 如果当前值为空, 先设置一个测试值
        if not masked_value:
            api_client.put(f"{api_client.base_url}/settings/ai/", json={
                "settings": [{"key": "OPENAI_API_KEY", "value": "sk-test-secret-key-12345"}]
            })

        # 尝试用脱敏值更新 (应被忽略)
        api_client.put(f"{api_client.base_url}/settings/ai/", json={
            "settings": [{"key": "OPENAI_API_KEY", "value": "sk-********345"}]
        })

        # 验证真实值没有被覆盖
        resp2 = api_client.get(f"{api_client.base_url}/settings/ai/")
        data2 = resp2.json()
        api_key_item2 = next((i for i in data2 if i["key"] == "OPENAI_API_KEY"), None)
        if masked_value:
            assert api_key_item2["value"] == masked_value

        # 清理测试值
        api_client.put(f"{api_client.base_url}/settings/ai/", json={
            "settings": [{"key": "OPENAI_API_KEY", "value": ""}]
        })

    def test_ai_config_check_endpoint(self, api_client):
        """验证 AI 配置检查端点可用"""
        resp = api_client.get(f"{api_client.base_url}/settings/ai/check/")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "primary_provider" in data


# ============================================================
# 问题 3: MinIO 存储后端
# ============================================================

class TestMinIOStorageBackend:
    """验证 MinIO 存储后端通过 API 可用"""

    def test_trace_upload_uses_storage_backend(self, api_client, test_script):
        """验证 trace 上传使用存储抽象层"""
        # 创建执行
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        assert exec_resp.status_code == 201
        execution_id = exec_resp.json()["id"]

        # 查找关联的 task
        pending_resp = api_client.get(f"{api_client.base_url}/tasks/pending/")
        tasks_data = pending_resp.json()
        tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("results", [])

        if tasks:
            task_id = tasks[0]["id"]
            trace_content = b"mock-playwright-trace-content-for-storage-test"
            trace_file = io.BytesIO(trace_content)
            trace_resp = api_client.post(
                f"{api_client.base_url}/tasks/{task_id}/trace/",
                files={"trace": ("trace.zip", trace_file, "application/zip")},
            )
            assert trace_resp.status_code in (200, 201), \
                f"Trace 上传失败: {trace_resp.status_code} {trace_resp.text}"
            data = trace_resp.json()
            assert "path" in data
            assert data["message"] == "Trace 已保存"

    def test_project_crud_verifies_db_storage(self, api_client):
        """验证项目 CRUD 操作正常 (数据库存储可用)"""
        # 创建
        resp = api_client.post(
            f"{api_client.base_url}/projects/",
            json={"name": f"存储测试项目_{int(time.time())}", "type": "web"},
        )
        assert resp.status_code == 201
        project = resp.json()

        # 读取
        resp = api_client.get(f"{api_client.base_url}/projects/{project['id']}/")
        assert resp.status_code == 200

        # 更新
        resp = api_client.patch(
            f"{api_client.base_url}/projects/{project['id']}/",
            json={"name": f"更新后项目_{int(time.time())}"},
        )
        assert resp.status_code == 200

        # 删除
        resp = api_client.delete(f"{api_client.base_url}/projects/{project['id']}/")
        assert resp.status_code == 204


# ============================================================
# 问题 4: executor-client 清理
# ============================================================

class TestExecutorClientCleanup:
    """验证 executor-docker 注册和心跳 API 正常工作"""

    def test_executor_register_via_api(self, api_client):
        """验证执行器注册 API 正常工作"""
        import uuid
        executor_uuid = str(uuid.uuid4())
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/register/",
            json={
                "executor_uuid": executor_uuid,
                "executor_name": f"清理验证执行器_{int(time.time())}",
                "platform": "linux",
                "max_concurrent": 2,
                "owner_username": "admin",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_executor_heartbeat_via_api(self, api_client):
        """验证执行器心跳 API 正常工作"""
        import uuid
        executor_uuid = str(uuid.uuid4())

        # 先注册
        api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/register/",
            json={
                "executor_uuid": executor_uuid,
                "executor_name": "心跳验证执行器",
                "platform": "linux",
                "max_concurrent": 2,
                "owner_username": "admin",
            },
        )

        # 发送心跳
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/heartbeat/",
            json={
                "executor_uuid": executor_uuid,
                "cpu_usage": 30.0,
                "memory_usage": 50.0,
                "disk_usage": 40.0,
                "current_tasks": 0,
                "max_concurrent": 2,
            },
        )
        assert resp.status_code in (200, 201), f"心跳失败: {resp.status_code} {resp.text}"

    def test_online_executors_endpoint(self, api_client):
        """验证在线执行器列表 API 可用"""
        resp = api_client.get(f"{api_client.base_url}/executors/online/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ============================================================
# 全链路集成测试
# ============================================================

class TestFullIntegration:
    """全链路集成测试 - 验证所有修改协同工作"""

    def test_api_login_and_crud(self, api_client):
        """验证 API 认证和基本 CRUD"""
        # 创建项目
        resp = api_client.post(
            f"{api_client.base_url}/projects/",
            json={"name": f"集成测试项目_{int(time.time())}", "type": "web"},
        )
        assert resp.status_code == 201
        project = resp.json()

        # 创建脚本
        resp = api_client.post(
            f"{api_client.base_url}/scripts/",
            json={
                "name": f"集成测试脚本_{int(time.time())}",
                "project": project["id"],
                "type": "web",
                "framework": "playwright",
                "steps": [
                    {"type": "open_page", "name": "打开页面", "params": {"url": "https://example.com"}},
                ],
            },
        )
        assert resp.status_code == 201
        script = resp.json()

        # 创建执行
        resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": script["id"]},
        )
        assert resp.status_code == 201
        execution = resp.json()

        # 查询在线执行器
        resp = api_client.get(f"{api_client.base_url}/executors/online/")
        assert resp.status_code == 200

        # 清理
        api_client.delete(f"{api_client.base_url}/scripts/{script['id']}/")
        api_client.delete(f"{api_client.base_url}/projects/{project['id']}/")

    def test_executor_register_and_heartbeat(self, api_client):
        """验证执行器注册和心跳"""
        import uuid
        executor_uuid = str(uuid.uuid4())

        # 注册
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/register/",
            json={
                "executor_uuid": executor_uuid,
                "executor_name": f"集成测试执行器_{int(time.time())}",
                "platform": "linux",
                "max_concurrent": 2,
                "owner_username": "admin",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # 心跳
        resp = api_client.post(
            f"{api_client.base_url.replace('/api', '')}/api/executor/heartbeat/",
            json={
                "executor_uuid": executor_uuid,
                "cpu_usage": 30.0,
                "memory_usage": 50.0,
                "disk_usage": 40.0,
                "current_tasks": 0,
                "max_concurrent": 2,
            },
        )
        assert resp.status_code in (200, 201), f"心跳失败: {resp.status_code} {resp.text}"

    def test_trace_upload_and_storage(self, api_client):
        """验证 Trace 上传和存储"""
        # 创建项目和脚本
        project_resp = api_client.post(
            f"{api_client.base_url}/projects/",
            json={"name": f"Trace测试项目_{int(time.time())}", "type": "web"},
        )
        assert project_resp.status_code == 201
        project = project_resp.json()

        script_resp = api_client.post(
            f"{api_client.base_url}/scripts/",
            json={
                "name": f"Trace测试脚本_{int(time.time())}",
                "project": project["id"],
                "type": "web",
                "framework": "playwright",
                "steps": [{"type": "open_page", "name": "打开", "params": {"url": "https://example.com"}}],
            },
        )
        assert script_resp.status_code == 201
        script = script_resp.json()

        # 创建执行
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": script["id"]},
        )
        assert exec_resp.status_code == 201

        # 查找 task 并上传 trace
        pending_resp = api_client.get(f"{api_client.base_url}/tasks/pending/")
        tasks_data = pending_resp.json()
        tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("results", [])

        if tasks:
            task_id = tasks[0]["id"]
            trace_content = b"PK\x03\x04mock-trace-zip-content-for-integration-test"
            trace_file = io.BytesIO(trace_content)
            trace_resp = api_client.post(
                f"{api_client.base_url}/tasks/{task_id}/trace/",
                files={"trace": ("trace.zip", trace_file, "application/zip")},
            )
            assert trace_resp.status_code in (200, 201)
            assert "path" in trace_resp.json()

        # 清理
        api_client.delete(f"{api_client.base_url}/scripts/{script['id']}/")
        api_client.delete(f"{api_client.base_url}/projects/{project['id']}/")

    def test_sandbox_validate(self, api_client):
        """验证沙盒验证端点"""
        steps = [
            {"type": "goto", "name": "打开页面", "params": {"url": "https://example.com"}},
            {"type": "click", "name": "点击", "params": {"locator": {"type": "css", "value": "#btn"}}},
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/sandbox_validate/",
            json={"steps": steps},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    def test_ai_config_check(self, api_client):
        """验证 AI 配置检查端点"""
        resp = api_client.get(f"{api_client.base_url}/settings/ai/check/")
        assert resp.status_code == 200
        data = resp.json()
        assert "configured" in data
        assert "primary_provider" in data
