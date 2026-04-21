"""
Playwright 执行引擎 - 替代 Selenium
- 全异步，与 asyncio 事件循环配合
- 自动 Trace 录制
- 完全兼容现有步骤 JSON 格式
"""

import asyncio
import base64
import json
import time
from typing import Any, Dict, Optional

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Locator,
    Playwright,
    expect,
)


# Playwright 支持的浏览器类型映射
BROWSER_MAP = {
    "chromium": "chromium",
    "chrome": "chromium",   # 兼容旧配置
    "firefox": "firefox",
    "edge": "chromium",     # Edge 基于 Chromium
}


class PlaywrightStepExecutor:
    """
    Playwright 单步执行器
    将平台统一的步骤 JSON 转译为 Playwright API 调用
    """

    def __init__(self, page: Page):
        self.page = page

    # ==================== 定位器转换 ====================

    def _get_locator(self, locator: Dict[str, Any]) -> Optional[Locator]:
        """
        将平台定位器格式转为 Playwright Locator

        Args:
            locator: {"type": "xpath|css|id|...", "value": "..."}
        """
        if not locator or not locator.get("value"):
            return None

        loc_type = locator.get("type", "css")
        loc_value = locator.get("value", "")

        try:
            if loc_type == "css":
                return self.page.locator(loc_value)
            elif loc_type == "xpath":
                return self.page.locator(f"xpath={loc_value}")
            elif loc_type == "id":
                return self.page.locator(f"#{loc_value}")
            elif loc_type == "name":
                return self.page.locator(f"[name='{loc_value}']")
            elif loc_type == "class":
                return self.page.locator(f".{loc_value}")
            elif loc_type == "tag":
                return self.page.locator(loc_value)
            elif loc_type == "link_text":
                return self.page.get_by_text(loc_value, exact=True)
            elif loc_type == "partial_link_text":
                return self.page.get_by_text(loc_value, exact=False)
            elif loc_type == "data-testid":
                return self.page.get_by_test_id(loc_value)
            elif loc_type == "text":
                return self.page.get_by_text(loc_value)
            else:
                # 降级为 CSS
                return self.page.locator(loc_value)
        except Exception as e:
            logger.warning(f"定位器创建失败: {loc_type}={loc_value}, {e}")
            return None

    # ==================== 变量替换 ====================

    @staticmethod
    def _replace_variables(params: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """递归替换参数中的 ${变量名}"""

        def _replace(value: Any) -> Any:
            if isinstance(value, str):
                for var_name, var_value in variables.items():
                    value = value.replace(f"${{{var_name}}}", str(var_value))
                return value
            elif isinstance(value, dict):
                return {k: _replace(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_replace(v) for v in value]
            return value

        return _replace(params)

    # ==================== 步骤执行入口 ====================

    async def execute(
        self, step: Dict[str, Any], variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step: {"type": str, "name": str, "params": dict}
            variables: 变量字典

        Returns:
            {"success": bool, "message": str, "screenshot": str|None}
        """
        step_type = step.get("type", "")
        step_name = step.get("name", "")
        params = self._replace_variables(step.get("params", {}), variables or {})

        logger.info(f"执行步骤: {step_name} (类型: {step_type})")

        try:
            handler = getattr(self, f"_step_{step_type}", None)
            if handler:
                result = await handler(params)
            else:
                result = {"success": False, "message": f"未知步骤类型: {step_type}"}

            if result["success"]:
                logger.info(f"步骤成功: {step_name}")
            else:
                logger.error(f"步骤失败: {step_name} - {result['message']}")

            return result

        except Exception as e:
            logger.exception(f"步骤异常: {step_name}")
            return {
                "success": False,
                "message": f"执行异常: {str(e)}",
                "screenshot": await self._screenshot_base64(),
            }

    # ==================== 导航类 ====================

    async def _step_goto(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "")
        if url and not url.startswith(("http://", "https://", "file://")):
            url = "http://" + url
        await self.page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "message": f"打开页面: {url}"}

    async def _step_refresh(self, params: Dict[str, Any]) -> Dict[str, Any]:
        await self.page.reload()
        return {"success": True, "message": "页面已刷新"}

    async def _step_back(self, params: Dict[str, Any]) -> Dict[str, Any]:
        await self.page.go_back()
        return {"success": True, "message": "已后退"}

    async def _step_forward(self, params: Dict[str, Any]) -> Dict[str, Any]:
        await self.page.go_forward()
        return {"success": True, "message": "已前进"}

    # ==================== 交互类 ====================

    async def _step_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        await locator.click()
        return {"success": True, "message": "元素已点击"}

    async def _step_double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        await locator.dblclick()
        return {"success": True, "message": "元素已双击"}

    async def _step_right_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        await locator.click(button="right")
        return {"success": True, "message": "元素已右键点击"}

    async def _step_hover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        await locator.hover()
        return {"success": True, "message": "鼠标已悬停"}

    async def _step_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}

        value = params.get("value", "")
        if params.get("clear_first", True):
            await locator.fill("")
        await locator.fill(value)
        return {"success": True, "message": f"已输入: {value}"}

    async def _step_clear(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        await locator.fill("")
        return {"success": True, "message": "输入框已清空"}

    async def _step_select(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        value = params.get("value", "")
        await locator.select_option(label=value)
        return {"success": True, "message": f"已选择: {value}"}

    async def _step_checkbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        checked = params.get("checked", True)
        if checked:
            await locator.check()
        else:
            await locator.uncheck()
        return {"success": True, "message": f"复选框已{'选中' if checked else '取消选中'}"}

    # ==================== 断言类 ====================

    async def _step_assert_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        expected = params.get("text", "")
        locator_dict = params.get("locator", {})

        if locator_dict and locator_dict.get("value"):
            locator = self._get_locator(locator_dict)
            if not locator:
                return {"success": False, "message": "未找到元素"}
            actual = await locator.text_content() or ""
        else:
            actual = await self.page.locator("body").text_content() or ""

        if expected in actual:
            return {"success": True, "message": f"文本验证通过: {expected}"}
        return {
            "success": False,
            "message": f"文本验证失败，期望包含: {expected}，实际: {actual[:200]}",
            "screenshot": await self._screenshot_base64(),
        }

    async def _step_assert_title(self, params: Dict[str, Any]) -> Dict[str, Any]:
        expected = params.get("expected", "")
        actual = await self.page.title()
        if expected == actual:
            return {"success": True, "message": f"标题验证通过: {expected}"}
        return {
            "success": False,
            "message": f"标题验证失败，期望: {expected}，实际: {actual}",
            "screenshot": await self._screenshot_base64(),
        }

    async def _step_assert_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        expected = params.get("expected", "")
        actual = self.page.url
        if expected == actual:
            return {"success": True, "message": f"URL验证通过: {expected}"}
        return {
            "success": False,
            "message": f"URL验证失败，期望: {expected}，实际: {actual}",
            "screenshot": await self._screenshot_base64(),
        }

    async def _step_assert_element(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if locator and await locator.count() > 0:
            return {"success": True, "message": "元素存在"}
        return {
            "success": False,
            "message": "元素不存在",
            "screenshot": await self._screenshot_base64(),
        }

    async def _step_assert_visible(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        if locator and await locator.is_visible():
            return {"success": True, "message": "元素可见"}
        return {
            "success": False,
            "message": "元素不可见",
            "screenshot": await self._screenshot_base64(),
        }

    # ==================== 等待类 ====================

    async def _step_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration = params.get("duration", 1)
        await asyncio.sleep(duration)
        return {"success": True, "message": f"等待了 {duration} 秒"}

    async def _step_wait_element(self, params: Dict[str, Any]) -> Dict[str, Any]:
        timeout = (params.get("timeout", 10)) * 1000  # 秒 → 毫秒
        locator = self._get_locator(params.get("locator"))
        if not locator:
            return {"success": False, "message": "未提供定位器"}
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            return {"success": True, "message": "元素已出现"}
        except Exception:
            return {
                "success": False,
                "message": f"等待元素超时（{timeout / 1000}秒）",
                "screenshot": await self._screenshot_base64(),
            }

    # ==================== 其他 ====================

    async def _step_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        data = await self._screenshot_base64()
        return {"success": True, "message": "截图成功", "screenshot": data}

    async def _step_scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        scroll_type = params.get("scroll_type", "bottom")
        if scroll_type == "top":
            await self.page.evaluate("window.scrollTo(0, 0)")
        elif scroll_type == "bottom":
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif scroll_type == "custom":
            x, y = params.get("x", 0), params.get("y", 0)
            await self.page.evaluate(f"window.scrollTo({x}, {y})")
        return {"success": True, "message": f"已滚动到{scroll_type}"}

    async def _step_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        locator = self._get_locator(params.get("locator"))
        file_path = params.get("file_path", "")
        if not locator or not file_path:
            return {"success": False, "message": "缺少locator或file_path"}
        await locator.set_input_files(file_path)
        return {"success": True, "message": f"已上传文件: {file_path}"}

    async def _step_download(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url", "")
        if url:
            async with self.page.expect_download() as download_info:
                await self.page.goto(url)
            download = await download_info.value
            save_path = params.get("save_path", f"/tmp/{download.suggested_filename}")
            await download.save_as(save_path)
            return {"success": True, "message": f"文件已下载到: {save_path}"}
        return {"success": True, "message": "下载已触发"}

    # ==================== 辅助方法 ====================

    async def _screenshot_base64(self) -> str:
        """截图并返回 Base64 编码"""
        try:
            buf = await self.page.screenshot(type="png")
            return base64.b64encode(buf).decode("utf-8")
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return ""

    async def get_dom_snapshot(self) -> str:
        """获取当前页面 DOM 快照，用于自愈分析"""
        try:
            return await self.page.content()
        except Exception as e:
            logger.error(f"DOM 快照获取失败: {e}")
            return ""


class PlaywrightScriptExecutor:
    """
    脚本执行器 - 管理浏览器生命周期，执行完整脚本
    """

    def __init__(self, config, sandbox: bool = False):
        self.config = config
        self.sandbox = sandbox  # 沙盒模式：短超时、不录制 Trace、仅验证不等待
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._step_executor: Optional[PlaywrightStepExecutor] = None
        self._trace_path: Optional[str] = None

    async def start(self, browser_type: str = "chromium") -> bool:
        """
        启动浏览器，创建上下文和页面

        Returns:
            是否启动成功
        """
        try:
            pw_type = BROWSER_MAP.get(browser_type, "chromium")
            self._playwright = await async_playwright().start()

            # 启动浏览器
            launch_method = getattr(self._playwright, pw_type)
            self._browser = await launch_method.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo if self.config.slow_mo > 0 else None,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )

            # 创建上下文（沙盒模式使用更短的超时）
            default_timeout = 5000 if self.sandbox else 30000
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )
            self._context.set_default_timeout(default_timeout)
            self._context.set_default_navigation_timeout(default_timeout)

            # Trace 录制（沙盒模式跳过以节省资源）
            if self.config.trace_enabled and not self.sandbox:
                await self._context.tracing.start(
                    screenshots=True,
                    snapshots=True,
                    sources=True,
                )

            self._page = await self._context.new_page()
            self._step_executor = PlaywrightStepExecutor(self._page)

            logger.info(f"Playwright 浏览器启动成功: {browser_type} (headless={self.config.headless})")
            return True

        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            await self.stop()
            return False

    async def execute_script(
        self,
        script: Dict[str, Any],
        variables: Dict[str, Any] = None,
        on_step_complete=None,
    ) -> Dict[str, Any]:
        """
        执行完整脚本

        Args:
            script: {"steps": [...], "name": str}
            variables: 变量字典
            on_step_complete: 回调 (step_index, step_result)

        Returns:
            {"success": bool, "message": str, "steps": list, "duration": float}
        """
        if not self._step_executor:
            return {"success": False, "message": "浏览器未启动", "steps": []}

        steps = script.get("steps", [])
        script_name = script.get("name", "未命名脚本")
        logger.info(f"开始执行脚本: {script_name}，共 {len(steps)} 个步骤")

        results = []
        all_success = True
        start_time = time.time()

        for index, step in enumerate(steps):
            step_name = step.get("name", f"步骤{index + 1}")
            step_start = time.time()

            step_result = await self._step_executor.execute(step, variables)
            step_duration = round((time.time() - step_start) * 1000, 2)

            step_result["name"] = step_name
            step_result["type"] = step.get("type", "")
            step_result["duration"] = step_duration
            step_result["step_index"] = index
            results.append(step_result)

            if on_step_complete:
                try:
                    on_step_complete(index, step_result)
                except Exception:
                    pass

            if not step_result["success"]:
                all_success = False
                break

        duration = round(time.time() - start_time, 2)

        return {
            "success": all_success,
            "message": "脚本执行成功" if all_success else "脚本执行失败",
            "steps": results,
            "duration": duration,
        }

    async def stop(self):
        """关闭浏览器，保存 Trace"""
        trace_path = None
        try:
            if self._context and self.config.trace_enabled:
                trace_path = f"/app/traces/trace-{int(time.time())}.zip"
                await self._context.tracing.stop(path=trace_path)
                logger.info(f"Trace 已保存: {trace_path}")
        except Exception as e:
            logger.warning(f"Trace 保存失败: {e}")
            trace_path = None

        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._step_executor = None
        self._trace_path = trace_path
        logger.info("Playwright 浏览器已关闭")

    @property
    def trace_path(self) -> Optional[str]:
        return self._trace_path

    @property
    def page(self) -> Optional[Page]:
        return self._page
