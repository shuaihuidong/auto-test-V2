"""
Page Object: 报告页 — 含 HealLogPanel 自愈面板
"""
from playwright.sync_api import Page, expect


class ReportPage:
    def __init__(self, page: Page):
        self.page = page
        # 自愈面板
        self.heal_panel = page.locator(".heal-panel")
        self.heal_items = self.heal_panel.locator(".heal-item")
        self.heal_empty = self.heal_panel.locator(".heal-empty, .ant-empty")

    def goto(self, execution_id: int):
        self.page.goto(f"/reports/{execution_id}")
        self.page.wait_for_load_state("networkidle")

    def get_heal_log_count(self) -> int:
        return self.heal_items.count()

    def has_heal_logs(self) -> bool:
        return self.heal_items.count() > 0

    def is_heal_empty(self) -> bool:
        return self.heal_empty.is_visible()

    def get_heal_log_status(self, index: int = 0) -> str:
        tag = self.heal_items.nth(index).locator(".ant-tag").first
        return tag.inner_text() if tag.is_visible() else ""

    def click_apply(self, index: int = 0):
        item = self.heal_items.nth(index)
        apply_btn = item.locator("button", has_text="应用")
        if apply_btn.is_visible():
            apply_btn.click()

    def is_auto_applied(self, index: int = 0) -> bool:
        item = self.heal_items.nth(index)
        return item.locator("text=已自动应用").is_visible()

    def get_confidence(self, index: int = 0) -> str:
        item = self.heal_items.nth(index)
        conf = item.locator("text=置信度")
        if conf.is_visible():
            return conf.inner_text()
        return ""

    def get_original_locator(self, index: int = 0) -> str:
        item = self.heal_items.nth(index)
        locator = item.locator(".heal-locator.old")
        return locator.inner_text() if locator.is_visible() else ""

    def get_suggested_locator(self, index: int = 0) -> str:
        item = self.heal_items.nth(index)
        locator = item.locator(".heal-locator.new")
        return locator.inner_text() if locator.is_visible() else ""
