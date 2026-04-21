"""
测试用例: 登录与权限控制 (UI-AUTH-001 ~ UI-AUTH-008)
"""
import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.project_list_page import ProjectListPage


class TestLogin:
    """UI-AUTH-001 ~ UI-AUTH-003: 登录功能"""

    def test_login_success(self, page):
        """UI-AUTH-001: 正常登录"""
        login = LoginPage(page)
        login.goto()
        login.login("admin", "admin123")
        login.wait_for_redirect()
        assert "/projects" in page.url

    def test_login_wrong_password(self, page):
        """UI-AUTH-002: 错误密码"""
        login = LoginPage(page)
        login.goto()
        login.login("admin", "wrong_password")
        error = login.get_error_text()
        assert error != ""
        assert login.is_on_login_page()

    def test_login_empty_form(self, page):
        """UI-AUTH-003: 空表单提交"""
        login = LoginPage(page)
        login.goto()
        login.submit_button.click()
        # 应该看到表单校验提示
        form_error = page.locator(".ant-form-item-explain-error")
        expect(form_error.first).to_be_visible()

    def test_token_expired_redirect(self, page):
        """UI-AUTH-004: Token 过期跳转登录页"""
        page.goto("/projects")
        # 设置一个无效 token
        page.evaluate("localStorage.setItem('auth_token', 'invalid-token')")
        page.reload()
        # 应被拦截跳转到登录页
        page.wait_for_url("**/login**", timeout=10000)
        assert "/login" in page.url


class TestPermission:
    """UI-AUTH-005 ~ UI-AUTH-008: 权限控制"""

    def test_super_admin_sees_all_menus(self, authenticated_page):
        """UI-AUTH-005: 超管可见所有菜单"""
        projects = ProjectListPage(authenticated_page)
        projects.goto()
        assert projects.has_menu_item("用户管理") or projects.has_menu_item("账号角色")

    def test_tester_no_admin_menus(self, tester_page):
        """UI-AUTH-006: 测试人员看不到管理菜单"""
        projects = ProjectListPage(tester_page)
        projects.goto()
        assert not projects.has_menu_item("用户管理")

    def test_guest_readonly_no_create(self, guest_page):
        """UI-AUTH-007: 访客无创建/删除按钮"""
        projects = ProjectListPage(guest_page)
        projects.goto()
        # 查找新建按钮不应存在或不可见
        create_btn = guest_page.locator("button", has_text="新建项目")
        assert create_btn.count() == 0 or not create_btn.is_visible()

    def test_guest_cannot_access_account_role(self, guest_page):
        """UI-AUTH-008: 访客无法访问账号角色管理"""
        guest_page.goto("/account-role")
        # 应被路由守卫拦截
        # 可能跳转到首页或显示无权限提示
        guest_page.wait_for_timeout(2000)
        assert "/account-role" not in guest_page.url or \
               guest_page.locator("text=无权限, text=权限不足").count() > 0
