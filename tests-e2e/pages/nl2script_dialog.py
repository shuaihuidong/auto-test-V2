"""
Page Object: NL2Script AI 生成对话框
"""
from playwright.sync_api import Page, expect


class NL2ScriptDialog:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator(".ant-modal:has-text('AI 生成测试脚本')")
        self.textarea = self.modal.locator("textarea")
        self.generate_button = self.modal.locator("button", has_text="生成脚本")
        self.save_button = self.modal.locator("button", has_text="保存")
        self.close_button = self.modal.locator(".ant-modal-close")
        # 结果区域
        self.result_area = self.modal.locator(".nl-result-area, .nl-steps")
        self.step_items = self.result_area.locator(".nl-step-item")
        self.provider_tag = self.modal.locator(".ant-tag", has_text="mock")

    def is_visible(self) -> bool:
        return self.modal.is_visible()

    def input_prompt(self, text: str):
        self.textarea.fill(text)

    def click_generate(self):
        self.generate_button.click()
        # 等待生成结果
        self.result_area.wait_for(state="visible", timeout=15000)

    def get_generated_step_count(self) -> int:
        return self.step_items.count()

    def get_provider_info(self) -> str:
        tags = self.modal.locator(".nl-meta .ant-tag")
        if tags.count() >= 2:
            return tags.nth(1).inner_text()
        return ""

    def save_as_script(self, script_name: str, project_id: int = None):
        # 填写脚本名
        name_input = self.modal.locator("input[placeholder*='脚本名称']")
        if name_input.is_visible():
            name_input.fill(script_name)
        # 选择项目
        if project_id:
            project_select = self.modal.locator(".ant-select")
            if project_select.is_visible():
                project_select.click()
                self.page.locator(f".ant-select-item-option:has-text('{project_id}')").first.click()
        self.save_button.click()

    def close(self):
        self.close_button.click()
