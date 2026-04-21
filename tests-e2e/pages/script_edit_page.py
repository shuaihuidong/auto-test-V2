"""
Page Object: 脚本编辑器页
"""
from playwright.sync_api import Page, expect


class ScriptEditPage:
    def __init__(self, page: Page):
        self.page = page
        # 基本信息
        self.name_input = page.locator("input[placeholder*='脚本名称']")
        self.save_button = page.locator("button", has_text="保存")
        self.debug_button = page.locator("button", has_text="调试")
        self.back_button = page.locator("button", has_text="返回")
        # 步骤面板
        self.step_panel = page.locator(".step-panel, .step-library")
        self.canvas = page.locator(".step-canvas, .flow-canvas, .ant-card")
        # JSON 编辑模式
        self.json_toggle = page.locator("button", has_text="JSON")
        self.json_editor = page.locator(".json-editor textarea, .CodeMirror")

    def goto_create(self, project_id: int):
        self.page.goto(f"/script/edit?project_id={project_id}")
        self.page.wait_for_load_state("networkidle")

    def goto_edit(self, script_id: int):
        self.page.goto(f"/script/edit/{script_id}")
        self.page.wait_for_load_state("networkidle")

    def set_name(self, name: str):
        self.name_input.fill(name)

    def save(self):
        self.save_button.click()
        # 等待保存成功提示
        self.page.locator(".ant-message-success").wait_for(state="visible", timeout=5000)

    def select_script_type(self, script_type: str = "web", framework: str = "playwright"):
        """在类型选择弹窗中选择脚本类型和框架"""
        modal = self.page.locator(".ant-modal")
        if modal.is_visible():
            # 选择类型
            type_card = modal.locator(f".type-card:has-text('{script_type}'), .ant-card:has-text('{script_type}')")
            if type_card.count() > 0:
                type_card.first.click()
            # 选择框架
            fw = modal.locator(f"text={framework}")
            if fw.count() > 0:
                fw.first.click()
            # 确认
            modal.locator("button", has_text="确").click()

    def drag_step_to_canvas(self, step_name: str):
        """从步骤面板拖拽步骤到画布"""
        step = self.step_panel.locator(f".step-item:has-text('{step_name}')")
        canvas_area = self.canvas.first
        if step.count() > 0:
            step.first.drag_to(canvas_area)

    def get_canvas_step_count(self) -> int:
        return self.canvas.locator(".step-node, .step-card, .step-item").count()

    def switch_to_json(self):
        self.json_toggle.click()

    def get_json_content(self) -> str:
        return self.json_editor.input_value() if self.json_editor.is_visible() else ""
