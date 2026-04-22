"""
E2E 测试配置 — conftest.py
提供全局 fixture: 浏览器启动、登录态、Mock LLM 服务、API 客户端
"""
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Generator

import pytest
from playwright.sync_api import Page, BrowserContext, expect

# ============================================================
# 常量
# ============================================================
BASE_URL = "http://localhost:5173"     # 前端地址 (Vite dev server)
API_URL = "http://localhost:8000"      # 后端地址 (Django)

TEST_USERS = {
    "super_admin": {"username": "admin", "password": "admin123"},
    "admin": {"username": "admin2", "password": "admin123"},
    "tester": {"username": "tester1", "password": "test123456"},
    "guest": {"username": "guest1", "password": "guest123456"},
}


# ============================================================
# Mock LLM Server
# ============================================================
MOCK_LLM_RESPONSES = {
    "nl2script": {
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
    },
    "healing": {
        "suggested_locator": "input[name='wd']",
        "locator_type": "css",
        "confidence": 0.92,
        "reason": "原定位器 #kw 已失效，通过 DOM 分析发现 input[name='wd'] 功能等价",
        "strategy": "dom_analysis",
    },
}


class MockLLMHandler(BaseHTTPRequestHandler):
    """Mock HTTP Server — 模拟 OpenAI 兼容接口"""

    def do_POST(self):
        if "/chat/completions" in self.path:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            content = self._pick_response(body)
            response = {
                "id": "mock-response-id",
                "object": "chat.completion",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": json.dumps(content, ensure_ascii=False)},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
                "model": "mock-model",
            }
            self._json_response(200, response)
        else:
            self._json_response(404, {"error": "not found"})

    def _pick_response(self, body: dict):
        messages = body.get("messages", [])
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        if "NL2Script" in system_msg or "nl2script" in system_msg.lower():
            return MOCK_LLM_RESPONSES["nl2script"]
        if "heal" in system_msg.lower() or "自愈" in system_msg:
            return MOCK_LLM_RESPONSES["healing"]
        return MOCK_LLM_RESPONSES["nl2script"]

    def _json_response(self, code: int, data: dict):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass  # 静默日志


@pytest.fixture(scope="session")
def mock_llm_server():
    """启动 Mock LLM 服务，返回 (host, port)"""
    server = HTTPServer(("127.0.0.1", 0), MockLLMHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


# ============================================================
# Playwright 浏览器 Fixture
# ============================================================
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "ignore_https_errors": True,
        "base_url": BASE_URL,
    }


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Page:
    """已登录 admin 的页面 (POM 层使用)"""
    from pages.login_page import LoginPage
    login = LoginPage(page)
    login.goto()
    login.login("admin", "admin123")
    login.wait_for_redirect()
    return page


@pytest.fixture(scope="function")
def tester_page(page: Page) -> Page:
    """已登录 tester1 的页面"""
    from pages.login_page import LoginPage
    login = LoginPage(page)
    login.goto()
    login.login("tester1", "test123456")
    login.wait_for_redirect()
    return page


@pytest.fixture(scope="function")
def guest_page(page: Page) -> Page:
    """已登录 guest1 的页面"""
    from pages.login_page import LoginPage
    login = LoginPage(page)
    login.goto()
    login.login("guest1", "guest123456")
    login.wait_for_redirect()
    return page


# ============================================================
# API 客户端 Fixture
# ============================================================
@pytest.fixture(scope="session")
def api_token():
    """获取 admin 的 API Token"""
    import requests
    resp = requests.post(
        f"{API_URL}/api/auth/login/",
        json=TEST_USERS["super_admin"],
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="session")
def api_client(api_token):
    """带认证的 requests Session"""
    import requests
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
    })
    session.base_url = f"{API_URL}/api"
    return session


@pytest.fixture(scope="function")
def test_project(api_client):
    """创建并返回一个测试项目，测试结束后删除"""
    resp = api_client.post(f"{api_client.base_url}/projects/",
                           json={"name": f"E2E测试项目_{int(time.time())}", "type": "web"})
    assert resp.status_code == 201
    project = resp.json()
    yield project
    api_client.delete(f"{api_client.base_url}/projects/{project['id']}/")


@pytest.fixture(scope="function")
def test_script(api_client, test_project):
    """创建并返回一个测试脚本，测试结束后删除"""
    payload = {
        "name": f"E2E测试脚本_{int(time.time())}",
        "project": test_project["id"],
        "type": "web",
        "framework": "playwright",
        "steps": [
            {"type": "goto", "name": "打开页面", "params": {"value": "https://example.com"}},
        ],
    }
    resp = api_client.post(f"{api_client.base_url}/scripts/", json=payload)
    assert resp.status_code == 201
    script = resp.json()
    yield script
    api_client.delete(f"{api_client.base_url}/scripts/{script['id']}/")
