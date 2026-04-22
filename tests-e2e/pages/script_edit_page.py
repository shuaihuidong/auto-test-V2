"""
Page Object: 脚本编辑器页
"""
from playwright.sync_api import Page, expect


class ScriptEditPage:
    def __init__(self, page: Page):
        self.page = page
        # 页面头部按钮 (使用原生 button 选择器，SimpleButton 渲染为 <button>)
        self.back_button = page.locator("button", has_text="返回")
        self.save_button = page.locator("button", has_text="保存")
        # 脚本名称输入 (SimpleInput 渲染为原生 <input>)
        self.name_input = page.locator("input[placeholder='请输入脚本名称']")
        # 类型选择 Modal
        self.type_modal = page.locator(".simple-modal, .ant-modal").filter(has_text="选择测试类型")
        # 编辑器区域
        self.editor_area = page.locator(".script-editor, .editor-card")

    def goto_create(self, project_id: int):
        self.page.goto(f"/script/edit?project_id={project_id}")
        self.page.wait_for_load_state("networkidle")

    def goto_edit(self, script_id: int):
        self.page.goto(f"/script/edit/{script_id}")
        self.page.wait_for_load_state("networkidle")

    def set_name(self, name: str):
        self.name_input.fill(name)

    def select_script_type(self, script_type: str = "web", framework: str = "selenium"):
        """在类型选择弹窗中选择脚本类型和框架"""
        # 等待类型选择 modal 出现
        modal = self.page.locator(".simple-modal, .ant-modal").filter(has_text="选择测试类型")
        if not modal.is_visible(timeout=5000):
            return

        # 点击脚本类型卡片 (type-card class)
        type_card = modal.locator(f".type-card").filter(has_text=script_type.capitalize())
        if type_card.count() > 0:
            type_card.first.click()

        # 等待框架选项加载
        self.page.wait_for_timeout(500)

        # 点击框架卡片
        fw_card = modal.locator(f".framework-card").filter(has_text=framework.capitalize())
        if fw_card.count() > 0:
            fw_card.first.click()

        # 点击确定按钮
        confirm_btn = modal.locator("button", has_text="确定")
        if confirm_btn.is_visible(timeout=3000):
            confirm_btn.click()

        # 等待 modal 关闭
        self.page.wait_for_timeout(1000)

    def save(self):
        self.save_button.click()
        # 等待保存成功提示 (可能是 ant-message 或其他提示)
        self.page.wait_for_timeout(2000)

    def drag_step_to_canvas(self, step_name: str):
        """从步骤面板拖拽步骤到画布"""
        # 查找步骤面板中的步骤项
        step = self.page.locator(f".step-card, .step-item").filter(has_text=step_name)
        if step.count() > 0:
            canvas = self.page.locator(".canvas-area, .step-canvas").first
            step.first.drag_to(canvas)

    def get_canvas_step_count(self) -> int:
        return self.page.locator(".canvas-step, .step-node").count()
