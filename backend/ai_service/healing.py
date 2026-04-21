"""
智能自愈 - 定位器修复服务
根据执行报错和 DOM 快照，调用 LLM 推荐替代定位器
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

from .client import LLMGateway
from .exceptions import AIServiceError

# ==================== System Prompt ====================

HEAL_SYSTEM_PROMPT = """\
你是一个专业的 Web 自动化测试定位器修复专家。

用户会提供一个失败的定位器信息、错误消息以及当前页面的 DOM 快照。
你需要分析 DOM 结构，找到一个可以替代原始定位器的新定位器。

## 定位器推荐优先级（从高到低）
1. data-testid 属性: [data-testid="xxx"] （最稳定，推荐首选）
2. id 属性: #id-value
3. 语义化 CSS: 结合标签+类名+属性，如 button.submit-btn, input[name="email"]
4. 稳定 XPath: 基于文本内容或稳定属性，如 //button[text()="登录"]
5. 层级 CSS: 如 form.login-form > button

## 严格规则
1. 禁止使用绝对位置 XPath（如 /html/body/div[2]/div[3]/span[1]）
2. 推荐的定位器必须在 DOM 快照中能唯一定位到目标元素
3. 如果 DOM 中确实无法找到匹配元素，返回 heal_status=failed
4. 如果原始定位器格式本身有误，优先修复格式

## 输出格式（严格 JSON，不要输出其他内容）
{
  "heal_status": "success 或 failed",
  "original_locator": "原始定位器（回显）",
  "suggested_locator": "推荐的替代定位器",
  "locator_type": "css 或 xpath 或 data-testid 或 id 或 text",
  "target_element": "目标元素的简短描述",
  "confidence": 0.0到1.0之间的置信度,
  "reason": "推荐理由的中文说明"
}

## 示例

输入:
- 原始定位器: xpath=//button[@class='submit-btn']
- 错误: 元素未找到
- DOM 片段: <button data-testid="login-submit" class="btn-primary" type="submit">登录</button>

输出:
{
  "heal_status": "success",
  "original_locator": "xpath=//button[@class='submit-btn']",
  "suggested_locator": "[data-testid='login-submit']",
  "locator_type": "data-testid",
  "target_element": "登录提交按钮",
  "confidence": 0.95,
  "reason": "原始 class 名已变更，发现 data-testid 属性，这是最稳定的定位方式"
}
"""

# ==================== 规则引擎（不依赖 LLM 的快速匹配） ====================

# 常见定位器失败原因和修复规则
_QUICK_FIX_RULES = [
    # ID 选择器：页面重构后 ID 可能加了前缀
    {
        "pattern": r"^#(\w+)$",
        "hint": "尝试搜索包含该 ID 片段的元素",
    },
    # class 选择器：class 名可能变更
    {
        "pattern": r"^\.([\w-]+)$",
        "hint": "class 名可能已变更，检查是否有相近的 class",
    },
]


def _extract_original_locator_info(locator: Dict[str, Any]) -> str:
    """从平台定位器格式中提取可读字符串"""
    if not locator:
        return ""
    loc_type = locator.get("type", "")
    loc_value = locator.get("value", "")
    if loc_type == "xpath":
        return f"xpath={loc_value}"
    elif loc_type == "css":
        return loc_value
    elif loc_type == "id":
        return f"#{loc_value}"
    elif loc_type == "name":
        return f"[name='{loc_value}']"
    else:
        return f"{loc_type}={loc_value}"


def _suggested_locator_to_platform(
    suggested: str, locator_type: str
) -> Dict[str, str]:
    """
    将 LLM 推荐的定位器字符串转为平台格式

    LLM 输出 locator_type: css/xpath/data-testid/id/text
    平台格式: {"type": "css"/"xpath"/"id"/"text"/..., "value": "..."}
    """
    # data-testid 本质是 CSS 选择器
    if locator_type == "data-testid":
        return {"type": "css", "value": suggested}
    elif locator_type == "id":
        # 确保不重复 # 前缀
        value = suggested.lstrip("#")
        return {"type": "id", "value": value}
    elif locator_type == "xpath":
        # 去掉可能的 xpath= 前缀
        value = suggested.replace("xpath=", "", 1)
        return {"type": "xpath", "value": value}
    elif locator_type == "text":
        return {"type": "text", "value": suggested}
    else:
        # 默认 CSS
        return {"type": "css", "value": suggested}


# ==================== 自愈主服务 ====================

class HealingService:
    """定位器智能自愈服务"""

    def __init__(self, gateway: LLMGateway):
        self.gateway = gateway

    async def analyze(
        self,
        original_locator: Dict[str, Any],
        error_message: str,
        dom_snapshot: str,
        step_name: str = "",
        step_index: int = -1,
    ) -> Dict[str, Any]:
        """
        分析失败步骤并推荐替代定位器

        Args:
            original_locator: 原始定位器 {"type": "...", "value": "..."}
            error_message: 错误信息
            dom_snapshot: DOM 快照 HTML
            step_name: 步骤名称
            step_index: 步骤索引

        Returns:
            自愈分析结果（兼容 HealLog 字段）
        """
        # 如果 DOM 快照太长，截取前 8000 字符（控制 Token 消耗）
        dom_preview = dom_snapshot[:8000] if len(dom_snapshot) > 8000 else dom_snapshot

        locator_str = _extract_original_locator_info(original_locator)

        # 构建 prompt
        prompt = f"""\
请分析以下定位器失败案例：

## 失败信息
- 步骤名称: {step_name or '未命名步骤'}
- 步骤索引: {step_index}
- 原始定位器: {locator_str}
- 错误消息: {error_message}

## 当前页面 DOM 快照
```html
{dom_preview}
```

请推荐一个替代定位器。"""

        # 调用 LLM
        response = await self.gateway.call_json(
            prompt=prompt,
            system_prompt=HEAL_SYSTEM_PROMPT,
            temperature=0.2,  # 低温度，保证分析稳定性
        )

        parsed = response.raw_response.get("parsed_json", {})

        # 转换推荐定位器为平台格式
        suggested_str = parsed.get("suggested_locator", "")
        locator_type = parsed.get("locator_type", "css")
        suggested_platform = _suggested_locator_to_platform(suggested_str, locator_type)

        # 确定修复策略
        heal_strategy = "llm_recommend"
        if parsed.get("confidence", 0) >= 0.9:
            heal_strategy = "llm_recommend"

        return {
            "heal_status": parsed.get("heal_status", "failed"),
            "original_locator": locator_str,
            "suggested_locator": suggested_str,
            "suggested_locator_platform": suggested_platform,
            "locator_type": locator_type,
            "confidence": min(parsed.get("confidence", 0.0), 1.0),
            "reason": parsed.get("reason", ""),
            "target_element": parsed.get("target_element", ""),
            "heal_strategy": heal_strategy,
            "token_usage": response.token_usage,
            "model": response.model,
            "provider": response.provider,
        }

    async def auto_heal_script(
        self,
        script_id: int,
        execution_id: int,
        step_index: int,
        error_message: str,
        dom_snapshot: str,
    ) -> Dict[str, Any]:
        """
        自动修复脚本中指定步骤的定位器

        流程：
        1. 读取脚本中失败步骤的定位器
        2. 调用 LLM 分析并推荐替代定位器
        3. 记录 HealLog
        4. 如果置信度 >= 0.8 且脚本启用自愈，自动应用

        Args:
            script_id: 脚本 ID
            execution_id: 执行记录 ID
            step_index: 失败步骤索引
            error_message: 错误信息
            dom_snapshot: DOM 快照

        Returns:
            自愈结果
        """
        from apps.scripts.models import Script
        from apps.executions.models import Execution, HealLog

        # 读取脚本和步骤
        try:
            script = Script.objects.get(id=script_id)
        except Script.DoesNotExist:
            raise AIServiceError(f"脚本不存在: {script_id}")

        try:
            execution = Execution.objects.get(id=execution_id)
        except Execution.DoesNotExist:
            raise AIServiceError(f"执行记录不存在: {execution_id}")

        steps = script.steps or []
        if step_index < 0 or step_index >= len(steps):
            raise AIServiceError(f"步骤索引越界: {step_index}")

        step = steps[step_index]
        step_name = step.get("name", "")
        original_locator = step.get("params", {}).get("locator", {})

        # 调用 LLM 分析
        result = await self.analyze(
            original_locator=original_locator,
            error_message=error_message,
            dom_snapshot=dom_snapshot,
            step_name=step_name,
            step_index=step_index,
        )

        # 记录 HealLog
        heal_log = HealLog.objects.create(
            script=script,
            execution=execution,
            step_index=step_index,
            step_name=step_name,
            original_locator=result["original_locator"],
            suggested_locator=result["suggested_locator"],
            locator_type=result["locator_type"],
            heal_status=result["heal_status"],
            heal_strategy=result["heal_strategy"],
            confidence=result["confidence"],
            reason=result["reason"],
            dom_snapshot=dom_snapshot[:5000],  # 截断存储
            llm_provider=result["provider"],
            token_consumed=result["token_usage"].get("total_tokens", 0),
            auto_applied=False,
        )

        # 自动应用逻辑：置信度 >= 0.8 且脚本启用了自愈
        auto_applied = False
        if (
            result["heal_status"] == "success"
            and result["confidence"] >= 0.8
            and script.heal_enabled
        ):
            # 更新脚本步骤中的定位器
            steps[step_index]["params"]["locator"] = result["suggested_locator_platform"]
            script.steps = steps
            script.save(update_fields=["steps", "updated_at"])

            heal_log.auto_applied = True
            heal_log.save(update_fields=["auto_applied"])
            auto_applied = True

            logger.info(
                f"自愈自动应用: 脚本 '{script.name}' 步骤 {step_index}, "
                f"{result['original_locator']} → {result['suggested_locator']}"
            )

        result["auto_applied"] = auto_applied
        result["heal_log_id"] = heal_log.id
        return result
