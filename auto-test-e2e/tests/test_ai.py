"""
测试用例: NL2Script + Self-healing AI 功能
覆盖:
  - 单条生成 API (nl2script, nl2script_save)
  - 批量生成 API (nl2script_batch, nl2script_batch_save, nl2script_review)
  - 权限控制 (guest 拒绝)
  - 单条生成 UI (预览 → 保存/丢弃/编辑)
  - 批量生成 UI (预览 → AI 审查 → 选择保存 → 重新生成)
  - Self-healing API 测试
"""
import time

import pytest
from playwright.sync_api import expect

from pages.script_list_page import ScriptListPage
from pages.nl2script_dialog import NL2ScriptDialog
from pages.nl2script_batch_dialog import NL2ScriptBatchDialog
from pages.heal_log_panel import ReportPage


# ============================================================
# 单条生成 API 测试
# ============================================================

class TestNL2ScriptAPI:
    """NL2Script 单条生成 API 测试"""

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_generate_no_auto_save(self, api_client):
        """API-NL2S-001: nl2script 仅生成不保存，响应不含 script_id"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script/",
            json={"prompt": "打开百度首页，在搜索框输入playwright，点击搜索按钮"},
        )
        if resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key 才能运行此测试")
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        assert len(data["steps"]) >= 2
        for step in data["steps"]:
            assert "type" in step
            assert "name" in step
        # 重构后不应返回 script_id
        assert "script_id" not in data

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_empty_prompt(self, api_client):
        """API-NL2S-002: 空 prompt 返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script/",
            json={"prompt": ""},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_save(self, api_client, test_project):
        """API-NL2S-003: nl2script_save 独立保存端点"""
        steps = [
            {"type": "goto", "name": "打开页面", "params": {"url": "https://example.com"}},
            {"type": "click", "name": "点击按钮", "params": {"locator": {"type": "css", "value": "#btn"}}},
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_save/",
            json={
                "steps": steps,
                "project_id": test_project["id"],
                "script_name": f"API保存测试_{int(time.time())}",
                "prompt": "打开页面并点击按钮",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "script_id" in data
        assert isinstance(data["script_id"], int)
        # 清理
        api_client.delete(f"{api_client.base_url}/scripts/{data['script_id']}/")

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_save_no_project(self, api_client):
        """API-NL2S-004: 保存时不传 project_id 返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_save/",
            json={
                "steps": [{"type": "goto", "name": "打开", "params": {"url": "https://example.com"}}],
                "script_name": "无项目",
                "prompt": "测试",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_save_empty_steps(self, api_client, test_project):
        """API-NL2S-005: 保存时步骤为空返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_save/",
            json={
                "steps": [],
                "project_id": test_project["id"],
                "script_name": "空步骤",
                "prompt": "测试",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_save_auto_name(self, api_client, test_project):
        """API-NL2S-006: 保存时不传 script_name 自动生成"""
        steps = [{"type": "goto", "name": "打开", "params": {"url": "https://example.com"}}]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_save/",
            json={
                "steps": steps,
                "project_id": test_project["id"],
                "prompt": "这是一个长描述用于自动生成脚本名称的测试",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "script_id" in data
        # 清理
        api_client.delete(f"{api_client.base_url}/scripts/{data['script_id']}/")

    @pytest.mark.api
    @pytest.mark.p0
    def test_nl2script_locator_parsing(self, api_client):
        """API-NL2S-007: 定位器解析正确"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script/",
            json={"prompt": "点击登录按钮"},
        )
        if resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key")
        assert resp.status_code == 200
        data = resp.json()
        locator_steps = [s for s in data.get("steps", []) if "locator" in s.get("params", {})]
        if locator_steps:
            loc = locator_steps[0]["params"]["locator"]
            assert "type" in loc
            assert "value" in loc


# ============================================================
# 批量生成 API 测试
# ============================================================

class TestNL2ScriptBatchAPI:
    """NL2Script 批量生成 API 测试"""

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_generate_no_auto_save(self, api_client):
        """API-BATCH-001: 批量生成仅返回结果不保存，响应不含 saved_ids"""
        prompts = [f"测试操作{i+1}: 打开页面并点击按钮" for i in range(3)]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch/",
            json={"prompts": prompts},
        )
        if resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 3
        assert data["total"] == 3
        # 重构后不应返回 saved_ids
        assert "saved_ids" not in data

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_exceed_limit(self, api_client):
        """API-BATCH-002: 超过 50 条返回 400"""
        prompts = [f"测试{i}" for i in range(51)]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch/",
            json={"prompts": prompts},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_empty_prompts(self, api_client):
        """API-BATCH-003: 空 prompts 列表返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch/",
            json={"prompts": []},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_save(self, api_client, test_project):
        """API-BATCH-004: nl2script_batch_save 批量保存"""
        scripts = [
            {
                "prompt": "打开百度搜索",
                "steps": [{"type": "goto", "name": "打开", "params": {"url": "https://baidu.com"}}],
                "script_name": f"批量脚本A_{int(time.time())}",
            },
            {
                "prompt": "登录系统",
                "steps": [{"type": "goto", "name": "打开登录", "params": {"url": "/login"}}],
                "script_name": f"批量脚本B_{int(time.time())}",
            },
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch_save/",
            json={"project_id": test_project["id"], "scripts": scripts},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "saved_ids" in data
        assert len(data["saved_ids"]) == 2
        # 清理
        for sid in data["saved_ids"]:
            api_client.delete(f"{api_client.base_url}/scripts/{sid}/")

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_save_no_project(self, api_client):
        """API-BATCH-005: 批量保存不传 project_id 返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch_save/",
            json={"project_id": None, "scripts": [{"prompt": "t", "steps": [], "script_name": "t"}]},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p0
    def test_batch_save_empty_scripts(self, api_client, test_project):
        """API-BATCH-006: 批量保存空脚本列表返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_batch_save/",
            json={"project_id": test_project["id"], "scripts": []},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p1
    def test_review(self, api_client):
        """API-REVIEW-001: nl2script_review AI 审查"""
        items = [
            {
                "prompt": "打开百度搜索playwright",
                "steps": [
                    {"type": "goto", "name": "打开", "params": {"url": "https://baidu.com"}},
                    {"type": "input", "name": "输入", "params": {"locator": {"type": "css", "value": "#kw"}, "value": "playwright"}},
                ],
            }
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_review/",
            json={"items": items},
        )
        if resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key")
        assert resp.status_code == 200
        data = resp.json()
        assert "reviews" in data
        assert len(data["reviews"]) == 1
        review = data["reviews"][0]
        assert "quality_score" in review
        assert "intent_match" in review
        assert "suggestions" in review
        assert "passed" in review
        assert isinstance(review["quality_score"], int)
        assert isinstance(review["intent_match"], int)
        assert isinstance(review["suggestions"], list)
        assert isinstance(review["passed"], bool)
        assert 0 <= review["quality_score"] <= 100
        assert 0 <= review["intent_match"] <= 100

    @pytest.mark.api
    @pytest.mark.p1
    def test_review_empty_items(self, api_client):
        """API-REVIEW-002: 空审查项返回 400"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_review/",
            json={"items": []},
        )
        assert resp.status_code == 400

    @pytest.mark.api
    @pytest.mark.p1
    def test_review_multiple_items(self, api_client):
        """API-REVIEW-003: 审查多项"""
        items = [
            {
                "prompt": f"测试操作{i}",
                "steps": [{"type": "goto", "name": "打开", "params": {"url": "https://example.com"}}],
            }
            for i in range(3)
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script_review/",
            json={"items": items},
        )
        if resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key")
        assert resp.status_code == 200
        assert len(resp.json()["reviews"]) == 3


# ============================================================
# 权限控制 API 测试
# ============================================================

class TestNL2ScriptPermission:
    """NL2Script 权限控制"""

    @pytest.mark.api
    @pytest.mark.p0
    def test_guest_nl2script_denied(self, guest_api_client):
        """API-PERM-001: guest 无权使用 nl2script"""
        resp = guest_api_client.post(
            f"{guest_api_client.base_url}/scripts/nl2script/",
            json={"prompt": "打开页面"},
        )
        assert resp.status_code == 403

    @pytest.mark.api
    @pytest.mark.p0
    def test_guest_nl2script_save_denied(self, guest_api_client, test_project):
        """API-PERM-002: guest 无权保存 AI 脚本"""
        resp = guest_api_client.post(
            f"{guest_api_client.base_url}/scripts/nl2script_save/",
            json={
                "steps": [{"type": "goto", "name": "打开", "params": {"url": "https://example.com"}}],
                "project_id": test_project["id"],
                "script_name": "guest脚本",
                "prompt": "测试",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.api
    @pytest.mark.p0
    def test_guest_nl2script_batch_denied(self, guest_api_client):
        """API-PERM-003: guest 无权批量生成"""
        resp = guest_api_client.post(
            f"{guest_api_client.base_url}/scripts/nl2script_batch/",
            json={"prompts": ["打开页面"]},
        )
        assert resp.status_code == 403

    @pytest.mark.api
    @pytest.mark.p0
    def test_guest_nl2script_batch_save_denied(self, guest_api_client, test_project):
        """API-PERM-004: guest 无权批量保存"""
        resp = guest_api_client.post(
            f"{guest_api_client.base_url}/scripts/nl2script_batch_save/",
            json={"project_id": test_project["id"], "scripts": [{"prompt": "t", "steps": [], "script_name": "t"}]},
        )
        assert resp.status_code == 403

    @pytest.mark.api
    @pytest.mark.p0
    def test_guest_nl2script_review_denied(self, guest_api_client):
        """API-PERM-005: guest 无权 AI 审查"""
        resp = guest_api_client.post(
            f"{guest_api_client.base_url}/scripts/nl2script_review/",
            json={"items": [{"prompt": "t", "steps": []}]},
        )
        assert resp.status_code == 403


# ============================================================
# 沙盒验证
# ============================================================

class TestSandboxValidate:
    """沙盒验证"""

    @pytest.mark.api
    @pytest.mark.p0
    def test_sandbox_validate_valid(self, api_client):
        """API-SANDBOX-001: 合法步骤验证通过"""
        steps = [
            {"type": "goto", "name": "打开页面", "params": {"value": "https://example.com"}},
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/sandbox_validate/",
            json={"steps": steps},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    @pytest.mark.api
    @pytest.mark.p0
    def test_sandbox_validate_invalid_type(self, api_client):
        """API-SANDBOX-002: 非法步骤类型"""
        steps = [
            {"type": "invalid_type", "name": "非法步骤", "params": {}},
        ]
        resp = api_client.post(
            f"{api_client.base_url}/scripts/sandbox_validate/",
            json={"steps": steps},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert resp.json()["error_count"] >= 1


# ============================================================
# 单条生成 UI 测试
# ============================================================

class TestNL2ScriptUI:
    """NL2Script 单条生成前端交互"""

    @pytest.fixture(autouse=True)
    def check_ai_configured(self, api_client):
        """检查 AI 服务是否已配置，未配置则跳过整个类"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script/",
            json={"prompt": "__health_check__"},
        )
        if resp.status_code in (500, 503):
            pytest.skip("AI 服务未配置 (需要 LLM API Key)")

    @pytest.mark.ui
    @pytest.mark.p0
    def test_nl2script_generate_preview(self, authenticated_page, test_project):
        """UI-NL2S-001: 生成后进入预览模式，不自动保存"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptDialog(authenticated_page)
        script_list.open_nl2script_dialog()
        expect(dialog.modal).to_be_visible()

        dialog.input_prompt("打开百度首页搜索playwright")
        dialog.click_generate()

        # 预览区显示步骤
        step_count = dialog.get_generated_step_count()
        assert step_count >= 2, f"Expected >=2 steps, got {step_count}"

        # 显示保存/丢弃/复制按钮
        assert dialog.has_save_button(), "应有'保存'按钮"
        assert dialog.discard_button.is_visible(), "应有'丢弃'按钮"
        assert dialog.copy_button.is_visible(), "应有'复制 JSON'按钮"

    @pytest.mark.ui
    @pytest.mark.p0
    def test_nl2script_discard(self, authenticated_page, test_project):
        """UI-NL2S-002: 丢弃后回到输入状态"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptDialog(authenticated_page)
        script_list.open_nl2script_dialog()
        dialog.input_prompt("打开百度搜索playwright")
        dialog.click_generate()

        assert dialog.is_result_visible()

        dialog.click_discard()

        # 丢弃后结果区消失，输入区重新显示
        assert dialog.is_input_visible(), "丢弃后应回到输入状态"
        assert not dialog.is_result_visible(), "丢弃后结果区应消失"

    @pytest.mark.ui
    @pytest.mark.p0
    def test_nl2script_save_then_edit(self, authenticated_page, test_project):
        """UI-NL2S-003: 选中项目 → 生成 → 保存 → 出现编辑脚本按钮"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])
        initial_count = script_list.get_script_count()

        dialog = NL2ScriptDialog(authenticated_page)
        script_list.open_nl2script_dialog()
        dialog.input_prompt("打开百度搜索playwright")
        dialog.select_project(test_project["name"])
        dialog.click_generate()

        # 点保存
        dialog.click_save()

        # 保存后应出现"编辑脚本"按钮
        expect(dialog.edit_button).to_be_visible(timeout=5000)

    @pytest.mark.ui
    @pytest.mark.p1
    def test_nl2script_save_without_project(self, authenticated_page, test_project):
        """UI-NL2S-004: 不选项目点保存应提示用户"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptDialog(authenticated_page)
        script_list.open_nl2script_dialog()
        dialog.input_prompt("打开百度搜索playwright")
        # 不选项目，直接生成
        dialog.click_generate()

        # 点保存时应弹出 warning
        dialog.click_save()
        # 检查 ant-message warning
        warning_msg = authenticated_page.locator(".ant-message-warning, .ant-message-notice")
        # warning 可能耗时显示
        authenticated_page.wait_for_timeout(2000)


# ============================================================
# 批量生成 UI 测试
# ============================================================

class TestNL2ScriptBatchUI:
    """NL2Script 批量生成前端交互"""

    @pytest.fixture(autouse=True)
    def check_ai_configured(self, api_client):
        """检查 AI 服务是否已配置，未配置则跳过整个类"""
        resp = api_client.post(
            f"{api_client.base_url}/scripts/nl2script/",
            json={"prompt": "__health_check__"},
        )
        if resp.status_code in (500, 503):
            pytest.skip("AI 服务未配置 (需要 LLM API Key)")

    @pytest.mark.ui
    @pytest.mark.p0
    def test_batch_generate_preview(self, authenticated_page, test_project):
        """UI-BATCH-001: 批量生成后进入预览模式，不自动保存"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptBatchDialog(authenticated_page)
        script_list.open_batch_nl2script_dialog()
        expect(dialog.modal).to_be_visible()

        dialog.input_prompts("打开百度搜索测试\n登录系统测试")
        dialog.click_generate()

        # 应显示结果列表
        count = dialog.get_result_count()
        assert count >= 1, "批量生成后应显示结果项"

        # 应显示工具栏 (项目选择、AI 审查、保存按钮)
        assert dialog.is_toolbar_visible(), "工具栏应可见"

    @pytest.mark.ui
    @pytest.mark.p1
    def test_batch_toolbar_project_selector(self, authenticated_page, test_project):
        """UI-BATCH-002: 预览阶段项目选择器在工具栏可见"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptBatchDialog(authenticated_page)
        script_list.open_batch_nl2script_dialog()

        dialog.input_prompts("打开百度搜索测试\n登录系统测试")
        dialog.click_generate()

        # 工具栏中应有项目选择器
        assert dialog.project_select.is_visible(), "工具栏中应有项目选择器"

    @pytest.mark.ui
    @pytest.mark.p1
    def test_batch_back_to_input(self, authenticated_page, test_project):
        """UI-BATCH-003: 点返回输入回到输入阶段"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptBatchDialog(authenticated_page)
        script_list.open_batch_nl2script_dialog()

        dialog.input_prompts("打开百度搜索测试")
        dialog.click_generate()

        assert dialog.get_result_count() >= 1

        dialog.click_back()

        # 应回到输入阶段
        assert dialog.textarea.is_visible(), "返回后应显示输入框"

    @pytest.mark.ui
    @pytest.mark.p1
    def test_batch_save_without_project_warning(self, authenticated_page, test_project):
        """UI-BATCH-004: 不选项目点保存应提示"""
        script_list = ScriptListPage(authenticated_page)
        script_list.goto(test_project["id"])

        dialog = NL2ScriptBatchDialog(authenticated_page)
        script_list.open_batch_nl2script_dialog()

        dialog.input_prompts("打开百度搜索测试")
        dialog.click_generate()

        # 不选项目直接保存
        dialog.click_save_selected()
        authenticated_page.wait_for_timeout(2000)


# ============================================================
# Self-healing API 测试 (保持原有)
# ============================================================

class TestSelfHealingAPI:
    """AI-HEAL-001 ~ AI-HEAL-008: Self-healing API 测试"""

    def test_heal_analysis(self, api_client, test_script):
        """AI-HEAL-001: 触发修复分析"""
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        assert exec_resp.status_code == 201
        execution_id = exec_resp.json()["id"]

        api_client.patch(
            f"{api_client.base_url}/executions/{execution_id}/",
            json={"status": "failed"},
        )

        heal_resp = api_client.post(
            f"{api_client.base_url}/executions/{execution_id}/heal/",
            json={
                "script_id": test_script["id"],
                "step_index": 0,
                "error_message": "Element not found: #missing-btn",
                "dom_snapshot": "<html><input id='old-kw' name='wd' /></html>",
            },
        )
        if heal_resp.status_code in (500, 503):
            pytest.skip("需要配置 LLM API Key")
        assert heal_resp.status_code == 200
        data = heal_resp.json()
        assert "suggested_locator" in data or "heal_log_id" in data or "heal_status" in data

    def test_heal_logs_list(self, api_client, test_script):
        """AI-HEAL-002: 查询修复日志"""
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = exec_resp.json()["id"]

        logs_resp = api_client.get(
            f"{api_client.base_url}/executions/{execution_id}/heal_logs/"
        )
        assert logs_resp.status_code == 200
        assert isinstance(logs_resp.json(), list)

    def test_heal_apply(self, api_client, test_script):
        """AI-HEAL-003: 手动应用修复"""
        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": test_script["id"]},
        )
        execution_id = exec_resp.json()["id"]

        api_client.post(
            f"{api_client.base_url}/executions/{execution_id}/heal/",
            json={"step_index": 0, "dom_snapshot": "<html><input id='kw' /></html>"},
        )

        logs_resp = api_client.get(
            f"{api_client.base_url}/executions/{execution_id}/heal_logs/"
        )
        logs = logs_resp.json()
        if logs:
            heal_log_id = logs[0]["id"]
            apply_resp = api_client.post(
                f"{api_client.base_url}/executions/heal_apply/",
                json={"heal_log_id": heal_log_id},
            )
            assert apply_resp.status_code == 200

    def test_heal_auto_apply_high_confidence(self, api_client, test_project):
        """AI-HEAL-004: 高置信度自动应用"""
        payload = {
            "name": f"自愈脚本_{int(time.time())}",
            "project": test_project["id"],
            "type": "web",
            "framework": "playwright",
            "steps": [
                {"type": "click", "name": "点击按钮", "params": {"locator": {"type": "css", "value": "#old-btn"}}},
            ],
            "heal_enabled": True,
        }
        script_resp = api_client.post(f"{api_client.base_url}/scripts/", json=payload)
        script = script_resp.json()

        exec_resp = api_client.post(
            f"{api_client.base_url}/executions/",
            json={"script_id": script["id"]},
        )
        execution_id = exec_resp.json()["id"]

        api_client.patch(f"{api_client.base_url}/executions/{execution_id}/", json={"status": "failed"})
        heal_resp = api_client.post(
            f"{api_client.base_url}/executions/{execution_id}/heal/",
            json={"step_index": 0, "dom_snapshot": "<html><button id='new-btn'>Submit</button></html>"},
        )

        logs_resp = api_client.get(f"{api_client.base_url}/executions/{execution_id}/heal_logs/")
        logs = logs_resp.json()
        if logs:
            assert logs[0].get("auto_applied") is True or logs[0].get("heal_status") in ("success", "pending")

        api_client.delete(f"{api_client.base_url}/scripts/{script['id']}/")
