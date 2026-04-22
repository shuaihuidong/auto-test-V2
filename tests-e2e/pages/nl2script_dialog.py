"""
Page Object: NL2Script AI 生成对话框
"""
from playwright.sync_api import Page, expect


class NL2ScriptDialog:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator(".ant-modal").filter(has_text="AI 生成测试脚本")
        self.textarea = self.modal.locator("textarea")
        self.generate_button = self.modal.locator("button", has_text="生成脚本")
        self.close_button = self.modal.locator(".ant-modal-close")
        # 项目选择 (在输入区，保存前需要先选择)
        self.project_select = self.modal.locator(".ant-select").first
        # 保存按钮 (生成后才出现，文字是"保存为脚本")
        self.save_button = self.modal.locator("button", has_text="保存为脚本")
        # 结果区域
        self.result_area = self.modal.locator(".nl-result-area")
        self.steps_area = self.modal.locator(".nl-steps")
        self.step_items = self.steps_area.locator(".nl-step-item")

    def is_visible(self) -> bool:
        return self.modal.is_visible()

    def input_prompt(self, text: str):
        self.textarea.fill(text)

    def select_project(self, project_name: str):
        """在生成前选择项目（保存按钮需要先选项目才出现）"""
        self.project_select.click()
        # 等待下拉展开
        self.page.wait_for_timeout(500)
        # 使用 title 属性匹配或直接用文本匹配
        options = self.page.locator(".ant-select-item-option")
        if options.count() > 0:
            # 先尝试精确匹配项目名
            exact = options.filter(has_text=project_name)
            if exact.count() > 0:
                exact.first.click()
            else:
                # 模糊匹配 (项目名包含 E2E测试项目 前缀)
                options.first.click()
        else:
            # 没有下拉选项可能是因为 select 还没加载完
            self.page.wait_for_timeout(1000)
            options = self.page.locator(".ant-select-item-option")
            if options.count() > 0:
                options.first.click()

    def click_generate(self):
        self.generate_button.click()
        # 等待生成结果出现
        self.result_area.wait_for(state="visible", timeout=30000)

    def get_generated_step_count(self) -> int:
        return self.step_items.count()

    def get_provider_info(self) -> str:
        tags = self.modal.locator(".nl-meta .ant-tag")
        if tags.count() >= 2:
            return tags.nth(1).inner_text()
        return ""

    def save_as_script(self, script_name: str = None, project_id: int = None):
        """点击保存为脚本按钮 (需要先生成结果且已选择项目)"""
        # 直接点击"保存为脚本"按钮
        self.save_button.click()
        # 等待保存完成
        self.page.wait_for_timeout(3000)

    def close(self):
        self.close_button.click()
