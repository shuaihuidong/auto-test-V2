"""
Page Object: AI 设置页
"""
from playwright.sync_api import Page, expect


class AISettingsPage:
    URL = "/ai-settings"

    def __init__(self, page: Page):
        self.page = page
        # 标签页
        self.api_tab = page.locator(".ant-tabs-tab", has_text="API 配置")
        self.healing_tab = page.locator(".ant-tabs-tab", has_text="自愈提示词")
        self.nl2script_tab = page.locator(".ant-tabs-tab", has_text="NL2Script 提示词")
        # 保存按钮
        self.save_button = page.locator("button", has_text="保存配置")
        # 新建模板按钮
        self.create_template_button = page.locator("button", has_text="新建模板")
        # 表格
        self.template_table = page.locator(".ant-table")

    def goto(self):
        self.page.goto(self.URL)
        self.page.wait_for_load_state("networkidle")

    def click_api_tab(self):
        self.api_tab.click()
        self.page.wait_for_timeout(500)

    def click_healing_tab(self):
        self.healing_tab.click()
        self.page.wait_for_timeout(500)

    def click_nl2script_tab(self):
        self.nl2script_tab.click()
        self.page.wait_for_timeout(500)

    def get_config_inputs(self) -> dict:
        """获取当前页面上所有配置输入框的值"""
        inputs = self.page.locator(".config-section input")
        result = {}
        for i in range(inputs.count()):
            inp = inputs.nth(i)
            label = inp.evaluate("el => el.closest('.ant-form-item')?.querySelector('label')?.textContent || ''")
            value = inp.input_value()
            result[label.strip()] = value
        return result

    def set_config_value_by_key(self, key: str, value: str):
        """通过配置项 label 定位并设置值"""
        form_item = self.page.locator(f".ant-form-item", has_text=key).last
        input_el = form_item.locator("input")
        input_el.fill("")
        input_el.fill(value)

    def click_save_config(self):
        self.save_button.click()
        self.page.wait_for_timeout(1000)

    def get_template_rows(self) -> list:
        """获取当前标签页下的模板列表行"""
        rows = self.template_table.locator("tbody tr")
        result = []
        for i in range(rows.count()):
            cells = rows.nth(i).locator("td")
            if cells.count() >= 4:
                result.append({
                    "name": cells.nth(0).inner_text(),
                    "scenario": cells.nth(1).inner_text(),
                    "temperature": cells.nth(2).inner_text(),
                    "status": cells.nth(3).inner_text(),
                })
        return result

    def click_template_action(self, template_name: str, action: str):
        """点击模板行的操作按钮"""
        row = self.template_table.locator("tbody tr", has_text=template_name).first
        btn = row.locator("button", has_text=action)
        btn.click()
        self.page.wait_for_timeout(500)

    def get_modal(self):
        return self.page.locator(".ant-modal")

    def fill_template_form(self, name: str, scenario: str, prompt: str, temperature: float = 0.3):
        """填写模板创建/编辑表单"""
        modal = self.get_modal()
        name_input = modal.locator("input").first
        name_input.fill(name)

        # 选择场景
        scenario_select = modal.locator(".ant-select")
        scenario_select.click()
        option = self.page.locator(f".ant-select-item-option", has_text=scenario)
        if option.count() > 0:
            option.first.click()

        # 填写提示词
        textarea = modal.locator("textarea").last
        textarea.fill(prompt)

    def click_modal_ok(self):
        modal = self.get_modal()
        ok_btn = modal.locator("button.ant-btn-primary", has_text="确")
        if ok_btn.count() == 0:
            ok_btn = modal.locator("button.ant-btn-primary").last
        ok_btn.click()
        self.page.wait_for_timeout(1000)
