"""
Page Object: 登录页
"""
from playwright.sync_api import Page, expect


class LoginPage:
    URL = "/login"

    def __init__(self, page: Page):
        self.page = page
        # 表单元素
        self.username_input = page.locator('input[placeholder="用户名"]')
        self.password_input = page.locator('input[placeholder="密码"]')
        self.submit_button = page.locator('button[type="submit"]')
        # 错误提示 (ant-design message)
        self.error_message = page.locator(".ant-message-error")

    def goto(self):
        self.page.goto(self.URL)
        self.page.wait_for_load_state("networkidle")

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()

    def wait_for_redirect(self):
        """等待登录成功跳转到首页"""
        self.page.wait_for_url("**/projects**", timeout=10000)

    def get_error_text(self) -> str:
        self.error_message.wait_for(state="visible", timeout=5000)
        return self.error_message.inner_text()

    def is_on_login_page(self) -> bool:
        return "/login" in self.page.url
