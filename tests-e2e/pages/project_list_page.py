"""
Page Object: 项目列表页
"""
from playwright.sync_api import Page, expect


class ProjectListPage:
    URL = "/projects"

    def __init__(self, page: Page):
        self.page = page
        # 新建项目
        self.create_button = page.locator("button", has_text="新建项目")
        self.project_cards = page.locator(".project-card, .ant-card")
        # 创建表单 (modal)
        self.name_input = page.locator(".ant-modal input#name, .ant-modal input[placeholder*='项目名称']")
        self.type_select = page.locator(".ant-modal .ant-select")
        self.modal_ok = page.locator(".ant-modal .ant-btn-primary", has_text="确")

    def goto(self):
        self.page.goto(self.URL)
        self.page.wait_for_load_state("networkidle")

    def create_project(self, name: str, project_type: str = "web"):
        self.create_button.click()
        self.name_input.fill(name)
        # 选择项目类型
        self.type_select.click()
        type_option = self.page.locator(f".ant-select-item-option", has_text=project_type.capitalize())
        if type_option.count() > 0:
            type_option.first.click()
        self.modal_ok.click()
        # 等待 modal 关闭
        self.page.locator(".ant-modal").wait_for(state="hidden", timeout=10000)

    def get_project_count(self) -> int:
        return self.project_cards.count()

    def click_project(self, name: str):
        card = self.page.locator(f".project-card:has-text('{name}'), .ant-card:has-text('{name}')")
        card.first.click()

    def has_menu_item(self, text: str) -> bool:
        """检查侧边栏是否包含指定菜单项"""
        return self.page.locator(f".ant-menu-item, .ant-menu-submenu-title").filter(has_text=text).count() > 0
