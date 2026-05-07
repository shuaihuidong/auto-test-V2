"""
Page Object: NL2Script 批量生成对话框 (重构后)
交互流程: 输入多条 → 批量生成 → 预览/AI审查 → 选择保存
"""
from playwright.sync_api import Page, expect


class NL2ScriptBatchDialog:
    def __init__(self, page: Page):
        self.page = page
        self.modal = page.locator(".ant-modal").filter(has_text="批量 AI 生成脚本")
        self.close_button = self.modal.locator(".ant-modal-close")
        # 输入区
        self.textarea = self.modal.locator("textarea").first
        self.generate_button = self.modal.locator("button", has_text="批量生成")
        # 结果区
        self.results_area = self.modal.locator(".batch-results")
        self.result_items = self.modal.locator(".batch-item")
        # 底部工具栏
        self.toolbar = self.modal.locator(".batch-toolbar")
        self.project_select = self.toolbar.locator(".ant-select")
        self.review_button = self.toolbar.locator("button", has_text="AI 审查")
        self.back_button = self.toolbar.locator("button", has_text="返回输入")
        self.save_selected_button = self.toolbar.locator("button", has_text="保存选中的")
        # 重新生成弹窗
        self.regen_modal = self.modal.locator(".ant-modal").filter(has_text="重新生成")
        self.regen_textarea = self.regen_modal.locator("textarea")
        self.regen_confirm_button = self.regen_modal.locator("button", has_text="确 定")

    def is_visible(self) -> bool:
        return self.modal.is_visible()

    def input_prompts(self, text: str):
        self.textarea.fill(text)

    def click_generate(self):
        self.generate_button.click()
        # 等待结果出现或进度条消失
        self.page.wait_for_timeout(5000)

    def get_result_count(self) -> int:
        return self.result_items.count()

    def get_success_count(self) -> int:
        return self.result_items.locator(".ant-tag-green").count()

    def get_failed_count(self) -> int:
        return self.result_items.locator(".ant-tag-red").count()

    def toggle_expand(self, index: int):
        item = self.result_items.nth(index)
        item.locator("button", has_text="展开").click()

    def toggle_check(self, index: int, checked: bool = True):
        item = self.result_items.nth(index)
        checkbox = item.locator(".ant-checkbox")
        if checkbox.is_visible():
            is_checked = item.locator(".ant-checkbox-checked").is_visible()
            if is_checked != checked:
                checkbox.click()

    def uncheck_all(self):
        for i in range(self.get_result_count()):
            self.toggle_check(i, False)

    def check_item(self, index: int):
        self.toggle_check(index, True)

    def select_project_in_toolbar(self, project_name: str):
        self.project_select.click()
        self.page.wait_for_timeout(500)
        options = self.page.locator(".ant-select-item-option")
        if options.count() > 0:
            exact = options.filter(has_text=project_name)
            if exact.count() > 0:
                exact.first.click()
            else:
                options.first.click()

    def click_review(self):
        self.review_button.click()
        self.page.wait_for_timeout(5000)

    def click_save_selected(self):
        self.save_selected_button.click()
        self.page.wait_for_timeout(3000)

    def click_back(self):
        self.back_button.click()
        self.page.wait_for_timeout(500)

    def click_regenerate(self, index: int):
        item = self.result_items.nth(index)
        item.locator("button", has_text="重新生成").click()
        self.page.wait_for_timeout(500)

    def confirm_regenerate(self):
        self.regen_confirm_button.click()
        self.page.wait_for_timeout(5000)

    def is_toolbar_visible(self) -> bool:
        return self.toolbar.is_visible()

    def has_review_tags(self, index: int) -> bool:
        item = self.result_items.nth(index)
        return item.locator("text=Q:").is_visible()

    def close(self):
        self.close_button.click()
