"""Seed default AI settings and prompt templates"""

from django.db import migrations


def seed_ai_settings(apps, schema_editor):
    AISetting = apps.get_model('settings', 'AISetting')

    defaults = [
        # Provider 选择
        {'key': 'PRIMARY_PROVIDER', 'value': '', 'category': 'provider', 'description': '主 Provider (openai/qwen)', 'is_secret': False},
        {'key': 'FALLBACK_PROVIDER', 'value': '', 'category': 'provider', 'description': '备用 Provider (openai/qwen)', 'is_secret': False},

        # OpenAI 配置
        {'key': 'OPENAI_API_KEY', 'value': '', 'category': 'openai', 'description': 'OpenAI API Key', 'is_secret': True},
        {'key': 'OPENAI_API_BASE', 'value': '', 'category': 'openai', 'description': 'OpenAI API Base URL', 'is_secret': False},
        {'key': 'OPENAI_MODEL', 'value': '', 'category': 'openai', 'description': 'OpenAI 模型名称', 'is_secret': False},

        # 通义千问配置
        {'key': 'QWEN_API_KEY', 'value': '', 'category': 'qwen', 'description': '通义千问 API Key', 'is_secret': True},
        {'key': 'QWEN_MODEL', 'value': '', 'category': 'qwen', 'description': '通义千问模型名称', 'is_secret': False},

        # 通用参数
        {'key': 'MAX_RETRIES', 'value': '', 'category': 'general', 'description': '最大重试次数', 'is_secret': False},
        {'key': 'RETRY_BASE_DELAY', 'value': '', 'category': 'general', 'description': '重试基础延迟 (秒)', 'is_secret': False},
        {'key': 'TIMEOUT', 'value': '', 'category': 'general', 'description': '请求超时 (秒)', 'is_secret': False},
        {'key': 'DEFAULT_MAX_TOKENS', 'value': '', 'category': 'general', 'description': '默认最大 Token 数', 'is_secret': False},
    ]

    for item in defaults:
        AISetting.objects.get_or_create(
            key=item['key'],
            defaults={
                'value': item['value'],
                'category': item['category'],
                'description': item['description'],
                'is_secret': item['is_secret'],
            },
        )


def seed_prompt_templates(apps, schema_editor):
    PromptTemplate = apps.get_model('settings', 'PromptTemplate')

    # healing strict 模板
    heal_prompt = """\
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

    PromptTemplate.objects.get_or_create(
        service='healing',
        scenario='strict',
        defaults={
            'name': '严格自愈模板',
            'system_prompt': heal_prompt,
            'description': '默认的自愈分析模板，优先推荐稳定定位器',
            'is_active': True,
            'temperature': 0.2,
        },
    )

    # nl2script strict 模板
    nl2script_prompt = """\
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

    PromptTemplate.objects.get_or_create(
        service='nl2script',
        scenario='strict',
        defaults={
            'name': '严格脚本生成模板',
            'system_prompt': nl2script_prompt,
            'description': '默认的 NL2Script 模板，优先使用 CSS 选择器',
            'is_active': True,
            'temperature': 0.3,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('settings', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_ai_settings, migrations.RunPython.noop),
        migrations.RunPython(seed_prompt_templates, migrations.RunPython.noop),
    ]
