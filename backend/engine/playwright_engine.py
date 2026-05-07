"""
Playwright测试引擎实现
"""
import asyncio
import time
import os
from typing import Dict, Any
from django.conf import settings

from .base import TestEngine


class PlaywrightEngine(TestEngine):
    """
    Playwright测试引擎
    支持Chromium、Firefox和WebKit浏览器
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.browser_type = self.config.get('browser', 'chromium')
        self.headless = self.config.get('headless', False)
        self.timeout = self.config.get('timeout', 10000)  # Playwright uses milliseconds
        self.screenshot_dir = self.config.get('screenshot_dir', settings.SCREENSHOTS_ROOT)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def setup(self) -> bool:
        """初始化Playwright"""
        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()

            if self.browser_type == 'chromium':
                browser_launcher = self.playwright.chromium
            elif self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                raise ValueError(f"不支持的浏览器: {self.browser_type}")

            self.browser = browser_launcher.launch(headless=self.headless)
            self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)

            self.add_log(f"Playwright {self.browser_type} 初始化成功")
            return True

        except Exception as e:
            self.add_log(f"Playwright初始化失败: {str(e)}", 'error')
            return False

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行Playwright测试步骤"""
        start_time = time.time()
        step_type = step.get('type')
        params = step.get('params', {})

        try:
            # 步骤类型别名映射（AI 生成的脚本可能使用不同的命名）
            _TYPE_ALIASES = {
                'wait_element': 'wait',
                'wait_for_element': 'wait',
                'assert_element': 'assert',
                'assert_text': 'assert',
                'assert_title': 'assert',
                'type': 'input',
                'navigate': 'goto',
                'open': 'goto',
                'js': 'execute_script',
                'run_script': 'execute_script',
                'take_screenshot': 'screenshot',
            }
            resolved_type = _TYPE_ALIASES.get(step_type, step_type)

            if resolved_type == 'goto':
                result = self._goto(params)
            elif resolved_type == 'click':
                result = self._click(params)
            elif resolved_type == 'input':
                result = self._input(params)
            elif resolved_type == 'assert':
                result = self._assert(params)
            elif resolved_type == 'wait':
                result = self._wait(params)
            elif resolved_type == 'scroll':
                result = self._scroll(params)
            elif resolved_type == 'switch':
                result = self._switch(params)
            elif resolved_type == 'execute_script':
                result = self._execute_script(params)
            elif resolved_type == 'screenshot':
                result = self._screenshot(params)
            elif resolved_type == 'hover':
                result = self._hover(params)
            elif resolved_type == 'select':
                result = self._select(params)
            elif resolved_type == 'checkbox':
                result = self._checkbox(params)
            elif resolved_type == 'clear':
                result = self._clear(params)
            elif resolved_type == 'upload':
                result = self._upload(params)
            elif resolved_type == 'set_variable':
                result = self._set_variable(params)
            elif resolved_type == 'extract_variable':
                result = self._extract_variable(params)
            elif resolved_type == 'refresh':
                result = self._refresh(params)
            elif resolved_type == 'back':
                result = self._back(params)
            elif resolved_type == 'forward':
                result = self._forward(params)
            elif resolved_type == 'double_click':
                result = self._double_click(params)
            elif resolved_type == 'right_click':
                result = self._right_click(params)
            elif resolved_type == 'press_key':
                result = self._press_key(params)
            elif resolved_type == 'new_tab':
                result = self._new_tab(params)
            elif resolved_type == 'close_tab':
                result = self._close_tab(params)
            elif resolved_type == 'set_cookie':
                result = self._set_cookie(params)
            elif resolved_type == 'download':
                result = self._download(params)
            else:
                result = {
                    'success': False,
                    'error': f'未知的步骤类型: {step_type}'
                }

            result['duration'] = round((time.time() - start_time) * 1000, 2)

            # 如果步骤失败，尝试截图
            if not result.get('success') and self.config.get('screenshot_on_failure', True):
                screenshot_path = self._take_screenshot(f"step_{self.current_step_index}_failure")
                if screenshot_path:
                    result['screenshot'] = screenshot_path

                # 捕获页面元素摘要供 AI 分析
                try:
                    result['dom_snapshot'] = self._extract_page_elements()
                except Exception:
                    pass

            return result

        except Exception as e:
            # 捕获页面元素摘要供 AI 分析
            dom_snapshot = ''
            try:
                dom_snapshot = self._extract_page_elements()
            except Exception:
                pass

            result = {
                'success': False,
                'error': f'步骤执行异常: {str(e)}',
                'duration': round((time.time() - start_time) * 1000, 2)
            }
            if dom_snapshot:
                result['dom_snapshot'] = dom_snapshot
            return result

    def teardown(self) -> None:
        """清理Playwright资源"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self.add_log("Playwright已关闭")
        except Exception as e:
            self.add_log(f"关闭Playwright时出错: {str(e)}", 'error')

    def get_result(self) -> Dict[str, Any]:
        """获取测试结果"""
        return self.results

    def _find_element(self, locator: Dict[str, Any]):
        """查找页面元素"""
        locator_type = locator.get('type', 'css')
        value = locator.get('value', '')

        # 验证 value 不为空
        if not value or not value.strip():
            raise ValueError(f"定位器值不能为空 (type: {locator_type})")

        if locator_type == 'xpath':
            return self.page.locator(f'xpath={value}')
        elif locator_type == 'css':
            return self.page.locator(f'css={value}')
        elif locator_type == 'id':
            return self.page.locator(f'#{value}')
        elif locator_type == 'text':
            return self.page.get_by_text(value)
        elif locator_type == 'label':
            return self.page.get_by_label(value)
        elif locator_type == 'placeholder':
            return self.page.get_by_placeholder(value)
        elif locator_type == 'role':
            # value format: "button[name='Submit']"
            return self.page.get_by_role(value.split('[')[0], **self._parse_role_params(value))
        elif locator_type == 'test_id':
            return self.page.get_by_test_id(value)
        else:
            return self.page.locator(value)

    def _parse_role_params(self, role_value: str) -> Dict[str, str]:
        """解析role参数"""
        import re
        params = {}
        # 提取方括号中的参数
        match = re.search(r'\[(.*?)\]', role_value)
        if match:
            param_str = match.group(1)
            # 解析 key='value' 格式
            for m in re.finditer(r"(\w+)='([^']*)'", param_str):
                params[m.group(1)] = m.group(2)
        return params

    def _goto(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """导航到指定URL"""
        url = params.get('url')
        if not url:
            return {'success': False, 'error': '缺少url参数'}

        wait_until = params.get('wait_until', 'load')
        self.page.goto(url, wait_until=wait_until)
        return {'success': True, 'message': f'已导航到 {url}'}

    def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """点击元素"""
        locator = params.get('locator')
        if not locator:
            return {'success': False, 'error': '缺少locator参数'}

        element = self._find_element(locator)
        element.click(timeout=params.get('timeout', self.timeout))
        return {'success': True, 'message': '已点击元素'}

    def _input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """输入文本"""
        locator = params.get('locator')
        value = params.get('value')
        clear_first = params.get('clear_first', True)

        if not locator or value is None:
            return {'success': False, 'error': '缺少locator或value参数'}

        element = self._find_element(locator)
        if clear_first:
            element.fill('')
        element.fill(str(value))
        return {'success': True, 'message': f'已输入文本: {value}'}

    def _assert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """断言"""
        assert_type = params.get('assert_type', 'text')
        locator = params.get('locator')
        expected = params.get('expected')

        try:
            if assert_type == 'text':
                element = self._find_element(locator) if locator else self.page
                actual = element.inner_text() if locator else self.page.inner_text()
                success = str(actual).strip() == str(expected).strip()
                return {
                    'success': success,
                    'message': f'文本断言: 期望="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'exists':
                element = self._find_element(locator)
                element.count() > 0
                return {'success': True, 'message': '元素存在'}

            elif assert_type == 'visible':
                element = self._find_element(locator)
                is_visible = element.is_visible()
                return {
                    'success': is_visible,
                    'message': f'元素可见性: {is_visible}'
                }

            elif assert_type == 'attribute':
                attr_name = params.get('attribute', 'value')
                element = self._find_element(locator)
                actual = element.get_attribute(attr_name)
                success = str(actual) == str(expected)
                return {
                    'success': success,
                    'message': f'属性断言 [{attr_name}]: 期望="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'url':
                actual = self.page.url
                success = actual == expected or actual.startswith(expected)
                return {
                    'success': success,
                    'message': f'URL断言: 期望="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'title':
                actual = self.page.title()
                success = str(actual) == str(expected)
                return {
                    'success': success,
                    'message': f'标题断言: 期望="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'count':
                element = self._find_element(locator)
                actual = element.count()
                expected_count = int(expected)
                success = actual == expected_count
                return {
                    'success': success,
                    'message': f'数量断言: 期望={expected_count}, 实际={actual}',
                    'expected': expected_count,
                    'actual': actual
                }

            elif assert_type == 'contains':
                element = self._find_element(locator) if locator else self.page
                actual = element.inner_text() if locator else self.page.inner_text()
                success = str(expected) in str(actual)
                return {
                    'success': success,
                    'message': f'文本包含断言: 期望包含="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'not_contains':
                element = self._find_element(locator) if locator else self.page
                actual = element.inner_text() if locator else self.page.inner_text()
                success = str(expected) not in str(actual)
                return {
                    'success': success,
                    'message': f'文本不包含断言: 期望不包含="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'regex':
                import re
                element = self._find_element(locator) if locator else self.page
                actual = element.inner_text() if locator else self.page.inner_text()
                try:
                    pattern = re.compile(str(expected))
                    success = pattern.search(str(actual)) is not None
                    return {
                        'success': success,
                        'message': f'正则匹配断言: pattern="{expected}", 实际="{actual}"',
                        'expected': expected,
                        'actual': actual
                    }
                except re.error as e:
                    return {'success': False, 'error': f'正则表达式错误: {str(e)}'}

            elif assert_type == 'numeric_compare':
                element = self._find_element(locator) if locator else self.page
                actual = element.inner_text() if locator else self.page.inner_text()
                operator = params.get('operator', '==')

                try:
                    actual_num = float(str(actual).strip())
                    expected_num = float(str(expected).strip())

                    if operator == '==':
                        success = actual_num == expected_num
                    elif operator == '!=':
                        success = actual_num != expected_num
                    elif operator == '>':
                        success = actual_num > expected_num
                    elif operator == '>=':
                        success = actual_num >= expected_num
                    elif operator == '<':
                        success = actual_num < expected_num
                    elif operator == '<=':
                        success = actual_num <= expected_num
                    else:
                        return {'success': False, 'error': f'未知的比较运算符: {operator}'}

                    return {
                        'success': success,
                        'message': f'数值比较断言: 期望 {operator} {expected_num}, 实际={actual_num}',
                        'expected': expected_num,
                        'actual': actual_num
                    }
                except (ValueError, TypeError):
                    return {'success': False, 'error': '无法转换为数值进行比较'}

            elif assert_type == 'page_contains':
                text = params.get('text', expected)
                page_content = self.page.content()
                success = str(text) in page_content
                return {
                    'success': success,
                    'message': f'页面包含断言: 期望页面包含="{text}", 结果={success}',
                    'expected': text,
                    'actual': 'found' if success else 'not found'
                }

            elif assert_type == 'enabled':
                element = self._find_element(locator)
                is_enabled = element.is_enabled()
                return {
                    'success': is_enabled,
                    'message': f'元素可用性: {is_enabled}'
                }

            elif assert_type == 'element_value':
                element = self._find_element(locator)
                actual = element.input_value()
                success = str(actual).strip() == str(expected).strip()
                return {
                    'success': success,
                    'message': f'元素值断言: 期望="{expected}", 实际="{actual}"',
                    'expected': expected,
                    'actual': actual
                }

            elif assert_type == 'not_visible':
                try:
                    element = self._find_element(locator)
                    is_visible = element.is_visible()
                    return {
                        'success': not is_visible,
                        'message': f'元素不可见断言: visible={is_visible}, 期望不可见'
                    }
                except Exception:
                    # 元素不存在也视为不可见
                    return {
                        'success': True,
                        'message': '元素不可见断言: 元素不存在, 视为不可见'
                    }

            elif assert_type == 'not_exists':
                try:
                    element = self._find_element(locator)
                    exists = element.count() > 0
                    return {
                        'success': not exists,
                        'message': f'元素不存在断言: exists={exists}, 期望不存在'
                    }
                except Exception:
                    return {
                        'success': True,
                        'message': '元素不存在断言: 元素查找异常, 视为不存在'
                    }

            elif assert_type == 'disabled':
                element = self._find_element(locator)
                is_enabled = element.is_enabled()
                return {
                    'success': not is_enabled,
                    'message': f'元素禁用断言: enabled={is_enabled}, 期望禁用'
                }

            else:
                return {'success': False, 'error': f'未知的断言类型: {assert_type}'}

        except Exception as e:
            return {'success': False, 'error': f'断言失败: {str(e)}'}

    def _wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """等待"""
        wait_type = params.get('wait_type', 'fixed')
        duration = params.get('duration', 1000)

        if wait_type == 'fixed':
            self.page.wait_for_timeout(duration)
            return {'success': True, 'message': f'已等待 {duration} ms'}

        elif wait_type == 'selector':
            locator = params.get('locator')
            if not locator:
                return {'success': False, 'error': '缺少locator参数'}

            element = self._find_element(locator)
            state = params.get('state', 'visible')
            element.wait_for(state=state, timeout=duration)
            return {'success': True, 'message': f'元素已{state}'}

        elif wait_type == 'navigation':
            self.page.wait_for_load_state(state=params.get('state', 'load'), timeout=duration)
            return {'success': True, 'message': '导航已完成'}

        elif wait_type == 'url':
            expected_url = params.get('url')
            self.page.wait_for_url(expected_url, timeout=duration)
            return {'success': True, 'message': f'已跳转到 {expected_url}'}

        return {'success': False, 'error': f'未知的等待类型: {wait_type}'}

    def _scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """滚动页面"""
        scroll_type = params.get('scroll_type', 'position')

        if scroll_type == 'position':
            x = params.get('x', 0)
            y = params.get('y', 0)
            self.page.evaluate(f'window.scrollTo({x}, {y})')
            return {'success': True, 'message': f'已滚动到 ({x}, {y})'}

        elif scroll_type == 'element':
            locator = params.get('locator')
            if not locator:
                return {'success': False, 'error': '缺少locator参数'}

            element = self._find_element(locator)
            element.scroll_into_view_if_needed()
            return {'success': True, 'message': '已滚动到元素'}

        elif scroll_type == 'bottom':
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            return {'success': True, 'message': '已滚动到底部'}

        return {'success': False, 'error': f'未知的滚动类型: {scroll_type}'}

    def _switch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """切换上下文"""
        switch_type = params.get('switch_type', 'page')

        if switch_type == 'page':
            # Playwright中每个page都是独立的
            page_index = params.get('index', -1)
            if page_index >= 0:
                pages = self.context.pages
                if page_index < len(pages):
                    self.page = pages[page_index]
                    return {'success': True, 'message': f'已切换到页面 {page_index}'}

            # 切换到最新打开的页面
            if self.context.pages:
                self.page = self.context.pages[-1]
                return {'success': True, 'message': '已切换到最新页面'}

        elif switch_type == 'frame':
            locator = params.get('locator')
            if locator:
                element = self._find_element(locator)
                frame_name = element.get_attribute('name')
                self.page.frame(name=frame_name)
            else:
                # 切换回主文档
                pass
            return {'success': True, 'message': '已切换框架'}

        return {'success': False, 'error': f'未知的切换类型: {switch_type}'}

    def _execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行JavaScript"""
        script = params.get('script')
        if not script:
            return {'success': False, 'error': '缺少script参数'}

        result = self.page.evaluate(script)
        return {
            'success': True,
            'message': '已执行JavaScript',
            'result': result
        }

    def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """截图"""
        filename = params.get('filename', f'step_{self.current_step_index}')
        full_page = params.get('full_page', False)
        path = self._take_screenshot(filename, full_page)
        if path:
            return {'success': True, 'message': f'已截图: {path}', 'screenshot': path}
        return {'success': False, 'error': '截图失败'}

    def _take_screenshot(self, filename: str, full_page: bool = False) -> str:
        """实际执行截图，返回 MEDIA 相对 URL"""
        try:
            os.makedirs(self.screenshot_dir, exist_ok=True)
            filepath = os.path.join(self.screenshot_dir, f'{filename}.png')
            self.page.screenshot(path=filepath, full_page=full_page)
            # 返回 URL 路径而非文件系统绝对路径，便于前端直接展示
            rel = os.path.relpath(filepath, settings.MEDIA_ROOT)
            return f'/media/{rel}'.replace('\\', '/')
        except Exception as e:
            self.add_log(f'截图失败: {str(e)}', 'error')
            return None

    # ---- 元素摘要提取（替代原始 DOM 快照，供 AI 自愈分析） ----

    _EXTRACT_ELEMENTS_JS = """
    (() => {
        const KEEP_ATTRS = ['id','name','class','type','placeholder','value','role',
            'aria-label','data-testid','href','title','alt','for','action','method'];

        const results = [];
        const seen = new Set();

        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.nodeType !== 1) continue;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) continue;

            const hasId = el.id && el.id.trim();
            const hasName = el.getAttribute('name');
            const hasTestId = el.getAttribute('data-testid');
            const isInteractive = ['A','BUTTON','INPUT','SELECT','TEXTAREA','FORM','LABEL','IMG'].includes(el.tagName);
            const isHeading = /^H[1-6]$/.test(el.tagName);

            if (!hasId && !hasName && !hasTestId && !isInteractive && !isHeading) continue;

            const tag = el.tagName.toLowerCase();
            const key = hasId || (hasName + '_' + tag);
            if (seen.has(key)) continue;
            seen.add(key);

            const attrs = {};
            for (const a of KEEP_ATTRS) {
                const v = el.getAttribute(a);
                if (v !== null && v !== '') attrs[a] = v;
            }
            if (attrs.class) {
                const parts = attrs.class.trim().split(/\\s+/).filter(c =>
                    c.length >= 2 && !/^(css|sc|styled|_|__)[-_]/.test(c) && !/^[a-z]{1,2}[A-Z0-9]/.test(c)
                );
                if (parts.length > 0) attrs.class = parts.slice(0, 5).join(' ');
                else delete attrs.class;
            }

            const name = (el.getAttribute('aria-label') || el.getAttribute('title') ||
                el.getAttribute('alt') || el.getAttribute('placeholder') ||
                (el.textContent || '').trim()).slice(0, 80);

            const roleMap = {a:'link',button:'button',input: attrs.type==='submit'?'button':'textbox',
                select:'combobox',textarea:'textbox',form:'form',img:'img',
                h1:'heading',h2:'heading',h3:'heading',h4:'heading',h5:'heading',h6:'heading',
                nav:'navigation',main:'main'};
            const role = attrs.role || roleMap[tag] || '';

            const entry = { tag };
            if (role) entry.role = role;
            if (name) entry.name = name;
            if (Object.keys(attrs).length > 0) entry.attrs = attrs;
            results.push(entry);
        }

        let jsonStr = JSON.stringify(results, null, 2);
        if (jsonStr.length > 20000) {
            results.splice(80);
            jsonStr = JSON.stringify(results, null, 2);
        }
        return jsonStr;
    })()
    """

    def _extract_page_elements(self) -> str:
        """提取页面元素摘要（role + name + 属性），替代原始 page.content()

        返回 JSON 数组，每个元素包含 tag/role/name/attrs，
        体积通常为原始 DOM 的 1-2%，LLM 可直接理解。
        """
        try:
            return self.page.evaluate(self._EXTRACT_ELEMENTS_JS)
        except Exception:
            # fallback 到原始方式
            try:
                return self.page.content()[:30000]
            except Exception:
                return ''

    def _hover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """鼠标悬停"""
        locator = params.get('locator')
        if not locator:
            return {'success': False, 'error': '缺少locator参数'}

        element = self._find_element(locator)
        element.hover()
        return {'success': True, 'message': '已悬停'}

    def _select(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """选择下拉选项"""
        locator = params.get('locator')
        value = params.get('value')

        if not locator or value is None:
            return {'success': False, 'error': '缺少locator或value参数'}

        element = self._find_element(locator)
        element.select_option(value)
        return {'success': True, 'message': f'已选择: {value}'}

    def _checkbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """复选框操作"""
        locator = params.get('locator')
        checked = params.get('checked', True)

        if not locator:
            return {'success': False, 'error': '缺少locator参数'}

        element = self._find_element(locator)
        if checked:
            element.check()
        else:
            element.uncheck()
        return {'success': True, 'message': f'已{"勾选" if checked else "取消勾选"}复选框'}

    def _clear(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清空输入框"""
        locator = params.get('locator')

        if not locator:
            return {'success': False, 'error': '缺少locator参数'}

        element = self._find_element(locator)
        element.clear()
        return {'success': True, 'message': '已清空输入框'}

    def _upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """上传文件"""
        locator = params.get('locator')
        file_path = params.get('file_path')

        if not locator or not file_path:
            return {'success': False, 'error': '缺少locator或file_path参数'}

        element = self._find_element(locator)
        element.set_input_files(file_path)
        return {'success': True, 'message': f'已上传文件: {file_path}'}

    def _set_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置变量

        参数:
            params: 包含:
                - name: 变量名
                - value: 变量值
        """
        name = params.get('name')
        value = params.get('value')

        if not name:
            return {'success': False, 'error': '缺少name参数'}

        self.set_variable(name, value)
        return {
            'success': True,
            'message': f'已设置变量: {name} = {value}'
        }

    def _extract_variable(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        从页面元素提取变量

        参数:
            params: 包含:
                - name: 变量名
                - locator: 元素定位器
                - extract_type: 提取类型 (text, attribute, value)
                - attribute: 属性名（当extract_type为attribute时使用）
                - pattern: 提取模式（正则表达式，可选）
        """
        name = params.get('name')
        locator = params.get('locator')
        extract_type = params.get('extract_type', 'text')

        if not name:
            return {'success': False, 'error': '缺少name参数'}

        try:
            if extract_type in ['text', 'attribute', 'value']:
                if not locator:
                    return {'success': False, 'error': f'{extract_type}类型需要locator参数'}

                element = self._find_element(locator)

                if extract_type == 'text':
                    extracted_value = element.inner_text()
                elif extract_type == 'attribute':
                    attr_name = params.get('attribute', 'value')
                    extracted_value = element.get_attribute(attr_name)
                elif extract_type == 'value':
                    extracted_value = element.input_value()
                else:
                    extracted_value = None

            elif extract_type == 'url':
                extracted_value = self.page.url

            elif extract_type == 'title':
                extracted_value = self.page.title()

            elif extract_type == 'cookie':
                cookie_name = params.get('cookie_name')
                if cookie_name:
                    context_cookies = self.context.cookies()
                    extracted_value = next(
                        (c.get('value') for c in context_cookies if c.get('name') == cookie_name),
                        None
                    )
                else:
                    extracted_value = self.context.cookies()

            else:
                return {'success': False, 'error': f'未知的提取类型: {extract_type}'}

            # 如果指定了提取模式（正则表达式），则进行模式匹配提取
            pattern = params.get('pattern')
            if pattern and extracted_value:
                extracted_value = self.extract_from_text(str(extracted_value), pattern)

            if extracted_value is None:
                return {'success': False, 'error': '提取值为空'}

            self.set_variable(name, extracted_value)
            return {
                'success': True,
                'message': f'已提取变量: {name} = {extracted_value}',
                'value': extracted_value
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'提取变量失败: {str(e)}'
            }

    def _refresh(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """刷新页面"""
        self.page.reload()
        return {'success': True, 'message': '页面已刷新'}

    def _back(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """后退"""
        self.page.go_back()
        return {'success': True, 'message': '已后退到上一页'}

    def _forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """前进"""
        self.page.go_forward()
        return {'success': True, 'message': '已前进到下一页'}

    def _double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """双击元素"""
        locator = params.get('locator')
        if not locator:
            return {'success': False, 'error': '缺少locator参数'}
        element = self._find_element(locator)
        element.dblclick()
        return {'success': True, 'message': '已双击元素'}

    def _right_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """右键点击元素"""
        locator = params.get('locator')
        if not locator:
            return {'success': False, 'error': '缺少locator参数'}
        element = self._find_element(locator)
        element.click(button='right')
        return {'success': True, 'message': '已右键点击元素'}

    def _press_key(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """按键"""
        key = params.get('key')
        if not key:
            return {'success': False, 'error': '缺少key参数'}
        self.page.keyboard.press(key)
        return {'success': True, 'message': f'已按键: {key}'}

    def _new_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """打开新标签页"""
        url = params.get('url', '')
        new_page = self.context.new_page()
        if url:
            new_page.goto(url)
        self.page = new_page
        return {'success': True, 'message': f'已打开新标签页{"并导航到: " + url if url else ""}'}

    def _close_tab(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """关闭当前标签页"""
        self.page.close()
        pages = self.context.pages
        if pages:
            self.page = pages[-1]
        return {'success': True, 'message': '已关闭当前标签页'}

    def _set_cookie(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """设置Cookie"""
        name = params.get('name')
        value = params.get('value')
        if not name or value is None:
            return {'success': False, 'error': '缺少name或value参数'}
        cookie = {
            'name': name,
            'value': value,
            'url': params.get('url', self.page.url)
        }
        if params.get('domain'):
            cookie['domain'] = params['domain']
        if params.get('path'):
            cookie['path'] = params['path']
        self.context.add_cookies([cookie])
        return {'success': True, 'message': f'已设置Cookie: {name}'}

    def _download(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """下载文件"""
        url = params.get('url')
        if not url:
            return {'success': False, 'error': '缺少url参数'}
        save_path = params.get('save_path', '')
        with self.page.expect_download() as download_info:
            self.page.goto(url)
        download = download_info.value
        if save_path:
            download.save_as(save_path)
        else:
            save_path = download.path()
        return {
            'success': True,
            'message': f'文件已下载: {download.suggested_filename}',
            'save_path': str(save_path)
        }
