"""
配置解析器 - 从数据库读取 AI 配置，环境变量兜底

对外暴露两个核心函数:
1. get_ai_config() -> dict — 获取所有 AI 配置
2. get_active_prompt(service) -> (str, float) — 获取激活的提示词模板
"""

from django.conf import settings as django_settings
from loguru import logger


def get_ai_config() -> dict:
    """
    从 DB 读配置，空值 fallback 到 settings.AI_SERVICE

    Returns:
        dict: 与 settings.AI_SERVICE 结构一致的配置字典
    """
    from .models import AISetting

    # 以环境变量配置为底板
    fallback = getattr(django_settings, 'AI_SERVICE', {})
    result = dict(fallback)

    try:
        db_settings = AISetting.objects.all()
        db_map = {s.key: s.value for s in db_settings}

        # 用 DB 中的值覆盖（空字符串也表示用户主动清空，应覆盖默认值）
        for key, value in db_map.items():
            if key in result:
                # 数值类型转换
                if key in ('MAX_RETRIES', 'TIMEOUT', 'DEFAULT_MAX_TOKENS'):
                    try:
                        result[key] = int(value)
                    except (ValueError, TypeError):
                        pass
                elif key in ('RETRY_BASE_DELAY',):
                    try:
                        result[key] = float(value)
                    except (ValueError, TypeError):
                        pass
                else:
                    result[key] = value
            elif value != '' and key not in result:
                result[key] = value
    except Exception as e:
        logger.warning(f'从 DB 读取 AI 配置失败，使用环境变量兜底: {e}')

    # 智能处理 FALLBACK_PROVIDER：仅当对应的 API Key 已配置时才启用
    fb_provider = result.get('FALLBACK_PROVIDER', '')
    if fb_provider:
        fb_key_map = {'openai': 'OPENAI_API_KEY', 'qwen': 'QWEN_API_KEY'}
        fb_key_name = fb_key_map.get(fb_provider)
        if fb_key_name and not result.get(fb_key_name, '').strip():
            logger.info(f'备用 Provider ({fb_provider}) 的 API Key 未配置，跳过备用 Provider')
            result['FALLBACK_PROVIDER'] = ''

    return result


def get_active_prompt(service: str):
    """
    获取激活模板的 prompt + temperature，fallback 到模块常量

    Args:
        service: 'healing' 或 'nl2script'

    Returns:
        tuple: (system_prompt: str, temperature: float)
    """
    from .models import PromptTemplate

    try:
        template = PromptTemplate.objects.filter(
            service=service, is_active=True
        ).first()

        if template and template.system_prompt:
            return template.system_prompt, template.temperature
    except Exception as e:
        logger.warning(f'从 DB 读取 Prompt 模板失败: {e}')

    # fallback 到模块常量
    if service == 'healing':
        from ai_service.healing import HEAL_SYSTEM_PROMPT
        return HEAL_SYSTEM_PROMPT, 0.2
    elif service == 'nl2script':
        from ai_service.nl2script import NL2SCRIPT_SYSTEM_PROMPT
        return NL2SCRIPT_SYSTEM_PROMPT, 0.3

    return '', 0.3


def _compute_config_hash() -> str:
    """计算当前配置的哈希值，用于判断配置是否变化"""
    import hashlib
    config = get_ai_config()
    raw = ','.join(f'{k}={v}' for k, v in sorted(config.items()))
    return hashlib.md5(raw.encode()).hexdigest()
