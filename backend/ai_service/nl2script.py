"""
NL2Script - 自然语言转 Playwright 测试步骤
调用 LLM Gateway，将用户自然语言描述转为平台标准步骤 JSON
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .client import LLMGateway
from .exceptions import AIServiceError

# ==================== System Prompt ====================

NL2SCRIPT_SYSTEM_PROMPT = """\
你是一个专业的 Playwright Web 自动化测试脚本生成器。
用户会用自然语言描述测试操作，你需要将其转化为结构化的 JSON 步骤数组。

## 严格规则
1. 仅输出合法 JSON 数组，不要输出任何解释文字、markdown 代码块标记或其他内容。
2. 定位器优先级：CSS 选择器 > data-testid > XPath。禁止使用绝对路径 XPath。
3. 每个独立动作为一个步骤，不要合并操作。
4. 在点击/输入等关键操作前，如果页面可能尚未加载完成，插入一个 wait_element 步骤。
5. 所有 locator 使用 Playwright 标准格式：
   - CSS: 直接写选择器，如 "#login-btn", ".submit", "[name='username']"
   - XPath: 加 "xpath=" 前缀，如 "xpath=//button[text()='登录']"
   - data-testid: 加 "[data-testid='xxx']"

## 支持的步骤类型 (type)
- goto: 打开页面，需提供 url
- click: 点击元素
- input: 输入文本，需提供 value
- clear: 清空输入框
- select: 下拉选择，需提供 value
- checkbox: 复选框操作，需提供 checked (true/false)
- double_click: 双击
- right_click: 右键点击
- hover: 鼠标悬停
- assert_text: 验证文本包含，需提供 text
- assert_title: 验证页面标题，需提供 expected
- assert_url: 验证URL，需提供 expected
- assert_element: 验证元素存在
- assert_visible: 验证元素可见
- wait: 固定等待，需提供 duration (秒)
- wait_element: 等待元素出现，需提供 timeout (秒，默认10)
- screenshot: 截图
- scroll: 滚动，需提供 scroll_type (top/bottom/custom)
- refresh: 刷新页面
- back: 后退
- forward: 前进

## 输出格式
```json
[
  {
    "type": "步骤类型",
    "name": "步骤中文名称（简短描述）",
    "locator": "定位器字符串（如 '#login-btn'）",
    "value": "输入值或期望值（如无则为空字符串）",
    "options": {}
  }
]
```

## 示例

用户输入: "打开百度，搜索关键词 playwright，然后点击搜索按钮"
输出:
[
  {"type": "goto", "name": "打开百度", "locator": "", "value": "https://www.baidu.com", "options": {}},
  {"type": "input", "name": "输入搜索关键词", "locator": "#kw", "value": "playwright", "options": {}},
  {"type": "click", "name": "点击搜索按钮", "locator": "#su", "value": "", "options": {}},
  {"type": "wait", "name": "等待搜索结果", "locator": "", "value": "", "options": {"duration": 2}},
  {"type": "assert_element", "name": "验证搜索结果存在", "locator": "#content_left", "value": "", "options": {}}
]

用户输入: "登录系统，用户名 admin，密码 123456"
输出:
[
  {"type": "goto", "name": "打开登录页面", "locator": "", "value": "/login", "options": {}},
  {"type": "wait_element", "name": "等待登录表单加载", "locator": "input[name='username']", "value": "", "options": {"timeout": 10}},
  {"type": "input", "name": "输入用户名", "locator": "input[name='username']", "value": "admin", "options": {}},
  {"type": "input", "name": "输入密码", "locator": "input[name='password']", "value": "123456", "options": {}},
  {"type": "click", "name": "点击登录按钮", "locator": "button[type='submit']", "value": "", "options": {}},
  {"type": "wait", "name": "等待登录完成", "locator": "", "value": "", "options": {"duration": 2}},
  {"type": "assert_url", "name": "验证跳转到首页", "locator": "", "value": "/", "options": {}}
]
"""


# ==================== LLM 输出 → 平台步骤格式转换 ====================

def _parse_locator_string(locator_str: str) -> Dict[str, str]:
    """
    将 LLM 输出的定位器字符串解析为平台格式 {"type": "...", "value": "..."}

    Playwright 定位器格式:
    - "xpath=//div" → {"type": "xpath", "value": "//div"}
    - "#id" → {"type": "css", "value": "#id"}
    - ".class" → {"type": "css", "value": ".class"}
    - "[name='x']" → {"type": "css", "value": "[name='x']"}
    - "text=登录" → {"type": "text", "value": "登录"}
    - 空/无 → None
    """
    if not locator_str or not locator_str.strip():
        return None

    locator_str = locator_str.strip()

    # 带 Playwright 前缀的定位器
    if locator_str.startswith("xpath="):
        return {"type": "xpath", "value": locator_str[6:]}
    if locator_str.startswith("text="):
        return {"type": "text", "value": locator_str[5:]}
    if locator_str.startswith("css="):
        return {"type": "css", "value": locator_str[4:]}

    # data-testid 属性
    if locator_str.startswith("[data-testid"):
        return {"type": "css", "value": locator_str}

    # ID 选择器
    if locator_str.startswith("#"):
        return {"type": "id", "value": locator_str[1:]}

    # CSS 类选择器
    if locator_str.startswith("."):
        return {"type": "css", "value": locator_str}

    # 属性选择器
    if locator_str.startswith("["):
        return {"type": "css", "value": locator_str}

    # 默认视为 CSS
    return {"type": "css", "value": locator_str}


def _convert_llm_step_to_platform(llm_step: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 LLM 输出的步骤格式转为平台标准格式

    LLM 格式: {"type": "click", "name": "...", "locator": "#btn", "value": "", "options": {}}
    平台格式: {"type": "click", "name": "...", "params": {"locator": {"type": "css", "value": "#btn"}, "value": ""}}
    """
    step_type = llm_step.get("type", "")
    step_name = llm_step.get("name", "")
    locator_str = llm_step.get("locator", "")
    value = llm_step.get("value", "")
    options = llm_step.get("options", {})

    # 构建 params
    params = {}

    # 解析定位器
    locator = _parse_locator_string(locator_str)
    if locator:
        params["locator"] = locator

    # 根据步骤类型填充参数
    if step_type == "goto":
        params["url"] = value
    elif step_type in ("input", "clear"):
        params["value"] = value
        if options.get("clear_first", True):
            params["clear_first"] = True
    elif step_type == "select":
        params["value"] = value
    elif step_type == "checkbox":
        params["checked"] = options.get("checked", True)
    elif step_type == "assert_text":
        params["text"] = value
        if locator:
            params["locator"] = locator
    elif step_type == "assert_title":
        params["expected"] = value
    elif step_type == "assert_url":
        params["expected"] = value
    elif step_type == "wait":
        params["duration"] = options.get("duration", 1)
    elif step_type == "wait_element":
        params["timeout"] = options.get("timeout", 10)
    elif step_type == "scroll":
        params["scroll_type"] = options.get("scroll_type", "bottom")
    elif step_type == "screenshot":
        pass  # 无需额外参数
    elif step_type == "upload":
        params["file_path"] = value

    return {
        "type": step_type,
        "name": step_name,
        "params": params,
    }


# ==================== NL2Script 主服务 ====================

class NL2ScriptService:
    """自然语言转脚本服务"""

    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        将自然语言描述转为平台步骤

        Args:
            prompt: 用户自然语言描述
            context: 上下文信息（如当前页面 URL、已有步骤等）

        Returns:
            {
                "steps": [...],          # 平台标准步骤数组
                "raw_steps": [...],      # LLM 原始输出
                "token_usage": {...},    # Token 消耗
                "model": str,            # 使用的模型
                "provider": str,         # 使用的提供商
            }
        """
        # 构建完整 prompt
        full_prompt = prompt
        if context:
            full_prompt = f"上下文信息:\n{context}\n\n请基于以上上下文，执行以下操作:\n{prompt}"

        # 调用 LLM Gateway
        response = await self.gateway.call_json(
            prompt=full_prompt,
            system_prompt=NL2SCRIPT_SYSTEM_PROMPT,
            temperature=0.3,  # 低温度，保证输出稳定性
        )

        # 解析 LLM 输出
        raw_steps = response.raw_response.get("parsed_json", [])

        if not isinstance(raw_steps, list):
            raise AIServiceError(f"LLM 输出不是数组: {type(raw_steps)}")

        # 转换为平台步骤格式
        platform_steps = []
        for i, llm_step in enumerate(raw_steps):
            try:
                platform_step = _convert_llm_step_to_platform(llm_step)
                platform_steps.append(platform_step)
            except Exception as e:
                logger.warning(f"步骤 {i} 转换失败: {e}, 原始数据: {llm_step}")
                # 保留原始步骤作为回退
                platform_steps.append({
                    "type": llm_step.get("type", "unknown"),
                    "name": llm_step.get("name", f"步骤{i + 1}"),
                    "params": llm_step.get("options", {}),
                })

        return {
            "steps": platform_steps,
            "raw_steps": raw_steps,
            "token_usage": response.token_usage,
            "model": response.model,
            "provider": response.provider,
        }

    async def batch_generate(
        self,
        prompts: List[str],
        context: Optional[str] = None,
        max_concurrency: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        批量生成脚本（并行调用 LLM）

        Args:
            prompts: 自然语言描述列表
            context: 共享上下文
            max_concurrency: 最大并行数（控制 Token 消耗速率）

        Returns:
            列表，每个元素与 generate() 返回格式一致，附加 index 和 error 字段
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        total_tokens = 0

        async def _generate_one(index: int, prompt: str) -> Dict[str, Any]:
            nonlocal total_tokens
            async with semaphore:
                try:
                    result = await self.generate(prompt=prompt, context=context)
                    total_tokens += result["token_usage"].get("total_tokens", 0)
                    result["index"] = index
                    result["prompt"] = prompt
                    result["success"] = True
                    return result
                except Exception as e:
                    logger.error(f"批量生成第 {index} 条失败: {e}")
                    return {
                        "index": index,
                        "prompt": prompt,
                        "success": False,
                        "error": str(e),
                        "steps": [],
                        "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    }

        tasks = [_generate_one(i, p) for i, p in enumerate(prompts)]
        results = await asyncio.gather(*tasks)

        # 按原始顺序排列
        results.sort(key=lambda x: x["index"])

        logger.info(f"批量生成完成: {len(prompts)} 条, 总 Token: {total_tokens}")
        return list(results)
