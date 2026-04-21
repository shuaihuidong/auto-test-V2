"""
Page Object: 脚本列表页
"""
from playwright.sync_api import Page, expect


class ScriptListPage:
    URL = "/scripts"

    def __init__(self, page: Page):
        self.page = page
        self.create_button = page.locator("button", has_text="新建脚本")
        self.ai_button = page.locator("button", has_text="AI 生成")
        self.batch_ai_button = page.locator("button", has_text="批量生成")
        self.script_rows = page.locator(".ant-table-tbody tr")
        self.back_button = page.locator("button", has_text="返回")

    def goto(self, project_id: int):
        self.page.goto(f"/scripts/{project_id}")
        self.page.wait_for_load_state("networkidle")

    def get_script_count(self) -> int:
        return self.script_rows.count()

    def click_edit(self, script_name: str):
        row = self.script_rows.filter(has_text=script_name).first
        row.locator("button", has_text="编辑").click()

    def click_run(self, script_name: str):
        row = self.script_rows.filter(has_text=script_name).first
        row.locator("button", has_text="运行").click()

    def click_delete(self, script_name: str):
        row = self.script_rows.filter(has_text=script_name).first
        row.locator("button").filter(has=self.page.locator(".anticon-delete")).click()

    def confirm_delete(self):
        self.page.locator(".ant-popconfirm .ant-btn-primary").click()

    def click_duplicate(self, script_name: str):
        row = self.script_rows.filter(has_text=script_name).first
        row.locator("button", has_text="复制").click()

    def open_nl2script_dialog(self):
        self.ai_button.click()

    def open_batch_nl2script_dialog(self):
        self.batch_ai_button.click()

    def has_script(self, name: str) -> bool:
        return self.script_rows.filter(has_text=name).count() > 0
