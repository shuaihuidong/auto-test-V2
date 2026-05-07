"""
Page Object: NL2Script AI 生成对话框 (重构后)
交互流程: 输入 → 生成 → 预览 → 保存/丢弃/编辑
"""
from playwright.sync_api import Page, expect


class NL2ScriptDialog:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator(".ant-modal").filter(has_text="AI 生成测试脚本")
        # 输入区
        self.textarea = self.modal.locator("textarea")
        self.generate_button = self.modal.locator("button", has_text="生成脚本")
        self.project_select = self.modal.locator(".ant-select").first
        self.close_button = self.modal.locator(".ant-modal-close")
        # 结果区
        self.result_area = self.modal.locator(".nl-result-area")
        self.steps_area = self.modal.locator(".nl-steps")
        self.step_items = self.steps_area.locator(".nl-step-item")
        # 操作按钮
        self.save_button = self.modal.locator("button", has_text="保存")
        self.edit_button = self.modal.locator("button", has_text="编辑脚本")
        self.discard_button = self.modal.locator("button", has_text="丢弃")
        self.copy_button = self.modal.locator("button", has_text="复制 JSON")

    def is_visible(self) -> bool:
        return self.modal.is_visible()

    def input_prompt(self, text: str):
        self.textarea.fill(text)

    def select_project(self, project_name: str):
        self.project_select.click()
        self.page.wait_for_timeout(500)
        options = self.page.locator(".ant-select-item-option")
        if options.count() > 0:
            exact = options.filter(has_text=project_name)
            if exact.count() > 0:
                exact.first.click()
            else:
                options.first.click()
        else:
            self.page.wait_for_timeout(1000)
            options = self.page.locator(".ant-select-item-option")
            if options.count() > 0:
                options.first.click()

    def click_generate(self):
        self.generate_button.click()
        self.result_area.wait_for(state="visible", timeout=30000)

    def get_generated_step_count(self) -> int:
        return self.step_items.count()

    def get_provider_info(self) -> str:
        tags = self.modal.locator(".nl-meta .ant-tag")
        if tags.count() >= 2:
            return tags.nth(1).inner_text()
        return ""

    def click_save(self):
        self.save_button.click()
        self.page.wait_for_timeout(3000)

    def click_edit(self):
        self.edit_button.click()
        self.page.wait_for_timeout(2000)

    def click_discard(self):
        self.discard_button.click()
        self.page.wait_for_timeout(500)

    def click_copy_json(self):
        self.copy_button.click()

    def is_result_visible(self) -> bool:
        return self.result_area.is_visible()

    def is_input_visible(self) -> bool:
        return self.modal.locator(".nl-input-area").is_visible()

    def has_edit_button(self) -> bool:
        return self.edit_button.is_visible()

    def has_save_button(self) -> bool:
        return self.save_button.is_visible()

    def close(self):
        self.close_button.click()
