"""
Page Object: 执行记录列表页
"""
from playwright.sync_api import Page, expect


class ExecutionListPage:
    URL = "/executions"

    def __init__(self, page: Page):
        self.page = page
        self.execution_rows = page.locator(".ant-table-tbody tr")

    def goto(self):
        self.page.goto(self.URL)
        self.page.wait_for_load_state("networkidle")

    def get_execution_count(self) -> int:
        return self.execution_rows.count()

    def get_status_by_index(self, index: int = 0) -> str:
        row = self.execution_rows.nth(index)
        tag = row.locator(".ant-tag")
        return tag.inner_text() if tag.is_visible() else ""

    def click_report(self, index: int = 0):
        row = self.execution_rows.nth(index)
        report_btn = row.locator("button", has_text="报告").first
        if report_btn.count() == 0:
            report_btn = row.locator("a", has_text="报告").first
        report_btn.click()

    def wait_for_status(self, index: int, status: str, timeout: int = 30000):
        """等待指定行的状态变为目标值"""
        row = self.execution_rows.nth(index)
        tag = row.locator(f".ant-tag:has-text('{status}')")
        tag.wait_for(state="visible", timeout=timeout)
